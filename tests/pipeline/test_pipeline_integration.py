# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
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

from kedro.io import DataCatalog
from kedro.pipeline import Pipeline, node
from kedro.runner import SequentialRunner


def defrost(frozen_meat):
    return frozen_meat + "_defrosted"


def grill(meat):
    return meat + "_grilled"


def eat(food):
    return food + "_done"


class TestTransformPipelineIntegration:
    def test_connect_existing_pipelines(self):
        """
        Two pipelines exist, the dataset names do not match.
        We `transform` them to work together.
        """
        cook_pipeline = Pipeline(
            [node(defrost, "frozen_meat", "meat"), node(grill, "meat", "grilled_meat")]
        )

        lunch_pipeline = Pipeline([node(eat, "food", "output")])

        pipeline1 = (
            cook_pipeline.transform(datasets={"grilled_meat": "food"}) + lunch_pipeline
        )
        pipeline2 = cook_pipeline + lunch_pipeline.transform(
            datasets={"food": "grilled_meat"}
        )
        pipeline3 = cook_pipeline.transform(
            datasets={"grilled_meat": "NEW_NAME"}
        ) + lunch_pipeline.transform(datasets={"food": "NEW_NAME"})

        for pipeline in [pipeline1, pipeline2, pipeline3]:
            catalog = DataCatalog({}, feed_dict={"frozen_meat": "frozen_meat_data"})
            result = SequentialRunner().run(pipeline, catalog)
            assert result == {"output": "frozen_meat_data_defrosted_grilled_done"}

    def test_reuse_same_pipeline(self):
        """
        The same pipeline needs to be used twice in the same big pipeline.
        Normally dataset and node names would conflict,
        so we need to `transform` the pipelines.
        """
        cook_pipeline = Pipeline(
            [
                node(defrost, "frozen_meat", "meat", name="defrost_node"),
                node(grill, "meat", "grilled_meat", name="grill_node"),
            ]
        )
        breakfast_pipeline = Pipeline([node(eat, "breakfast_food", "breakfast_output")])
        lunch_pipeline = Pipeline([node(eat, "lunch_food", "lunch_output")])

        # We are using two different mechanisms here for breakfast and lunch,
        # renaming and prefixing pipelines differently.
        pipeline = (
            cook_pipeline.transform(
                datasets={"grilled_meat": "breakfast_food"}, prefix="breakfast"
            )
            + breakfast_pipeline
            + cook_pipeline.transform(prefix="lunch")
            + lunch_pipeline.transform(datasets={"lunch_food": "lunch.grilled_meat"})
        )
        catalog = DataCatalog(
            {},
            feed_dict={
                "breakfast.frozen_meat": "breakfast_frozen_meat",
                "lunch.frozen_meat": "lunch_frozen_meat",
            },
        )
        result = SequentialRunner().run(pipeline, catalog)
        assert result == {
            "breakfast_output": "breakfast_frozen_meat_defrosted_grilled_done",
            "lunch_output": "lunch_frozen_meat_defrosted_grilled_done",
        }
