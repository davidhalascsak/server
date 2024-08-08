import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from src.api_server import app

TEST_MODEL = "gpt2"


# TODO: Test TRTLLM too
class TestChatCompletion:
    # TODO: Consider module/package scope, or join ChatCompletions tests into same file
    # to run server only once for both sets of tests for faster iteration.
    @pytest.fixture(scope="class")
    def client(self):
        model_repository = Path(__file__).parent / "vllm_models"
        os.environ["TRITON_MODEL_REPOSITORY"] = str(model_repository)
        with TestClient(app) as test_client:
            yield test_client

    def test_completions_defaults(self, client):
        prompt = "Hello"

        response = client.post(
            "/v1/completions",
            json={"model": TEST_MODEL, "prompt": prompt},
        )

        print("Response:", response.json())
        assert response.status_code == 200
        # NOTE: Could be improved to look for certain quality of response,
        #       or tested with dummy identity model.
        assert response.json()["choices"][0]["text"].strip()

    @pytest.mark.parametrize(
        "sampling_parameter, value",
        [
            ("temperature", 0.7),
            ("max_tokens", 10),
            ("top_p", 0.9),
            ("frequency_penalty", 0.5),
            ("presence_penalty", 0.2),
            ("logprobs", 5),
            ("logit_bias", {"0": 0}),
        ],
    )
    def test_completions_sampling_parameters(self, client, sampling_parameter, value):
        prompt = "Hello"

        response = client.post(
            "/v1/completions",
            json={"model": TEST_MODEL, "prompt": prompt, sampling_parameter: value},
        )
        print("Response:", response.json())

        # TODO: Add support and remove this check
        unsupported_parameters = ["logprobs", "logit_bias"]
        if sampling_parameter in unsupported_parameters:
            assert response.status_code == 400
            assert response.json()["detail"] == "logit bias and log probs not supported"
            return

        assert response.status_code == 200
        assert response.json()["choices"][0]["text"].strip()

    # Simple tests to verify max_tokens roughly behaves as expected
    def test_completions_max_tokens(self, client):
        prompt = "Hello"
        responses = []

        max_tokens = 1
        responses.append(
            client.post(
                "/v1/completions",
                json={"model": TEST_MODEL, "prompt": prompt, "max_tokens": max_tokens},
            )
        )
        max_tokens = 1
        responses.append(
            client.post(
                "/v1/completions",
                json={"model": TEST_MODEL, "prompt": prompt, "max_tokens": max_tokens},
            )
        )
        max_tokens = 100
        responses.append(
            client.post(
                "/v1/completions",
                json={"model": TEST_MODEL, "prompt": prompt, "max_tokens": max_tokens},
            )
        )

        for response in responses:
            print("Response:", response.json())
            assert response.status_code == 200

        response1_text = responses[0].json()["choices"][0]["text"].strip().split()
        response2_text = responses[1].json()["choices"][0]["text"].strip().split()
        response3_text = responses[2].json()["choices"][0]["text"].strip().split()
        assert len(response1_text) == len(response2_text) == 1
        assert len(response3_text) > len(response1_text)

    @pytest.mark.parametrize(
        "sampling_parameter, value",
        [
            ("temperature", 2.1),
            ("temperature", -0.1),
            ("max_tokens", -1),
            ("top_p", 1.1),
            ("frequency_penalty", 3),
            ("frequency_penalty", -3),
            ("presence_penalty", 2.1),
            ("presence_penalty", -2.1),
        ],
    )
    def test_completions_invalid_sampling_parameters(
        self, client, sampling_parameter, value
    ):
        prompt = "Hello"

        response = client.post(
            "/v1/completions",
            json={"model": TEST_MODEL, "prompt": prompt, sampling_parameter: value},
        )

        print("Response:", response.json())
        assert response.status_code == 422

    def test_empty_prompt(self, client):
        response = client.post(
            "/v1/completions", json={"model": TEST_MODEL, "prompt": ""}
        )

        # NOTE: Should this be validated in schema instead?
        # 400 Error returned in route handler
        assert response.status_code == 400

    def test_no_prompt(self, client):
        response = client.post("/v1/completions", json={"model": TEST_MODEL})

        # 422 Error returned by schema validation
        assert response.status_code == 422
