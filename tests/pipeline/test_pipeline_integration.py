from kedro.io import KedroDataCatalog
from kedro.pipeline import node, pipeline
from kedro.pipeline.modular_pipeline import pipeline as modular_pipeline
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
        cook_pipeline = modular_pipeline(
            [node(defrost, "frozen_meat", "meat"), node(grill, "meat", "grilled_meat")]
        )

        lunch_pipeline = modular_pipeline([node(eat, "food", "output")])

        pipeline1 = (
            pipeline(cook_pipeline, outputs={"grilled_meat": "food"}) + lunch_pipeline
        )

        pipeline2 = cook_pipeline + pipeline(
            lunch_pipeline, inputs={"food": "grilled_meat"}
        )
        pipeline3 = pipeline(
            cook_pipeline, outputs={"grilled_meat": "NEW_NAME"}
        ) + pipeline(lunch_pipeline, inputs={"food": "NEW_NAME"})

        for pipe in [pipeline1, pipeline2, pipeline3]:
            catalog = KedroDataCatalog(
                {}, feed_dict={"frozen_meat": "frozen_meat_data"}
            )
            result = SequentialRunner().run(pipe, catalog)
            assert result == {"output": "frozen_meat_data_defrosted_grilled_done"}

    def test_reuse_same_pipeline(self):
        """
        The same pipeline needs to be used twice in the same big pipeline.
        Normally dataset and node names would conflict,
        so we need to `transform` the pipelines.
        """
        cook_pipeline = modular_pipeline(
            [
                node(defrost, "frozen_meat", "meat", name="defrost_node"),
                node(grill, "meat", "grilled_meat", name="grill_node"),
            ]
        )
        breakfast_pipeline = modular_pipeline(
            [node(eat, "breakfast_food", "breakfast_output")]
        )
        lunch_pipeline = modular_pipeline([node(eat, "lunch_food", "lunch_output")])

        # We are using two different mechanisms here for breakfast and lunch,
        # renaming and prefixing pipelines differently.
        pipe = (
            pipeline(
                cook_pipeline,
                outputs={"grilled_meat": "breakfast_food"},
                namespace="breakfast",
            )
            + breakfast_pipeline
            + pipeline(cook_pipeline, namespace="lunch")
            + pipeline(lunch_pipeline, inputs={"lunch_food": "lunch.grilled_meat"})
        )
        catalog = KedroDataCatalog(
            {},
            feed_dict={
                "breakfast.frozen_meat": "breakfast_frozen_meat",
                "lunch.frozen_meat": "lunch_frozen_meat",
            },
        )
        result = SequentialRunner().run(pipe, catalog)
        assert result == {
            "breakfast_output": "breakfast_frozen_meat_defrosted_grilled_done",
            "lunch_output": "lunch_frozen_meat_defrosted_grilled_done",
        }
