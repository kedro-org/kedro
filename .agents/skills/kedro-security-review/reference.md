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

Severity determines how the finding is surfaced to the user (the skill itself
does not enforce anything — it only reports):

- **ERROR severity** — the rule has high confidence and critical impact (e.g.
    RCE, arbitrary code execution, credential exposure). **Flag prominently and
    recommend fixing before the code is merged or released.** Suggest discussing
    with maintainers as part of the PR review. If the same pattern is later
    confirmed to exist in an already-released version, that is when a Security
    Advisory becomes relevant — not at PR time.
- **WARNING severity** — plausible risk but lower confidence or limited impact.
    **Recommend investigating and fixing, but it does not need to block the
    merge.** Suggest opening a maintainer follow-up issue if it can't be resolved
    in the current PR.

### `project_developer_responsibility`

Use when the risky behavior is explicitly authored code rather than Kedro
framework behavior.

**Suggested next step:** note in the report only; the project owner must fix or
accept the risk in their own codebase.

### `deployment_or_environment_issue`

Use when the real control point is infrastructure, secrets management, network
policy, or other deployment-owned controls.

**Suggested next step:** flag for ops / deployment documentation (secrets store,
network policy, IAM, etc.) — not actionable in Kedro framework code.

### `false_positive_or_informational`

Use when the rule fired but the surrounding code does not imply a meaningful
issue in context.

**Suggested next step:** suppress in future scans (`.semgrepignore` or
rule-specific nosemgrep) if the same hit recurs; otherwise omit from the
actionable findings list.

### `needs_manual_review`

Use when deeper context is required before you can classify confidently.

**Suggested next step:** open a follow-up issue or assign a human reviewer;
do not auto-dismiss.

## Manual review checks

Run these after Semgrep, regardless of whether any rule fired.
Semgrep only covers known patterns. These checks catch the unknown ones.

Apply the same path exclusions as the Semgrep scan when grepping or searching:
skip `tests/`, `docs/`, `features/`, and `.agents/`. Otherwise these checks
will re-flag hits in paths the Semgrep phase already filtered out.

### 1. New third-party functions that accept config dicts

For every function that takes a `dict` from user config (YAML, env var, API),
ask: **does this library treat any key as a callable specification?**

Known dangerous key conventions:

- `()` — Python logging `dictConfig` factory callable
- `class` — Python logging `dictConfig` handler/formatter class (fully-qualified
    dotted path, resolved via dynamic import)
- `py/object`, `py/reduce` — jsonpickle
- `!!python/object` — yaml.load without safe loader
- `_target_` — Hydra/OmegaConf structured config instantiation
- `type` — Kedro catalog (intentional, project developer responsibility)

If a new dependency uses any of these conventions and Kedro passes it a
user-controlled dict without validation, classify as
`candidate_kedro_vulnerability`.

### 2. New environment variable → execution paths

Search for `os.environ.get` / `os.getenv` / `os.environ[` that produce a value
used as: a file path that is then loaded and executed, a module path passed to
import machinery, or a dict key used in config resolution.

If any new env var creates a path from external string → Python execution with
no validation, classify as `candidate_kedro_vulnerability`.

### 3. Path construction from any external string

For any new code that constructs a file path from a string that originates
outside Kedro's own defaults (CLI arg, env var, catalog config, API param):

- Check whether `..` or absolute path segments are rejected before use
- If not: `needs_manual_review` at minimum

### 4. Security suppression comments

Search scanned files for comments that suppress security scanner findings:
- `# nosec` (Bandit)
- `# nosemgrep` (Semgrep)
- `# type: ignore[` used alongside a `nosec` or `nosemgrep` on the same line
  (occasionally combined to silence both type-checker and security scanner)

A suppression comment makes the flagged code invisible to the scanner. If the
suppression is unjustified or outdated, it silently masks a real vulnerability.

For every match, classify as `needs_manual_review` and ask the reviewer to
verify:
1. The suppression is still necessary — the underlying issue has not been
   refactored away.
2. The risk is documented — there is an adjacent comment explaining **why** the
   suppression is safe.
3. There is no code-level fix that would remove the need for suppression
   entirely.

**PR mode — new vs. pre-existing suppressions:**

In PR mode, compare each hit against the PR diff (`gh pr diff <number>`).
- A suppression whose line appears in the diff (added or modified) is a **new
  suppression** — flag it with higher priority. New suppressions in a PR are
  the primary concern: they indicate that a contributor is actively silencing a
  scanner finding on code that is about to be merged.
- A suppression on a line not in the diff is **pre-existing** — still flag it
  as `needs_manual_review`, but note that it predates this PR so it may be
  tracked separately (e.g. in a follow-up cleanup issue).

In full-codebase mode, all suppressions are treated equally (there is no diff
to distinguish new from old).

## General ruleset guidance

### `p/security-audit`

_Broad OWASP-style checks — injection, unsafe calls, dangerous APIs._

Expect high volume; most findings on a framework codebase are
`false_positive_or_informational`. Apply standard classification buckets.

### `p/secrets`

_Detects hardcoded credentials, tokens, and API keys in source files._

The Semgrep scan already excludes `tests/`, `docs/`, `features/`, and
`.agents/` via `--exclude`, so any finding from `p/secrets` is in production
code. Triage in order: (1) check for a placeholder value
(`"YOUR_API_KEY"`, `"xxx"`, `"<token>"`) — classify as
`false_positive_or_informational`; (2) if the string looks like a real secret,
classify as `needs_manual_review`. (If a finding does appear under an excluded
path, treat it as a scan misconfiguration rather than a real signal.)

### `p/python`

_General Python anti-patterns — unsafe deserialization, shell injection, insecure stdlib use._

Rarely indicates Kedro vulnerabilities. One exception worth checking: `pickle`
usage — if Kedro framework code is deserialising untrusted data, classify as
`candidate_kedro_vulnerability`; if it is a developer-opted-in dataset (e.g.
`PickleDataset`), classify as `project_developer_responsibility`.

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

### `kedro-taint-config-to-callable-sink`

Fires when a value from `os.environ`, YAML loading, or JSON loading flows into
a Python callable-instantiation sink. This covers the full class of
data→executable vulnerabilities: `dictConfig` `()` keys, `pickle` `__reduce__`,
`eval`/`exec`, etc.

Sinks covered: `logging.config.dictConfig`, `logging.config.fileConfig`,
`pickle.loads`, `marshal.loads`, `eval`, `exec`.

Note: `yaml.safe_load` is intentionally included as a taint source alongside
`yaml.load` and `os.environ`. Safe YAML parsing prevents arbitrary object
deserialisation at parse time, but it does not prevent the *parsed dict* from
containing keys (such as `()`) that a downstream sink like `dictConfig` will
interpret as callable factories. The risk is in the sink, not the loader — so
any config data reaching a callable sink is tracked regardless of how it was
parsed.

- If the tainted value flows into any sink with no sanitization and the source
    is user-controllable at runtime (env var, API, external file): classify as
    `candidate_kedro_vulnerability`.
- If the source is a framework-internal default file with no external override
    path: classify as `false_positive_or_informational`.
- If the source is developer-authored project config not reachable by external
    users: classify as `project_developer_responsibility`.
- Trace whether the taint path crosses a sanitizer (e.g. `()` key rejection,
    allowlist check) before classifying.

### `kedro-taint-string-param-to-path`

Fires on any explicitly `str`-annotated parameter flowing into a pathlib `/`
operator. Expect moderate-to-high volume; most hits are legitimate path
operations in CLI scaffolding and config resolution code. Untyped parameters
are intentionally out of scope to limit noise — flag any untyped string
parameters reaching path sinks as `needs_manual_review` instead.

Triage steps:

1. Trace where the `str` parameter originates. If it comes from developer-authored
    config (`catalog.yml`, `settings.py`, project code), classify as
    `project_developer_responsibility`.
1. If the parameter can be set by an untrusted external caller (API input, CI
    trigger, multi-tenant platform), classify as `candidate_kedro_vulnerability`
    if there is no `..` / absolute-path check anywhere in the call chain, or
    `deployment_or_environment_issue` if the deployment is expected to sanitize.
1. If the path operation is a read-only probe (`.exists()`, `.is_absolute()`,
    `.is_dir()`), classify as `false_positive_or_informational`.
1. If the flagged function is itself a sanitizer (checking for `..` or absolute
    paths), classify as `false_positive_or_informational`.

### `kedro-subprocess-shell-injection`

Fires on `subprocess.$FUNC($CMD, ..., shell=True)` where the command is not a
plain string literal. This includes:

- Variable-derived strings (most common case — possible RCE)
- List-form calls (`subprocess.run([cmd], shell=True)`) — flagged because
    Python only passes the first list element to the shell, which is rarely
    intentional and easy to misuse, even when the list contents are literals

Triage steps:

1. **List with only literal elements** (e.g. `subprocess.run(["ls", "-l"], shell=True)`): code smell but not exploitable in isolation. Classify as
    `false_positive_or_informational`; recommend converting to `shell=False`
    with the same list.
1. Trace where `$CMD` originates. If it is a hardcoded string assembled only
    from framework-internal defaults (no external input), classify as
    `false_positive_or_informational`.
1. If `$CMD` is constructed from a developer-authored project value
    (e.g. a Kedro node name, pipeline name, or catalog key provided in
    `catalog.yml`), classify as `project_developer_responsibility`.
1. If `$CMD` can be influenced by an untrusted external caller (env var, API
    input, CI trigger, user-supplied CLI flag) with no allowlist or escaping,
    classify as `candidate_kedro_vulnerability` at ERROR severity.
1. If the origin is unclear without deeper runtime context, classify as
    `needs_manual_review`.

Note: `shell=False` with an explicit list argument (`[cmd, arg1, arg2]`) is
always safe regardless of where the arguments come from, because the shell
never interprets them. The rule only fires when `shell=True` is present.

### `kedro-yaml-unsafe-load`

Fires on `yaml.load()` without a safe Loader. Kedro should always use
`yaml.safe_load()` or an explicit safe Loader in framework code, because YAML
config files are user-controlled data.

- If found in **Kedro framework code** (`kedro/` package): classify as
    `candidate_kedro_vulnerability` — unsafe YAML deserialization on
    user-controlled config can execute arbitrary Python objects.
- If found in **project developer code**: classify as
    `project_developer_responsibility`.
- `yaml.safe_load()` is a separate function and is never matched by this rule
    (the pattern is `yaml.load(...)` only). For `yaml.load(...)`, safe loaders
    are excluded via `pattern-not` for both the fully-qualified forms
    (`Loader=yaml.SafeLoader`, `Loader=yaml.CSafeLoader`, and positional
    `yaml.SafeLoader` / `yaml.CSafeLoader`) and the unqualified forms used after
    `from yaml import SafeLoader` (`Loader=SafeLoader`, `Loader=CSafeLoader`,
    and positional `SafeLoader` / `CSafeLoader`).
- `yaml.CLoader` is **not** safe — it is the C extension of `FullLoader`, not
    `SafeLoader`. Do not treat `yaml.load(..., Loader=yaml.CLoader)` as safe; the
    rule will fire on it and it should be classified as
    `candidate_kedro_vulnerability` in Kedro framework code.
- `yaml.FullLoader` is **not** excluded — it is not safe for user-controlled
    data (can deserialise Python objects via `!!python/object/apply`). Treat any
    `yaml.load(..., Loader=yaml.FullLoader)` in Kedro framework code as
    `candidate_kedro_vulnerability`.
