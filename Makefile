install:
	uv pip install --system -e .

clean:
	rm -rf build dist site kedro/html pip-wheel-metadata .mypy_cache .pytest_cache features/test_plugin/test_plugin.egg-info
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

install-docs-requirements:
	uv pip install -e ".[docs]"

serve-docs: install-docs-requirements
	mkdocs serve --open

build-docs: install-docs-requirements
	mkdocs build

show-docs:
	open site/index.html

linkcheck: install-docs-requirements
	# this checks: mkdocs.yml is valid, all listed pages exist, plugins are correctly configured, no broken references in nav or Markdown links (internal), broken links and images (internal, not external)
	mkdocs build --strict
	# lychee checks for broken external links in the built site, with max concurrency set to 32
	lychee --max-concurrency 32 --exclude "@.lycheeignore" site/

fix-markdownlint:
	npm install -g markdownlint-cli2
	# markdownlint rules are defined in .markdownlint.yaml
	markdownlint-cli2 --config .markdownlint.yaml --fix "docs/**/*.md"

package: clean install
	python -m pip install build && python -m build

install-test-requirements:
	uv pip install "kedro[test] @ ."

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
