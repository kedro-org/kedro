import re
import pytest
from kedro.pipeline import node, pipeline
from kedro.runner import SequentialRunner
from kedro.io import DataCatalog, SharedMemoryDataCatalog
from kedro.runner import SequentialRunner, ThreadRunner, ParallelRunner


class TestRunnerInputValidation:
    @pytest.mark.parametrize(
    "runner_class,catalog_class",
    [
        (SequentialRunner, DataCatalog),
        (ThreadRunner, DataCatalog),
        (ParallelRunner, SharedMemoryDataCatalog),
    ],
)
    def test_missing_input_raises_value_error(self, runner_class, catalog_class):
        # Pipeline expects input 'missing_input', which is not in the catalog
        test_pipeline = pipeline([
            node(lambda x: x, "missing_input", "output")
        ])
        catalog = catalog_class()
        runner = runner_class()
        with pytest.raises(ValueError) as excinfo:
            runner.run(test_pipeline, catalog)
        assert re.search(r"Pipeline input\(s\) .*missing_input.* not found in the ", str(excinfo.value))

    @pytest.mark.parametrize(
    "runner_class,catalog_class",
    [
        (SequentialRunner, DataCatalog),
        (ThreadRunner, DataCatalog),
        (ParallelRunner, SharedMemoryDataCatalog),
    ],
)
    def test_missing_input_because_of_pipeline_namespace_raises_value_error(self, persistent_test_dataset, runner_class, catalog_class):
        catalog = catalog_class(
            {
                "Input1": persistent_test_dataset(
                    load=lambda: "data1", save=lambda data: None
                ),
                "Output1": persistent_test_dataset(
                    load=lambda: "data3", save=lambda data: None
                ),
            }
        )

        my_pipeline = pipeline(
            [
                node(lambda x: x, inputs="Input1", outputs="Output1", name="node1"),
            ], namespace="test"
        )

        runner = runner_class()

        with pytest.raises(ValueError) as excinfo:
            runner.run(my_pipeline, catalog)

        assert f"Pipeline input(s) {{'test.Input1'}} not found in the {catalog_class.__name__}" in str(excinfo.value)
