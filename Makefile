install:
	pip install .

clean:
	rm -rf build dist docs/build kedro/html pip-wheel-metadata .mypy_cache .pytest_cache features/steps/test_plugin/test_plugin.egg-info kedro/datasets
	find . -regex ".*/__pycache__" -exec rm -rf {} +
	find . -regex ".*\.egg-info" -exec rm -rf {} +
	pre-commit clean || true

install-pip-setuptools:
	pip install -U "pip>=21.2" "setuptools>=65.5.1" wheel

lint:
	pre-commit run -a --hook-stage manual $(hook)

test:
	pytest --numprocesses 4 --dist loadfile

test-no-spark:
	pytest --no-cov --ignore tests/extras/datasets/spark --numprocesses 4 --dist loadfile

test-no-datasets:
	pytest --no-cov --ignore tests/extras/datasets/ --numprocesses 4 --dist loadfile

e2e-tests:
	behave

pip-compile:
	pip-compile -q -o -

secret-scan:
	trufflehog --max_depth 1 --exclude_paths trufflehog-ignore.txt .

SPHINXPROJ = Kedro

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
