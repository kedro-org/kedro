.. Kedro documentation master file, created by
   sphinx-quickstart on Mon Dec 18 11:31:24 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


.. image:: https://raw.githubusercontent.com/kedro-org/kedro/main/static/img/kedro_banner.png
    :alt: Kedro logo
    :class: kedro-logo

Welcome to Kedro's award-winning documentation!
================================================

.. image:: https://img.shields.io/github/actions/workflow/status/kedro-org/kedro/all-checks.yml?label=main
    :target: https://github.com/kedro-org/kedro/actions/workflows/all-checks.yml?query=branch%3Amain
    :alt: GitHub Actions - Main Branch

.. image:: https://img.shields.io/github/actions/workflow/status/kedro-org/kedro/all-checks.yml?branch=develop&label=develop
    :target: https://github.com/kedro-org/kedro/actions/workflows/all-checks.yml?query=branch%3Adevelop
    :alt: GitHub Actions - Develop Branch

.. image:: https://img.shields.io/badge/license-Apache%202.0-blue.svg
    :target: https://opensource.org/license/apache2-0-php/
    :alt: License is Apache 2.0

.. image:: https://img.shields.io/badge/3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg
    :target: https://pypi.org/project/kedro/
    :alt: Python version 3.9, 3.10, 3.11, 3.12, 3.13

.. image:: https://badge.fury.io/py/kedro.svg
    :target: https://pypi.org/project/kedro/
    :alt: PyPI package version

.. image:: https://img.shields.io/conda/vn/conda-forge/kedro.svg
    :target: https://anaconda.org/conda-forge/kedro
    :alt: Conda package version

.. image:: https://readthedocs.org/projects/kedro/badge/?version=stable
    :target: https://docs.kedro.org/
    :alt: Docs build status

.. image:: https://img.shields.io/badge/slack-chat-blueviolet.svg?label=Kedro%20Slack&logo=slack
    :target: https://slack.kedro.org
    :alt: Kedro's Slack organisation

.. image:: https://img.shields.io/badge/slack-archive-blueviolet.svg?label=Kedro%20Slack%20
    :target: https://linen-slack.kedro.org/
    :alt: Kedro's Slack archive

.. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
    :target: https://github.com/astral-sh/ruff
    :alt: Linted and Formatted with Ruff

.. image:: https://bestpractices.coreinfrastructure.org/projects/6711/badge
    :target: https://bestpractices.coreinfrastructure.org/projects/6711
    :alt: OpenSSF Best Practices Badge Program

.. toctree::
   :maxdepth: 2
   :caption: Learn about Kedro

   introduction/index.md
   get_started/index.md
   course/index.md

.. toctree::
   :maxdepth: 2
   :caption: Tutorial and basic Kedro usage

   tutorial/spaceflights_tutorial.md
   visualisation/index.md
   notebooks_and_ipython/index.md
   resources/index.md

.. toctree::
   :maxdepth: 2
   :caption: Kedro projects

   starters/index.md
   configuration/index.md
   data/index.md
   nodes_and_pipelines/index.md
   configuration/telemetry.md

.. toctree::
   :maxdepth: 2
   :caption: Integrations

   integrations/pyspark_integration.md
   integrations/mlflow.md
   integrations/kedro_dvc_versioning.md
   integrations/deltalake_versioning.md

.. toctree::
   :maxdepth: 2
   :caption: Advanced usage

   kedro_project_setup/index.md
   extend_kedro/index.md
   hooks/index.md
   logging/index.md
   development/index.md
   deployment/index.md

.. toctree::
   :maxdepth: 2
   :caption: Contribute to Kedro

   contribution/index.md

API documentation
=================

.. autosummary::
   :toctree: api
   :caption: API documentation
   :template: autosummary/module.rst
   :recursive:

   kedro

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
