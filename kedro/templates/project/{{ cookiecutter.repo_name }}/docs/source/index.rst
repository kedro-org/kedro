.. {{ cookiecutter.python_package }} documentation master file, created by sphinx-quickstart.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to project {{ cookiecutter.python_package }}'s API docs!
=============================================

.. toctree::
   :maxdepth: 4

Getting Started
---------------

To generate API documentation from your project's docstrings, run:

.. code-block:: bash

   pip install -e ".[docs]"
   sphinx-apidoc -o docs/source src/{{ cookiecutter.python_package }}
   sphinx-build -b html docs/source docs/build/html

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
