# Hooks

Hooks are a mechanism to add extra behaviour to Kedro's main execution in an easy and consistent manner. Some examples might include:

- Adding a log statement after the data catalog is loaded.
- Adding data validation to the inputs before a node runs, and to the outputs after a node has run. This makes it possible to integrate with other tools like [Great-Expectations](https://docs.greatexpectations.io/en/latest/).
- Adding machine learning metrics tracking, e.g. using [MLflow](https://mlflow.org/), throughout a pipeline run.

- [Introduction](introduction.md)
- [Common Use Cases](common_use_cases.md)
- [Examples](examples.md)