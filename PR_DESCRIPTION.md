## Description
Fixes #4813.

This PR fixes `%reload_kedro --params` when a runtime parameter value containing spaces is wrapped in single quotes, for example:

```ipython
%reload_kedro --params foo='bar baz'
```

The normal `kedro run --params` CLI path already handles values with spaces. The issue was isolated to the IPython line magic parser, which split single-quoted `--params` values before Kedro's `_split_params()` received them.

## Development notes
Updated `%reload_kedro` to normalise single-quoted `--params` values before calling IPython's `parse_argstring()`. The fix is intentionally narrow:

- it only touches the `%reload_kedro` IPython parsing path;
- it leaves the shared CLI `_split_params()` implementation unchanged;
- it preserves existing `path`, `--env`, and `--conf-source` parsing.

Added regression tests that verify `%reload_kedro` passes `{"foo": "bar baz"}` to `reload_kedro()` for:

- `--params foo='bar baz'`;
- `--params 'foo=bar baz'`;
- a full invocation with path, `--env`, `--params`, and `--conf-source`.

Added a `RELEASE.md` entry for the bug fix.

Tested with:

```powershell
.venv\Scripts\python.exe -m pytest --no-cov tests\ipython\test_ipython.py
.venv\Scripts\python.exe -m pytest -o addopts="" --cov=kedro.ipython --cov-config pyproject.toml --cov-report term-missing --cov-fail-under=0 tests\ipython\test_ipython.py
pre-commit run ruff --files kedro\ipython\__init__.py tests\ipython\test_ipython.py
pre-commit run ruff-format --files kedro\ipython\__init__.py tests\ipython\test_ipython.py
pre-commit run trailing-whitespace --files RELEASE.md kedro\ipython\__init__.py tests\ipython\test_ipython.py
pre-commit run end-of-file-fixer --files RELEASE.md kedro\ipython\__init__.py tests\ipython\test_ipython.py
.venv\Scripts\mypy.exe kedro\ipython\__init__.py --strict --allow-any-generics --no-warn-unused-ignores
```

## Developer Certificate of Origin
We need all contributions to comply with the [Developer Certificate of Origin (DCO)](https://developercertificate.org/). All commits must be signed off by including a `Signed-off-by` line in the commit message. [See our wiki for guidance](https://github.com/kedro-org/kedro/wiki/Guidelines-for-contributing-developers/).

If your PR is blocked due to unsigned commits, then you must follow the instructions under "Rebase the branch" on the GitHub Checks page for your PR. This will retroactively add the sign-off to all unsigned commits and allow the DCO check to pass.

## Checklist

- [x] Read the [contributing](https://github.com/kedro-org/kedro/blob/main/CONTRIBUTING.md) guidelines
- [x] Signed off each commit with a [Developer Certificate of Origin (DCO)](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/managing-the-commit-signoff-policy-for-your-repository)
- [ ] Opened this PR as a 'Draft Pull Request' if it is work-in-progress
- [ ] Updated the documentation to reflect the code changes
- [x] Added a description of this change in the [`RELEASE.md`](https://github.com/kedro-org/kedro/blob/main/RELEASE.md) file
- [x] Added tests to cover my changes
- [x] Checked if this change will affect Kedro-Viz, and if so, communicated that with the Viz team
