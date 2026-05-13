# Kedro findings triage

Use this after the Semgrep phase completes.

The point is not to repeat Semgrep output. The point is to decide whether each
finding is actually a Kedro issue.

## Classification buckets

### `candidate_kedro_vulnerability`

Use when the finding points to behavior in Kedro framework code where:
- data may become executable behavior
- Kedro appears to use unsafe deserialization on user-controlled input
- Kedro appears to bypass or fail a documented safety restriction
- Kedro framework behavior may expose credentials or secrets unintentionally

### `project_developer_responsibility`

Use when the risky behavior is explicitly authored code rather than Kedro
framework behavior.

### `deployment_or_environment_issue`

Use when the real control point is infrastructure, secrets management, network
policy, or other deployment-owned controls.

### `false_positive_or_informational`

Use when the rule fired but the surrounding code does not imply a meaningful
issue in context.

### `needs_manual_review`

Use when deeper context is required before you can classify confidently.

## Questions to ask

- Is this Kedro framework code or intentionally authored project code?
- Is data being interpreted as executable behavior?
- Would fixing this belong to Kedro maintainers, project developers, or
  deployment managers?
- Is this a real security boundary violation or only a risky coding pattern?
