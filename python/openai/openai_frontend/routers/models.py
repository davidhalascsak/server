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

from fastapi import APIRouter, HTTPException, Request
from schemas.openai import ListModelsResponse, Model, ObjectType

router = APIRouter()

OWNED_BY = "Triton Inference Server"


@router.get("/v1/models", response_model=ListModelsResponse, tags=["Models"])
def list_models(request: Request) -> ListModelsResponse:
    """
    Lists the currently available models, and provides basic information about each one such as the owner and availability.
    """
    model_metadata = request.app.models
    if not model_metadata:
        raise HTTPException(status_code=400, detail="No known models")

    model_list = []
    for model in model_metadata:
        metadata = model_metadata[model]
        if not metadata:
            raise HTTPException(
                status_code=400, detail=f"No metadata for model: {model}"
            )

        model_list.append(
            Model(
                id=metadata.name,
                created=metadata.create_time,
                object=ObjectType.model,
                owned_by=OWNED_BY,
            ),
        )

    return ListModelsResponse(object=ObjectType.list, data=model_list)


@router.get("/v1/models/{model_name}", response_model=Model, tags=["Models"])
def retrieve_model(request: Request, model_name: str) -> Model:
    """
    Retrieves a model instance, providing basic information about the model such as the owner and permissioning.
    """
    model_metadata = request.app.models
    if not model_metadata:
        raise HTTPException(status_code=400, detail="No known models")

    model = model_metadata.get(model_name)
    if not model:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model_name}")

    if model_name == model.name:
        return Model(
            id=model.name,
            created=model.create_time,
            object=ObjectType.model,
            owned_by=OWNED_BY,
        )

    raise HTTPException(status_code=404, detail=f"Unknown model: {model_name}")
