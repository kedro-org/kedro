install: build-docs
	cp -r docs/build/html kedro
	pip install .

clean:
	rm -rf build dist docs/build kedro/html pip-wheel-metadata
	find . -regex ".*/__pycache__" -exec rm -rf {} +
	find . -regex ".*\.egg-info" -exec rm -rf {} +

install-pip-setuptools:
	python -m pip install -U "pip>=18.0, <19.0" "setuptools>=38.0, <39.0" wheel

legal:
	python tools/license_and_headers.py

lint:
	isort
	pylint -j 0 --disable=unnecessary-pass kedro
	pylint -j 0 --disable=missing-docstring,redefined-outer-name,no-self-use,invalid-name tests
	pylint -j 0 --disable=missing-docstring,no-name-in-module features
	pylint -j 0 extras
	flake8 kedro tests features extras --exclude kedro/template*
	mypy --allow-redefinition --ignore-missing-imports kedro tests features extras

test:
	pytest tests

e2e-tests:
	behave

SPHINXPROJ = Kedro

build-docs:
	./docs/build-docs.sh

devserver: build-docs
	cd docs && npm install && npm start

package: clean install
	python setup.py sdist bdist_wheel
