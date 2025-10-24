# How to validate data using Pandera in your Kedro workflow

[Pandera](https://pandera.readthedocs.io/) is an open-source data validation library that enables schema validation with expressive and flexible checks. It supports pandas, PySpark, Polars, Dask, Modin, and other dataframe libraries. It helps ensure data quality by validating types, ranges, business rules, and statistical properties of your datasets.

Adding Pandera to a Kedro project enables you to catch data quality issues early in your pipeline. For example, you can validate that CSV columns have the correct types and enforce business rules (like "price must be positive"). When collaborating with others on a Kedro project, Pandera schemas serve as documentation of your data contracts.

## Prerequisites

You will need the following:

- A working Kedro project. The examples in this document assume the `spaceflights-pandas` starter. If you're unfamiliar with the Spaceflights project, check out [our tutorial](../tutorials/spaceflights_tutorial.md).
- Pandera installed into the project.

To set yourself up, create a new Kedro project:

```bash
kedro new --starter=spaceflights-pandas --name spaceflights-pandera
```

Navigate to your project directory and add Pandera with pandas support to your `requirements.txt`:

```bash
pandera[pandas]>=0.18.0
```


Install the project dependencies:

```bash
uv pip install -r requirements.txt
```


## Use cases

This section explains how you can use Pandera to validate your Kedro datasets.

### Basic validation of Kedro datasets using Pandera schemas

The simplest way to add validation is to define schemas for your datasets and validate them using Kedro hooks.

First, create a directory structure for your schemas:

```bash
mkdir -p src/spaceflights_pandera/schemas
touch src/spaceflights_pandera/schemas/__init__.py
```

Create `src/spaceflights_pandera/schemas/raw.py` with validation schemas for your raw datasets:

```python
"""Pandera schemas for raw data validation."""
from pandera import Column, DataFrameSchema, Check

companies_schema = DataFrameSchema(
    columns={
        "id": Column(
            int,
            nullable=False,
            unique=True,
        ),
        "total_fleet_count": Column(
            float,
            nullable=True,
            checks=Check.greater_than_or_equal_to(0),
        ),
        "iata_approved": Column(
            str,
            nullable=True,
            checks=Check.isin(["t", "f"]),
        ),
    },
    strict=False,  # Allow additional columns not in schema
    name="companies_raw",
)

shuttles_schema = DataFrameSchema(
    columns={
        "id": Column(int, nullable=False, unique=True),
        "passenger_capacity": Column(
            int,
            nullable=False,
            checks=Check.greater_than_or_equal_to(1),
        ),
        "engines": Column(
            float,  # Use float to handle nullable integers (NaN compatibility)
            nullable=True,
            checks=Check.greater_than_or_equal_to(0),
        ),
    },
    strict=False,
    name="shuttles_raw",
)

reviews_schema = DataFrameSchema(
    columns={
        "shuttle_id": Column(int, nullable=False, unique=True),
        "review_scores_rating": Column(
            float,
            nullable=True,
            checks=Check.in_range(0, 100),
        ),
        "number_of_reviews": Column(
            int,
            nullable=True,
            checks=Check.greater_than_or_equal_to(0),
        ),
    },
    strict=False,
    name="reviews_raw",
)
```

!!! tip
    **Alternative schema style:**
    Instead of defining schemas as `DataFrameSchema` objects, Pandera also supports a Pydantic-like API with `DataFrameModel` classes and type annotations.
    This can give you IDE/type-checking support. See the [Typed Schemas guide](https://pandera.readthedocs.io/en/stable/schema_models.html).


Now create a hook to validate datasets. Create `src/spaceflights_pandera/hooks/validation.py`:

```python
"""Kedro hooks for Pandera validation integration."""
import logging
from typing import Any, Dict

from kedro.framework.hooks import hook_impl
from kedro.io import DataCatalog
from pandera.errors import SchemaError, SchemaErrors

from ..schemas.raw import companies_schema, shuttles_schema, reviews_schema

logger = logging.getLogger(__name__)


class PanderaValidationHook:
    """Kedro hook that integrates Pandera validation."""

    def __init__(self):
        # Map catalog dataset names to their validation schemas
        self.raw_schemas = {
            "companies": companies_schema,
            "shuttles": shuttles_schema,
            "reviews": reviews_schema,
        }

    @hook_impl
    def before_node_run(
        self,
        node,
        catalog: DataCatalog,
        inputs: Dict[str, Any],
        is_async: bool,
    ) -> Dict[str, Any]:
        """Validate input data before node execution."""
        validated_inputs = {}

        for input_name, data in inputs.items():
            schema = self.raw_schemas.get(input_name)

            if schema is None:
                validated_inputs[input_name] = data
                continue

            logger.info(f"Validating '{input_name}' for node '{node.name}'")

            try:
                validated_data = schema.validate(data, lazy=True)
                logger.info(f"✓ Validation passed for '{input_name}'")
                validated_inputs[input_name] = validated_data
            except (SchemaError, SchemaErrors) as e:
                logger.error("Validation failed for '%s': %s", input_name, e)
                raise

        return validated_inputs
```

Register the hook in `src/spaceflights_pandera/settings.py`:

```python
"""Project settings."""
from spaceflights_pandera.hooks.validation import PanderaValidationHook

HOOKS = (PanderaValidationHook(),)
```

From this point, when you execute `kedro run` you will see the validation logs:

```console
[10/01/25 11:10:13] INFO     Validating 'companies' for node 'preprocess_companies_node'
                    INFO     ✓ Validation passed for 'companies'
                    INFO     Validating 'shuttles' for node 'preprocess_shuttles_node'
                    INFO     ✓ Validation passed for 'shuttles'
                    INFO     Validating 'reviews' for node 'create_model_input_table_node'
                    INFO     ✓ Validation passed for 'reviews'
```

### What happens when validation fails?

Let's make one schema rule to deliberately fail so you can see Pandera in action.

In `src/spaceflights_pandera/schemas/raw.py`, change the `total_fleet_count` column check:

```diff
- checks=Check.greater_than_or_equal_to(0),
+ checks=Check.greater_than(100),  # intentionally to fail
```

Now run the pipeline again:

```bash
kedro run
```

You should see Pandera raise a `SchemaErrors` exception, reporting which rows failed:

```console
SchemaErrors: Column 'total_fleet_count' failed check 'greater_than_or_equal_to(100)'
failure cases: [1.0, 2.0, 5.0, ...]
```

Because the hook uses `lazy=True`, Pandera collects all errors at one go, making it easier to spot every problem.

### Validating data before saving with `before_dataset_saved`

So far, we validated datasets when they were loaded into a node (`before_node_run`).
You can also validate data before it is written back to the catalog, using `before_dataset_saved`.

The main difference is in what Kedro passes to the hook:

- **`before_node_run`** → gets all **node inputs** as a dictionary `{dataset_name: data}`
- **`before_dataset_saved`** → gets a single **dataset name and data** being saved

```python
@hook_impl
def before_dataset_saved(self, dataset_name: str, data: Any) -> None:
    """Validate data before saving to catalog."""
    schema = self.raw_schemas.get(dataset_name)
    if schema:
        schema.validate(data, lazy=True)
```

!!! info
    - Use `before_node_run` if you want to **guarantee that downstream nodes always receive valid inputs**.
    - Use `before_dataset_saved` if you want to **enforce contracts on the data you persist to the catalog** (for example, preventing invalid data from being stored in S3, a database, or parquet files).
    - You can also combine both hooks to validate at different stages of the pipeline.

!!! tip
    **Function-level validation**
    Instead of using Kedro hooks, you can validate directly at function boundaries with decorators:

    - `@pa.check_input`
    - `@pa.check_output`
    - `@pa.check_io`

    This can be useful for validating node functions in isolation.

## Advanced use cases

### Controlling validation behavior with environment variables

You can control validation behavior without modifying code by using environment variables.

Create configuration helpers in `src/spaceflights_pandera/schemas/__init__.py`:

```python
"""Configuration helpers for validation behavior."""
import os


def is_validation_enabled() -> bool:
    """Control validation via VALIDATION_ENABLED environment variable.

    Set to 'false' to disable all validation (useful for quick debugging).
    Default: true
    """
    return os.getenv("VALIDATION_ENABLED", "true").lower() == "true"


def should_fail_on_error() -> bool:
    """Control whether validation errors stop the pipeline.

    - true: Pipeline stops on validation errors (recommended for CI/CD)
    - false: Log errors but continue (useful for data exploration)

    Default: true
    """
    return os.getenv("VALIDATION_FAIL_ON_ERROR", "true").lower() == "true"


def get_lazy_flag() -> bool:
    """Control Pandera's lazy validation mode.

    - true: Collect ALL validation errors before failing (better error visibility)
    - false: Fail on first validation error (faster for CI/CD)

    Set via VALIDATION_LAZY environment variable.
    Default: true (collect all errors)
    """
    return os.getenv("VALIDATION_LAZY", "true").lower() == "true"
```

Update your hook to use these configuration helpers:

```python
from pandera.errors import SchemaError, SchemaErrors
from ..schemas import is_validation_enabled, should_fail_on_error, get_lazy_flag

class PanderaValidationHook:
    def __init__(self):
        self.enabled = is_validation_enabled()
        self.fail_on_error = should_fail_on_error()
        self.lazy = get_lazy_flag()

        self.raw_schemas = {
            "companies": companies_schema,
            "shuttles": shuttles_schema,
            "reviews": reviews_schema,
        }

    @hook_impl
    def before_node_run(
        self,
        node,
        catalog: DataCatalog,
        inputs: Dict[str, Any],
        is_async: bool,
    ) -> Dict[str, Any]:
        """Validate input data before node execution."""

        if not self.enabled:
            return inputs

        validated_inputs = {}

        for input_name, data in inputs.items():
            schema = self.raw_schemas.get(input_name)

            if schema is None:
                validated_inputs[input_name] = data
                continue

            logger.info(f"Validating '{input_name}' for node '{node.name}'")

            try:
                validated_data = schema.validate(data, lazy=self.lazy)
                logger.info(f"✓ Validation passed for '{input_name}'")
                validated_inputs[input_name] = validated_data
            except (SchemaError, SchemaErrors) as e:
                logger.error("Validation failed for '%s': %s", input_name, e)
                if self.fail_on_error:
                    raise
                else:
                    # Exploration mode: continue with original data
                    logger.warning(
                        "Continuing despite validation errors because "
                        "VALIDATION_FAIL_ON_ERROR=false"
                    )
                    validated_inputs[input_name] = data
            except (TypeError, AttributeError):
                # Not a validatable type, pass through unchanged
                validated_inputs[input_name] = data

        return {**inputs, **validated_inputs}
```

Now you can control validation behavior:

```bash
# Disable validation entirely (for quick debugging)
export VALIDATION_ENABLED=false
kedro run

# Log errors but don't stop pipeline (for data exploration)
export VALIDATION_FAIL_ON_ERROR=false
kedro run

# Fail on first error (for faster CI/CD)
export VALIDATION_LAZY=false
kedro run
```

**Caching validation results:** To avoid re-validating datasets used by multiple nodes, add caching to your hook:

```python
class PanderaValidationHook:
    def __init__(self):
        # ... existing init code ...
        self._validated_datasets = set()  # Add this line

    @hook_impl
    def after_context_created(self, context) -> None:
        """Reset cache at pipeline start."""
        self._validated_datasets.clear()

    @hook_impl
    def before_node_run(self, node, catalog, inputs, is_async):
        # ... existing code ...
        for input_name, data in inputs.items():
            # Skip if already validated
            if input_name in self._validated_datasets:
                validated_inputs[input_name] = data
                continue

            # ... validation logic ...

            # After successful validation:
            self._validated_datasets.add(input_name)
```


### Enhanced error reporting for validation failures

By default, Pandera error messages can be verbose. You can improve error reporting by parsing the SchemaError and logging the most relevant information.

Add this helper method to your `PanderaValidationHook` class:

```python
def _handle_validation_error(self, dataset_name: str, error: SchemaError) -> None:
    """Parse and log validation errors in a readable format."""
    logger.error(f"{'='*60}")
    logger.error(f"VALIDATION FAILED: {dataset_name}")
    logger.error(f"{'='*60}")

    # Extract key error information
    if hasattr(error, 'failure_cases') and error.failure_cases is not None:
        logger.error(f"\nFailed checks summary:")
        logger.error(f"\n{error.failure_cases.to_string()}")

    logger.error(f"\nFull error:\n{error}")
    logger.error(f"{'='*60}")

    if self.fail_on_error:
        raise
```

Then use it in your validation logic:

```python
try:
    validated_data = schema.validate(data, lazy=schema.lazy)
    logger.info(f"✓ Validation passed for '{input_name}'")
    validated_inputs[input_name] = validated_data
except SchemaError as e:
    self._handle_validation_error(input_name, e)
    validated_inputs[input_name] = data
```

### DataFrame-level checks for business rules

You can add custom business rules that validate relationships across rows or columns. For example, let's add a rule: "Type F5 shuttles cannot have more than 16 passengers."

In your schema file, define a custom check function:

```python
from pandera import Column, DataFrameSchema, Check
import pandas as pd

def check_f5_shuttle_capacity(df: pd.DataFrame) -> bool:
    """Business rule: Type F5 shuttles cannot have more than 16 passengers."""
    is_f5 = df["shuttle_type"] == "Type F5"
    has_valid_capacity = df["passenger_capacity"] <= 16
    return (~is_f5 | has_valid_capacity).all()

shuttles_schema = DataFrameSchema(
    columns={
        "id": Column(int, nullable=False, unique=True),
        "shuttle_type": Column(str, nullable=True),
        "passenger_capacity": Column(int, nullable=False),
    },
    checks=[
        Check(
            check_f5_shuttle_capacity,
            error="Type F5 shuttles cannot have more than 16 passengers"
        ),
    ],
    strict=False,
    name="shuttles_raw",
)
```

!!! tip
    **Distribution checks and hypothesis testing**
    Beyond simple rules, Pandera supports **statistical hypothesis tests** (for example two-sample tests) to validate whether two datasets come from the same distribution.
    This is useful for detecting **data drift** between training and serving environments.
    See [Hypothesis Testing](https://pandera.readthedocs.io/en/stable/hypothesis.html).

### Writing tests for your schemas

To ensure your schemas match your actual data, write tests.

Create `src/spaceflights_pandera/schemas/test_schemas.py`:

```python
"""Test utilities for validating schemas against sample data.

Run with: python -m pytest src/spaceflights_pandera/schemas/test_schemas.py -v
"""
import pandas as pd
import pytest
from pandera.errors import SchemaError, SchemaErrors

from .raw import companies_schema


class TestRawSchemas:
    """Test raw data schemas against sample data."""

    def test_companies_schema_valid_data(self):
        """Test companies schema accepts valid data."""
        valid_data = pd.DataFrame({
            "id": [1, 2, 3],
            "company_rating": ["100%", "50%", "75%"],
            "company_location": ["USA", "UK", "France"],
            "total_fleet_count": [10.0, 5.0, 8.0],
            "iata_approved": ["t", "f", "t"],
        })

        validated = companies_schema.validate(valid_data)
        assert validated.shape == valid_data.shape

    def test_companies_schema_rejects_invalid_iata(self):
        """Test companies schema rejects invalid IATA values."""
        invalid_data = pd.DataFrame({
            "id": [1],
            "company_rating": ["100%"],
            "company_location": ["USA"],
            "total_fleet_count": [10.0],
            "iata_approved": ["invalid"],  # Should be 't' or 'f'
        })

        with pytest.raises(SchemaErrors) as exc_info:
            companies_schema.validate(invalid_data, lazy=True)

        assert "iata_approved" in str(exc_info.value)

    def test_companies_schema_rejects_negative_fleet(self):
        """Test companies schema rejects negative fleet counts."""
        invalid_data = pd.DataFrame({
            "id": [1],
            "company_rating": ["100%"],
            "company_location": ["USA"],
            "total_fleet_count": [-5.0],  # Must be >= 0
            "iata_approved": ["t"],
        })

        with pytest.raises(SchemaErrors):
            companies_schema.validate(invalid_data, lazy=True)
```

Run your tests:

```bash
python -m pytest src/spaceflights_pandera/schemas/test_schemas.py -v
```


## Further reading

* [Pandera documentation](https://pandera.readthedocs.io/)
* [Kedro hooks documentation](https://docs.kedro.org/en/stable/hooks/introduction.html)
* [Lazy validation](https://pandera.readthedocs.io/en/stable/lazy_validation.html)
* [Custom checks](https://pandera.readthedocs.io/en/stable/checks.html)
* [Multi-backend support](https://pandera.readthedocs.io/en/stable/ecosystem.html) - Pandera also validates data in Dask, Polars, Modin, and PySpark
* [Ibis backend](https://pandera.readthedocs.io/en/stable/ibis.html) - Validate data with Ibis for cross-database compatibility

For a declarative approach to validation using catalog metadata, see the community-maintained [kedro-pandera plugin](https://github.com/Galileo-Galilei/kedro-pandera) (last updated July 2024).
