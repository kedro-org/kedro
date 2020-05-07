# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module contains the validate decorator, which can be used as
``Node`` decorators to validate node inputs of choice. See ``kedro.pipeline.node.decorate``
"""

from inspect import Parameter, signature
from typing import Any, Callable, TypeVar

from pydantic import validate_arguments

RT = TypeVar("RT")


def validate(*arguments: Any) -> Callable[[Callable[..., RT]], Callable[..., RT]]:
    """Creates a decorator for validating function inputs according to their types.
    For a list of supported types please refer to:
    https://pydantic-docs.helpmanual.io/usage/types/
    for types which inherit from `pydantic.BaseModel` it evaluates the functions
    with the inputs casted to their model.

    Returns:
        Callable[Callable[..., RT], Callable[..., RT]]: Decorator validating the inputs
        *arguments.
    """

    def _validate(func: Callable[..., RT]) -> Callable[..., RT]:
        sig = signature(func)
        sigdic = dict(sig.parameters)
        sigdic_na = {
            k: _remove_annotation(v, k in arguments) for k, v in sigdic.items()
        }
        func.__signature__ = sig.replace(parameters=sigdic_na.values())  # type: ignore
        valid_func = validate_arguments(func)
        valid_func.__signature__ = sig.replace(parameters=sigdic.values())  # type: ignore
        return valid_func

    return _validate


def _remove_annotation(param: Parameter, skip: bool = True) -> Parameter:
    if not skip:
        param = Parameter(param.name, param.kind, default=param.default)
    return param
