# How to validate data in your Kedro workflow using Great Expectations

[Great Expectations](https://docs.greatexpectations.io/docs/home/) (GE) is an open-source data quality framework that helps you validate, document, and profile your data.
It allows you to define expectations—assertions about your data’s structure and content—and verify that these hold true at runtime.

### The core concept: Expectations

An **Expectation** is a falsifiable, verifiable statement about your data. For example:
- "This column should never be null"
- "Values in this column should be between 0 and 100"
- "This column should only contain these specific categories"

When you run validations, Great Expectations checks if your data meets these expectations and tells you exactly what passed or failed.

### Why validate data?

Data validation helps catch issues early:
- **Bad data from external sources**: APIs change, file formats shift, upstream systems break
- **Data drift**: Your production data starts looking different from your training data
- **Pipeline bugs**: Your transformations accidentally introduce nulls or invalid values
- **Compliance**: Ensure data meets regulatory or business requirements

In Kedro, you can add these validations at strategic points in your pipeline to catch problems before they propagate downstream.

## Prerequisites

You will need the following:

- A working Kedro project.
    - The examples in this document assume the `spaceflights-pandas` starter.
If you're unfamiliar with the Spaceflights project, check out [our tutorial](../tutorials/spaceflights_tutorial.md).

- Great Expectations installed into your project.


To set yourself up, create a new Kedro project:

`kedro new --starter=spaceflights-pandas --name spaceflights-great-expectations`

Navigate to your project directory and add Great Expectations to your requirements.txt:

`great-expectations>=1.8.0`

Install the project dependencies:

`uv pip install -r requirements.txt`


## Understanding Great Expectations

Great Expectations version 1.0+ introduced a major API change: **everything is now done in Python code** rather than through CLI commands and YAML configuration files.

### Key components

1. **Context**: Your workspace for validation operations
   ```python
   context = gx.get_context()
   ```

2. **Data Source**: Connects to your data (in our case, in-memory pandas DataFrames)
   ```python
   source = context.data_sources.add_or_update_pandas("my_source")
   ```

3. **Data Asset**: A specific dataset within a data source
   ```python
   asset = source.add_dataframe_asset("companies")
   ```

4. **Batch**: A specific instance of data to validate
   ```python
   batch_request = asset.build_batch_request(options={"dataframe": df})
   batch = asset.get_batch(batch_request)
   ```

5. **Expectation Suite**: A collection of expectations to run
   ```python
   suite = gx.ExpectationSuite(name="my_validation")
   suite.expectations = [...]
   ```

6. **Validation Result**: The outcome of running expectations against a batch
   ```python
   result = batch.validate(suite)
   if not result.success:
       # Handle validation failure
   ```

### The validation workflow

```
DataFrame → Batch → Apply Expectations → Validation Result
```

When you validate data, Great Expectations:
1. Takes a snapshot of your data (the "batch")
2. Runs each expectation against it
3. Returns detailed results showing what passed and what failed


## Use cases

In this section, we're going to use Great Expectations for data validation in two ways:
- **As a Kedro hook**: Automatic validation whenever data is loaded/saved
- **As part of a pipeline run**: Explicit validation nodes in your pipeline

You can also **combine both approaches**: use hooks for automatic raw data validation, and pipeline nodes for critical checkpoints.

### Approach 1: As a Kedro hook

Hooks allow you to automatically validate data as it flows through your pipeline, without modifying your existing pipeline code.

Kedro hooks are functions that run automatically at specific points in your pipeline execution:
- `before_node_run`: Runs before a node executes (useful for validating inputs)
- `after_node_run`: Runs after a node executes (useful for validating outputs)

By placing validation logic in hooks, you create a "safety net" that catches bad data without cluttering your pipeline definitions.

To implementa hook, create or edit a file named hooks.py inside your project’s `src/spaceflights_great_expectations/` directory.

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

1. **Configuration**: The `EXPECTATIONS` dictionary maps dataset names to lists of expectations
2. **Automatic triggering**: Before/after each node runs, the hooks check if any inputs/outputs need validation
3. **Selective validation**: Only validates datasets you've explicitly configured
4. **Fail-fast behavior**: If validation fails, the pipeline stops immediately with a clear error message

Register your custom hook in `src/spaceflights_great_expectations/settings.py`:

```py
from spaceflights_great_expectations.hooks import DataValidationHooks

HOOKS = (DataValidationHooks(),)
```

run your pipeline as normal:

```bash
kedro run
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

### Approach 2: As part of a pipeline run

Another option for data validation is to integrate Great Expectations as explicit nodes in a Kedro pipeline.

Pipeline nodes offer several advantages:
- **Visibility**: Validation appears as nodes in `kedro viz`, making it clear where quality gates exist
- **Control**: Easy to run or skip validation using features like [tags](../deploy/nodes_grouping.md#grouping-by-tags) or [running pipelines by name](../getting-started/commands_reference.md#kedro-run).
- **Flexibility**: Place validation at any point—before preprocessing, after transformations, before modeling, etc.
- **Data lineage**: Validated datasets appear explicitly in your data catalog

As an example, let's create a data validation node and add it to our `data_processing` pipeline.

Add a new `validate_datasets` node to `src/spaceflights_great_expectations/pipelines/data_processing/nodes.py`:

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

Update `src/spaceflights_great_expectations/pipelines/data_processing/pipeline.py` to run the new node on our pipeline:

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
The pipeline now has an explicit validation gate at the beginning:

```
[Load data] → validate_datasets → preprocess_companies → ...
```

If validation fails, the preprocessing nodes never run, saving computation time and preventing bad data from propagating.

### Alternative: Individual validation nodes

Instead of one node that validates everything, you can create separate validation nodes:

```python
def validate_companies(companies: pd.DataFrame) -> pd.DataFrame:
    """Validate companies data and pass it through."""
    # ... validation logic ...
    return companies  # Pass through if valid

def validate_reviews(reviews: pd.DataFrame) -> pd.DataFrame:
    """Validate reviews data and pass it through."""
    # ... validation logic ...
    return reviews
```

Then in your pipeline:

```python
Pipeline([
    node(
        func=validate_companies,
        inputs="companies",
        outputs="validated_companies",
        name="validate_companies_node",
    ),
    node(
        func=preprocess_companies,
        inputs="validated_companies",  # Use validated data
        outputs="preprocessed_companies",
        name="preprocess_companies_node",
    ),
    # ...
])
```

This approach:
- Creates explicit data lineage (`companies` → `validated_companies`)
- Allows parallel validation of different datasets
- Makes it easier to skip validation for specific datasets

### Alternative: Using a file data context

If you prefer not to hardcode expectations inside your Kedro hooks or nodes, you can maintain your Great Expectations data context externally as a file.
This approach lets you separate data validation configuration from code and makes it easier to reuse the same expectations across environments or projects.

Start by creating a local Great Expectations workspace. From your project root:

```bash
mkdir great_expectations
```

Then, initialize a context in Python:

```py
import great_expectations as gx

context = gx.get_context(context_root_dir="great_expectations")
```

This will create a directory structure like:

```
great_expectations/
├── checkpoints/
├── expectations/
├── plugins/
├── uncommitted/
├── validation_definitions
└── great_expectations.yml
```

This directory acts as your file data context, storing all configuration, expectation suites, and validation results.

Instead of defining expectations inline, you can, for example, store them in the `expectations/` directory as JSON or YAML files.

For example, create an expectation suite for the companies dataset:

```
great_expectations/expectations/companies_suite.json
```

Each suite defines validation rules for a dataset, such as column existence, null checks, or value ranges.

These files can be created manually, generated from profiling code, or exported from the GX Python API:

```py
import great_expectations as gx

context = gx.get_context(context_root_dir="great_expectations")

suite = gx.ExpectationSuite(name="companies_suite")
suite.add_expectation(
    gx.expectations.ExpectColumnToExist(column="company_rating")
)
context.suites.add(suite)
```

You will see your expectation defined in the `companies_suite.json` file:

```json
{
  "expectations": [
    {
      "id": "b6c459dc-6272-4509-a986-212cc65af82e",
      "kwargs": {
        "column": "company_rating"
      },
      "meta": {},
      "severity": "critical",
      "type": "expect_column_to_exist"
    }
  ],
  "id": "b43064bb-e486-401b-b9da-0224961de88b",
  "meta": {
    "great_expectations_version": "1.8.0"
  },
  "name": "companies_suite",
  "notes": null
}
```

In your Kedro hook or pipeline node, instead of creating an in-memory context with `gx.get_context()`, load the file-based one pointing to your project directory:

```py
from pathlib import Path
import great_expectations as gx

context = gx.get_context(context_root_dir=Path.cwd() / "great_expectations")
suite = context.suites.get("companies_suite")

source = context.data_sources.add_or_update_pandas("companies_source")
asset = source.add_dataframe_asset("companies")

batch_request = asset.build_batch_request(options={"dataframe": companies})
batch = asset.get_batch(batch_request)
result = batch.validate(suite)
```

And run validation as before.


## Further reading

  - [Kedro Data Catalog](../catalog-data/data_catalog.md)
  - [Kedro Hooks](../extend/hooks/introduction.md)
  - [Kedro Pipelines](../build/pipeline_introduction.md)
  - [Learn Great Expectations](https://docs.greatexpectations.io/docs/reference/learn/)
  - [Great Expectations GitHub Repository](https://github.com/great-expectations/great_expectations)
  - [Expectations Reference Document](https://greatexpectations.io/expectations/)
