# How to validate data in your Kedro workflow using Great Expectations

[Great Expectations](https://docs.greatexpectations.io/docs/home/) (GE) is an open-source data quality framework that helps you validate, document, and profile your data.
It allows you to define expectations—assertions about your data’s structure and content—and verify that these hold true at runtime.

## Prerequisites

You will need the following:

- A working Kedro project.
    - The examples in this document assume the `spaceflights-pandas` starter.
If you're unfamiliar with the Spaceflights project, check out [our tutorial](../tutorials/spaceflights_tutorial.md).

- Great Expectations installed into your project.


To set yourself up, create a new Kedro project:

`kedro new --starter=spaceflights-pandas --name spaceflights-great-expectations`

Navigate to your project directory and add Pandera with pandas support to your requirements.txt:

`great-expectations>=1.8.0`

Install the project dependencies:

`uv pip install -r requirements.txt`

## Use cases

- In this section, we're going to use Great Expectations for data validation in two ways:
    - As a Kedro hook
    - As part of a pipeline run

### As a Kedro hook

Create or edit a file named hooks.py inside your project’s `src/spaceflights_great_expectations/` directory.

```py
from typing import Any
from kedro.framework.hooks import hook_impl
from kedro.pipeline.node import Node
import great_expectations as gx
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class DataValidationHooks:
    """Validate datasets using Great Expectations."""

    EXPECTATIONS = {
        "companies": [
            gx.expectations.ExpectColumnToExist(column="company_rating"),

        ],
        "reviews": [
            gx.expectations.ExpectColumnToExist(column="review_scores_rating"),
        ],
        "model_input_table": [
            gx.expectations.ExpectColumnToExist(column="price"),
            gx.expectations.ExpectColumnValuesToNotBeNull(column="price"),
        ],
    }

    def __init__(self):
        self.context = gx.get_context()

    @hook_impl
    def before_node_run(self, node: Node, inputs: dict[str, Any]) -> None:
        """Validate inputs before node runs."""
        for name, data in inputs.items():
            if name in self.EXPECTATIONS and isinstance(data, pd.DataFrame):
                self._validate(data, name)

    @hook_impl
    def after_node_run(self, node: Node, outputs: dict[str, Any]) -> None:
        """Validate outputs after node runs."""
        for name, data in outputs.items():
            if name in self.EXPECTATIONS and isinstance(data, pd.DataFrame):
                self._validate(data, name)

    def _validate(self, data: pd.DataFrame, name: str) -> None:
        """Run validation and raise error if it fails."""
        logger.info(f"Validating {name}...")

        source = self.context.data_sources.add_or_update_pandas(name)
        asset = source.add_dataframe_asset(name)

        batch_request = asset.build_batch_request(options={"dataframe": data})
        batch = asset.get_batch(batch_request)

        suite = gx.ExpectationSuite(name=f"{name}_validation")
        suite.expectations = self.EXPECTATIONS[name]

        result = batch.validate(suite)

        if not result.success:
            failed = [exp for exp in result.results if not exp.success]
            error_msg = f"Validation failed for {name}:\n"
            for exp in failed:
                error_msg += f"  - {exp.expectation_config.type}\n"
            raise ValueError(error_msg)

        logger.info(f"✓ {name} passed validation")

```

Register your custom hook in `src/spaceflights_great_expectations/settings.py`:

```py
from spaceflights_great_expectations.hooks import DataValidationHooks

HOOKS = (DataValidationHooks(),)
```

You will see the data validation in your logs, alongside your regular Kedro logs.

```bash
                    INFO     Validating reviews...                                                                                                                                                              hooks.py:47
Calculating Metrics: 100%|██████████████████████████| 2/2 [00:00<00:00, 3436.55it/s]
                    INFO     ✓ reviews passed validation                                                                                                                                                        hooks.py:67
                    INFO     Running node: create_model_input_table_node: create_model_input_table() ->                                                                                                         node.py:420
                    INFO     Validating model_input_table...                                                                                                                                                    hooks.py:47
Calculating Metrics: 100%|██████████████████████████| 8/8 [00:00<00:00, 4960.74it/s]
                    INFO     ✓ model_input_table passed validation                                                                                                                                              hooks.py:67
                    INFO     Saving data to model_input_table (ParquetDataset)...                                                                                                                      data_catalog.py:1008
                    INFO     Completed node: create_model_input_table_node                                                                                                                                    runner.py:245
                    INFO     Completed 6 out of 9 tasks                                                                                                                                                       runner.py:246
                    INFO     Loading data from model_input_table (ParquetDataset)...                                                                                                                   data_catalog.py:1048
                    INFO     Loading data from params:model_options (MemoryDataset)...                                                                                                                 data_catalog.py:1048
                    INFO     Validating model_input_table...                                                                                                                                                    hooks.py:47
Calculating Metrics: 100%|██████████████████████████| 8/8 [00:00<00:00, 4488.89it/s]
                    INFO     ✓ model_input_table passed validation
```

### As part of a pipeline run

Another option for data validation is to integrate Great Expectations as explicit nodes in a Kedro pipeline.

As an example, let's create a data validation node and add it to our `data_processing` pipeline.

```py
def validate_datasets(companies: pd.DataFrame, reviews: pd.DataFrame, shuttles: pd.DataFrame) -> None:
    """Validates datasets using Great Expectations.

    Args:
        companies: Data for companies.
        reviews: Data for reviews.
        shuttles: Data for shuttles.
    Raises:
        great_expectations.exceptions.ValidationError: If validation fails.
    """
    import great_expectations as gx

    context = gx.get_context()

    EXPECTATIONS = {
        "companies": [
            gx.expectations.ExpectColumnToExist(column="company_rating"),
        ],
        "reviews": [
            gx.expectations.ExpectColumnToExist(column="review_scores_rating"),
        ],
        "shuttles": [
            gx.expectations.ExpectColumnToExist(column="price"),
        ],
    }

    datasets = {"companies": companies, "reviews": reviews, "shuttles": shuttles}

    for name, data in datasets.items():
        source = context.data_sources.add_or_update_pandas(name)
        asset = source.add_dataframe_asset(name)

        batch_request = asset.build_batch_request(options={"dataframe": data})
        batch = asset.get_batch(batch_request)

        suite = gx.ExpectationSuite(name=f"{name}_validation")
        suite.expectations = EXPECTATIONS[name]

        result = batch.validate(suite)

        if not result.success:
            raise gx.exceptions.ValidationError(
                f"Validation failed for dataset: {name}"
            )
```

And add it to our pipeline, so it runs before the actual data processing.

```py
from .nodes import create_model_input_table, preprocess_companies, preprocess_shuttles, validate_datasets


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=validate_datasets,
                inputs=["companies", "reviews", "shuttles"],
                outputs=None,
                name="validade_datasets_node",
            ),
            Node(
                func=preprocess_companies,
                inputs="companies",
                outputs="preprocessed_companies",
                name="preprocess_companies_node",
            ),
            Node(
                func=preprocess_shuttles,
                inputs="shuttles",
                outputs="preprocessed_shuttles",
                name="preprocess_shuttles_node",
            ),
            Node(
                func=create_model_input_table,
                inputs=["preprocessed_shuttles", "preprocessed_companies", "reviews"],
                outputs="model_input_table",
                name="create_model_input_table_node",
            ),
        ]
    )
```

## Further reading

  - [Kedro Data Catalog](../catalog-data/data_catalog.md)
  - [Kedro Hooks](../extend/hooks/introduction.md)
  - [Kedro Pipelines](../build/pipeline_introduction.md)
  - [Learn Great Expectations](https://docs.greatexpectations.io/docs/reference/learn/)
  - [Great Expectations GitHub Repository](https://github.com/great-expectations/great_expectations)
