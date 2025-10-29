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
code example here
```

Register your custom hook in `src/spaceflights_great_expectations/settings.py`:

```py
from spaceflights_great_expectations.hooks import DataValidationHooks

HOOKS = (DataValidationHooks(),)
```

## Further Reading

  - [Kedro Data Catalog](../catalog-data/data_catalog.md)
  - [Kedro Hooks](../extend/hooks/introduction.md)
  - [Kedro Pipelines](../build/pipeline_introduction.md)
  - [Learn Great Expectations](https://docs.greatexpectations.io/docs/reference/learn/)
  - [Great Expectations GitHub Repository](https://github.com/great-expectations/great_expectations)
