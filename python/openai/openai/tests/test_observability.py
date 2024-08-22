# Copyright 2024, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#  * Neither the name of NVIDIA CORPORATION nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from src.api_server import init_app


# Override conftest.py default model
@pytest.fixture
def model():
    return "mock_llm"


class TestObservability:
    @pytest.fixture(scope="class")
    def client(self):
        model_repository = Path(__file__).parent / "test_models"
        os.environ["TRITON_MODEL_REPOSITORY"] = str(model_repository)
        app = init_app()
        with TestClient(app) as test_client:
            yield test_client

    ### General Error Handling ###
    def test_not_found(self, client):
        response = client.get("/does-not-exist")
        assert response.status_code == 404

    ### Startup / Health ###
    def test_startup_success(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_startup_fail(self):
        os.environ["TRITON_MODEL_REPOSITORY"] = "/does/not/exist"
        with pytest.raises(Exception):
            # Test that FastAPI lifespan startup fails when initializing Triton
            # with unknown model repository.
            app = init_app()
            with TestClient(app):
                pass

    ### Metrics ###
    def test_startup_metrics(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200
        # TODO: Flesh out metrics tests further
        # NOTE: response.json() works even on non-json prometheus data
        assert "nv_cpu_utilization" in response.json()

    ### Models ###
    def test_models_list(self, client):
        response = client.get("/v1/models")
        assert response.status_code == 200
        models = response.json()["data"]
        # Two models are in test_models specifically to verify that all models
        # are listed by this endpoint. This can be removed if the behavior changes.
        assert len(models) == 2
        for model in models:
            assert model["id"]
            assert model["object"] == "model"
            assert model["created"] > 0
            assert model["owned_by"] == "Triton Inference Server"

    def test_models_get(self, client, model):
        response = client.get(f"/v1/models/{model}")
        assert response.status_code == 200
        model_resp = response.json()
        assert model_resp["id"] == model
        assert model_resp["object"] == "model"
        assert model_resp["created"] > 0
        assert model_resp["owned_by"] == "Triton Inference Server"
