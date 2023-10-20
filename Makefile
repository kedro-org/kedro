install:
	pip install -e .

clean:
	rm -rf build dist docs/build kedro/html pip-wheel-metadata .mypy_cache .pytest_cache features/steps/test_plugin/test_plugin.egg-info
	find . -regex ".*/__pycache__" -exec rm -rf {} +
	find . -regex ".*\.egg-info" -exec rm -rf {} +
	pre-commit clean || true

lint:
	pre-commit run -a --hook-stage manual $(hook)
test:
	pytest --numprocesses 4 --dist loadfile

e2e-tests:
	behave --tags=-skip

pip-compile:
	pip-compile -q -o -

secret-scan:
	trufflehog --max_depth 1 --exclude_paths trufflehog-ignore.txt .

build-docs:
	pip install -e ".[docs]"
	./docs/build-docs.sh "docs"

show-docs:
	open docs/build/html/index.html

linkcheck:
	pip install -e ".[docs]"
	./docs/build-docs.sh "linkcheck"

package: clean install
	python -m pip install build && python -m build

install-test-requirements:
# pip==23.2 breaks pip-tools<7.0, and pip-tools>=7.0 does not support Python 3.7
# pip==23.3 breaks dependency resolution
	python -m pip install -U "pip>=21.2,<23.2"
	pip install .[test]

install-pre-commit: install-test-requirements
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
