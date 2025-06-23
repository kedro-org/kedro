install:
	uv pip install --system -e .

clean:
	rm -rf build dist docs/build kedro/html pip-wheel-metadata .mypy_cache .pytest_cache features/steps/test_plugin/test_plugin.egg-info
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

build-docs:
	uv pip install -e ".[docs]"
	./docs/build-docs.sh "docs"

show-docs:
	open docs/build/html/index.html

linkcheck:
	uv pip install --system "kedro[docs] @ ."
	./docs/build-docs.sh "linkcheck"

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
	echo "git interpret-trailers --if-exists doNothing \c" >> .git/hooks/commit-msg
	echo '--trailer "Signed-off-by: $$(git config user.name) <$$(git config user.email)>" \c' >> .git/hooks/commit-msg
	echo '--in-place "$$1"' >> .git/hooks/commit-msg
	chmod +x .git/hooks/commit-msg

language-lint: dir ?= docs

# Pattern rule to allow "make language-lint dir=doc/source/hooks>" syntax
language-lint:
	vale $(dir)
