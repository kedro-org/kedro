# kedro.inspection

::: kedro.inspection
    options:
      docstring_style: google
      members: false
      show_source: false

| Name                                                                                      | Type      | Description                                                            |
| ----------------------------------------------------------------------------------------- | --------- | ---------------------------------------------------------------------- |
| [`get_project_snapshot`](#kedro.inspection.get_project_snapshot)                          | Function  | Return a read-only snapshot of a Kedro project.                        |
| [`validate_deployment_grouping`](#kedro.inspection.grouping.validate_deployment_grouping) | Function  | Check that a node grouping can run with each group as a separate task. |
| [`DeploymentGroupingResult`](#kedro.inspection.grouping.DeploymentGroupingResult)         | Dataclass | Outcome of `validate_deployment_grouping`.                             |
| [`DeploymentGroupingIssue`](#kedro.inspection.grouping.DeploymentGroupingIssue)           | Dataclass | A problem found when checking a node grouping for deployment.          |
| [`DeploymentGroupingError`](#kedro.inspection.grouping.DeploymentGroupingError)           | Exception | Raised by `raise_if_failed` when a grouping has errors.                |

::: kedro.inspection.get_project_snapshot
    options:
      show_source: true

::: kedro.inspection.grouping.validate_deployment_grouping
    options:
      show_source: true

::: kedro.inspection.grouping.DeploymentGroupingResult
    options:
      show_source: true

::: kedro.inspection.grouping.DeploymentGroupingIssue
    options:
      show_source: true

::: kedro.inspection.grouping.DeploymentGroupingError
    options:
      show_source: true
