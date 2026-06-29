# Implementation plan for #4813

Issue: https://github.com/kedro-org/kedro/issues/4813

## Summary

`%reload_kedro --params` fails when a runtime parameter value with spaces is wrapped in single quotes, for example:

```ipython
%reload_kedro --params foo='bar baz'
```

The normal Kedro CLI path already supports values with spaces. The bug is isolated to the IPython line magic argument parsing path.

## Affected Code

- `kedro/ipython/__init__.py`
  - `magic_reload_kedro()` uses IPython's `parse_argstring()` to parse `%reload_kedro`.
  - The `--params` argument uses `_split_params()` as its converter.
- `kedro/framework/cli/utils.py`
  - `_split_params()` correctly handles values with spaces once it receives a single `key=value` string.
- `tests/ipython/test_ipython.py`
  - Existing tests cover valid `%reload_kedro` arguments, but not single-quoted `--params` values with spaces.

## Root Cause

IPython splits the line magic argument string before Kedro's `_split_params()` receives it.

Observed locally:

```text
--params foo="bar baz"  -> {'foo': 'bar baz'}
--params "foo=bar baz"  -> {'foo': 'bar baz'}
--params foo='bar baz'  -> ScannerError
--params 'foo=bar baz'  -> parsed incorrectly
```

So the fix should be in the `%reload_kedro` parsing layer, not in the shared CLI `_split_params()` function.

## Proposed Implementation

1. Add regression tests in `tests/ipython/test_ipython.py` for:
   - `%reload_kedro --params foo='bar baz'`
   - `%reload_kedro --params 'foo=bar baz'`
   - existing double-quoted and unquoted valid cases to guard against regressions.

2. Add a small private helper in `kedro/ipython/__init__.py`, for example:

   ```python
   def _normalise_reload_kedro_params(line: str) -> str:
       ...
   ```

3. Keep the helper narrow:
   - only inspect and normalise the raw `--params` argument;
   - do not replace all `%reload_kedro` parsing with `shlex.split()`;
   - preserve existing handling for `path`, `--env`, and `--conf-source`.

4. The helper should rewrite single-quoted `--params` values into a form IPython already parses correctly, for example:

   ```text
   --params foo='bar baz'
   ```

   becomes:

   ```text
   --params "foo=bar baz"
   ```

5. Leave `_split_params()` unchanged because the normal CLI path already depends on it and its current behavior is correct.

## Validation Plan

Run:

```powershell
.venv\Scripts\python.exe -m pytest --no-cov tests\ipython\test_ipython.py
pre-commit run ruff --files kedro\ipython\__init__.py tests\ipython\test_ipython.py
pre-commit run ruff-format --files kedro\ipython\__init__.py tests\ipython\test_ipython.py
pre-commit run trailing-whitespace --files kedro\ipython\__init__.py tests\ipython\test_ipython.py
pre-commit run end-of-file-fixer --files kedro\ipython\__init__.py tests\ipython\test_ipython.py
.venv\Scripts\mypy.exe kedro\ipython\__init__.py --strict --allow-any-generics --no-warn-unused-ignores
git diff --check
```

## Notes

This issue is on Kedro's OS contribution board with status `Ready`, has no assignee, and currently has no active PR.
