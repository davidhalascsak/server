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
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import openai
import requests
from src.api_server import init_app


def setup_fastapi_app(tokenizer: str, model_repository: str):
    os.environ["TOKENIZER"] = tokenizer
    os.environ["TRITON_MODEL_REPOSITORY"] = model_repository
    app = init_app()
    return app


# Heavily inspired by vLLM's test infrastructure
class OpenAIServer:
    API_KEY = "EMPTY"  # Triton's OpenAI server does not need API key
    START_TIMEOUT = 120  # wait for server to start for up to 120 seconds

    def __init__(
        self,
        cli_args: List[str],
        *,
        env_dict: Optional[Dict[str, str]] = None,
    ) -> None:
        self.host = "localhost"
        self.port = 8000

        env = os.environ.copy()
        if env_dict is not None:
            env.update(env_dict)

        this_dir = Path(__file__).resolve().parent
        script_path = this_dir / ".." / "main.py"
        self.proc = subprocess.Popen(
            ["python3", script_path] + cli_args,
            env=env,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        # Wait until health endpoint is responsive
        self._wait_for_server(url=self.url_for("health"), timeout=self.START_TIMEOUT)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.proc.terminate()
        try:
            wait_secs = 30
            self.proc.wait(wait_secs)
        except subprocess.TimeoutExpired:
            # force kill if needed
            self.proc.kill()

    def _wait_for_server(self, *, url: str, timeout: float):
        start = time.time()
        while True:
            try:
                if requests.get(url).status_code == 200:
                    break
            except Exception as err:
                result = self.proc.poll()
                if result is not None and result != 0:
                    raise RuntimeError("Server exited unexpectedly.") from err

                time.sleep(0.5)
                if time.time() - start > timeout:
                    raise RuntimeError("Server failed to start in time.") from err

    @property
    def url_root(self) -> str:
        return f"http://{self.host}:{self.port}"

    def url_for(self, *parts: str) -> str:
        return self.url_root + "/" + "/".join(parts)

    def get_client(self):
        return openai.OpenAI(
            base_url=self.url_for("v1"),
            api_key=self.API_KEY,
        )

    def get_async_client(self):
        return openai.AsyncOpenAI(
            base_url=self.url_for("v1"),
            api_key=self.API_KEY,
        )
