# kedro.inspection

::: kedro.inspection
    options:
      docstring_style: google
      members: false
      show_source: false

| Name                                                                              | Type      | Description                                                            |
| --------------------------------------------------------------------------------- | --------- | ---------------------------------------------------------------------- |
| [`get_project_snapshot`](#kedro.inspection.get_project_snapshot)                  | Function  | Return a read-only snapshot of a Kedro project.                        |
| [`validate_grouping`](#kedro.inspection.grouping.validate_grouping)               | Function  | Check that a node grouping can run with each group as a separate task. |
| [`GroupingValidationResult`](#kedro.inspection.grouping.GroupingValidationResult) | Dataclass | Outcome of `validate_grouping`.                                        |
| [`GroupingIssue`](#kedro.inspection.grouping.GroupingIssue)                       | Dataclass | A problem found in a node grouping.                                    |
| [`GroupingValidationError`](#kedro.inspection.grouping.GroupingValidationError)   | Exception | Raised by `raise_if_failed` when a grouping has errors.                |

::: kedro.inspection.get_project_snapshot
    options:
      show_source: true

::: kedro.inspection.grouping.validate_grouping
    options:
      show_source: true

::: kedro.inspection.grouping.GroupingValidationResult
    options:
      show_source: true

::: kedro.inspection.grouping.GroupingIssue
    options:
      show_source: true

::: kedro.inspection.grouping.GroupingValidationError
    options:
      show_source: true
