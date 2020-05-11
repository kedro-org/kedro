# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
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
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
import pytest

from kedro.hooks.manager import _create_hook_manager
from kedro.hooks.specs import DataCatalogSpecs, NodeSpecs, PipelineSpecs


@pytest.mark.parametrize(
    "hook_specs,hook_name,hook_params",
    [
        (
            DataCatalogSpecs,
            "after_catalog_created",
            (
                "catalog",
                "conf_catalog",
                "conf_creds",
                "feed_dict",
                "save_version",
                "load_versions",
                "run_id",
            ),
        ),
        (
            NodeSpecs,
            "before_node_run",
            ("node", "catalog", "inputs", "is_async", "run_id"),
        ),
        (
            NodeSpecs,
            "after_node_run",
            ("node", "catalog", "inputs", "outputs", "is_async", "run_id"),
        ),
        (PipelineSpecs, "before_pipeline_run", ("run_params", "pipeline", "catalog")),
        (PipelineSpecs, "after_pipeline_run", ("run_params", "pipeline", "catalog")),
    ],
)
def test_hook_manager_can_call_hooks_defined_in_specs(
    hook_specs, hook_name, hook_params
):
    """Tests to make sure that the hook manager can call all hooks defined by specs.
    """
    hook_manager = _create_hook_manager()
    hook = getattr(hook_manager.hook, hook_name)
    assert hook.spec.namespace == hook_specs
    kwargs = {param: None for param in hook_params}
    result = hook(**kwargs)
    # since there hasn't been any hook implementation, the result should be empty
    # but it shouldn't have raised
    assert result == []


def test_hook_manager_cannot_call_non_existent_hook():
    hook_manager = _create_hook_manager()
    with pytest.raises(
        AttributeError, match="'_HookRelay' object has no attribute 'i_do_not_exist'"
    ):
        hook_manager.hook.i_do_not_exist()  # pylint: disable=no-member
