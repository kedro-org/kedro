install:
	uv pip install --system -e .

clean:
	rm -rf build dist site kedro/html pip-wheel-metadata .mypy_cache .pytest_cache features/steps/test_plugin/test_plugin.egg-info
	find . -regex ".*/__pycache__" -exec rm -rf {} +
	find . -regex ".*\.egg-info" -exec rm -rf {} +
	pre-commit clean || true

lint:
	pre-commit run -a --hook-stage manual $(hook)
	mypy kedro --strict --allow-any-generics --no-warn-unused-ignores
test:
	pytest --numprocesses 4 --dist loadfile

show-coverage:
	coverage html --show-contexts || true
	open htmlcov/index.html

e2e-tests:
	behave --tags=-skip

e2e-tests-fast: export BEHAVE_LOCAL_ENV=TRUE
e2e-tests-fast:
	behave --tags=-skip --no-capture

pip-compile:
	pip-compile -q -o -

serve-docs:
	uv pip install -e ".[docs]"
	mkdocs serve

build-docs:
	uv pip install -e ".[docs]"
	mkdocs build

show-docs:
	open site/index.html

linkcheck:
	uv pip install -e ".[docs]"
	mkdocs build --strict
	vale docs
	linkchecker site/

package: clean install
	python -m pip install build && python -m build

install-test-requirements:
	python -m pip install "uv==0.4.29"
	uv pip install --system "kedro[test] @ ."

install-pre-commit:
	pre-commit install --install-hooks

uninstall-pre-commit:
	pre-commit uninstall

print-python-env:
	@./tools/print_env.sh

databricks-build:
	python -m pip install build && python -m build
	python ./tools/databricks_build.py

sign-off:
	echo "git inthttps://github.com/kedro-org/kedro/pull/4647/files#diff-26a89fcd97e55b24ac6c327e233357b2af642d3925075fcd8b31794085e654faerpret-trailers --if-exists doNothing \c" >> .git/hooks/commit-msg
	echo '--trailer "Signed-off-by: $$(git config user.name) <$$(git config user.email)>" \c' >> .git/hooks/commit-msg
	echo '--in-place "$$1"' >> .git/hooks/commit-msg
	chmod +x .git/hooks/commit-msg

language-lint: dir ?= docs

# Pattern rule to allow "make language-lint dir=doc/source/hooks>" syntax
language-lint:
	vale $(dir)
