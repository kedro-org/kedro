# Spec delta

## Add

## R0001: PyPI wheel excludes kedro_benchmarks package

- Theme: packaging

The published Kedro PyPI wheel and sdist must not include the `kedro_benchmarks`
package. That code is for internal ASV performance benchmarks only and remains
available in the source repository for CI and maintainers.

### Checks

- [ ] `[tool.setuptools.packages.find]` in `pyproject.toml` excludes `kedro_benchmarks*`
- [ ] A built wheel does not contain any `kedro_benchmarks` package paths
- [ ] Unit tests in `tests/` pass after the packaging change
- [ ] `kedro_benchmarks/` remains in the repository and `asv.conf.json` still references it as the benchmark directory

## Modify

## Remove
