# How to validate data in your Kedro workflow using Great Expectations

Great Expectations (GE) is an open-source data quality framework that helps you validate, document, and profile your data.
It allows you to define expectations—assertions about your data’s structure and content—and verify that these hold true at runtime.

## Prerequisites

You will need the following:

- A working Kedro project.
    - The examples in this document assume the `spaceflights-pandas` starter.
If you're unfamiliar with the Spaceflights project, check out our tutorial.

- Great Expectations installed into your project.

Show how to install and such.

## Use cases

- Do validation two ways:
    - As a Kedro hook
    - As part of a pipeline run

Show examples for both using spaceflights.


## Further Reading

- **Kedro Documentation**
  - [Data Catalog]()
  - [Hooks]()
  - [Pipeline Architecture]()
  - [Learn Great Expectations](https://docs.greatexpectations.io/docs/reference/learn/)
  - [Great Expectations GitHub Repository](https://github.com/great-expectations/great_expectations)
