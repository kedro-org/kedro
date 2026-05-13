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

## Kedro-specific rule guidance

### `kedro-dynamic-import`

Fires on `importlib.import_module($X)` where the argument is not a string
literal. Kedro uses dynamic imports extensively and legitimately — dataset
class paths, pipeline modules, and settings are all loaded this way from
project config.

- If the module path originates from `catalog.yml`, `settings.py`, or other
  **project developer-authored config**, classify as
  `project_developer_responsibility`.
- If the module path could be influenced by **external runtime input** with no
  validation (e.g. user-supplied parameters flowing into an import call),
  classify as `candidate_kedro_vulnerability`.
- If the call is inside Kedro framework code and the input path is not
  validated or allowlisted before importing, classify as
  `candidate_kedro_vulnerability`.
- In most cases this will be `false_positive_or_informational` — confirm by
  tracing where the argument originates.

### `kedro-yaml-unsafe-load`

Fires on `yaml.load()` without a safe Loader. Kedro should always use
`yaml.safe_load()` or an explicit safe Loader in framework code, because YAML
config files are user-controlled data.

- If found in **Kedro framework code** (`kedro/` package): classify as
  `candidate_kedro_vulnerability` — unsafe YAML deserialization on
  user-controlled config can execute arbitrary Python objects.
- If found in **project developer code**: classify as
  `project_developer_responsibility`.
- `yaml.safe_load`, `yaml.SafeLoader`, `yaml.FullLoader`, `yaml.CLoader`, and
  `yaml.CSafeLoader` are all safe and excluded by the rule automatically.
