# Copyright 2020-2024, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

import triton_python_backend_utils as pb_utils


class TritonPythonModel:
    def __init__(self):
        # Maintain total inference count, so as to return error on 2nd request, all of this to simulate model failure
        self.inf_count = 0

    def execute(self, requests):
        """This function is called on inference request."""
        responses = []

        # Generate the error for the second request
        for request in requests:
            input_tensor = pb_utils.get_input_tensor_by_name(request, "IN")
            out_tensor = pb_utils.Tensor("OUT", input_tensor.as_numpy())
            if self.inf_count == 0:
                responses.append(pb_utils.InferenceResponse([out_tensor]))
            elif self.inf_count == 1:
                error = pb_utils.TritonError("An error occurred during execution")
                responses.append(pb_utils.InferenceResponse([out_tensor], error))
            elif self.inf_count == 2:
                responses.append(pb_utils.InferenceResponse([out_tensor]))
            self.inf_count += 1

        return responses
