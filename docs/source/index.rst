.. Kedro documentation master file, created by
   sphinx-quickstart on Mon Dec 18 11:31:24 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


.. image:: https://raw.githubusercontent.com/kedro-org/kedro/develop/static/img/kedro_banner.png
    :alt: Kedro logo
    :class: kedro-logo

Welcome to Kedro's documentation!
=============================================

.. image:: https://img.shields.io/circleci/build/github/kedro-org/kedro/main?label=main
    :target: https://circleci.com/gh/kedro-org/kedro/tree/main
    :alt: CircleCI - Main Branch

.. image:: https://img.shields.io/circleci/build/github/kedro-org/kedro/develop?label=develop
    :target: https://circleci.com/gh/kedro-org/kedro/tree/develop
    :alt: CircleCI - Develop Branch

.. image:: https://img.shields.io/badge/license-Apache%202.0-blue.svg
    :target: https://opensource.org/licenses/Apache-2.0
    :alt: License is Apache 2.0

.. image:: https://img.shields.io/badge/python-3.7%20%7C%203.8%20%7C%203.9%20%7C%203.10-blue.svg
    :target: https://pypi.org/project/kedro/
    :alt: Python version 3.7, 3.8, 3.9, 3.10

.. image:: https://badge.fury.io/py/kedro.svg
    :target: https://pypi.org/project/kedro/
    :alt: PyPI package version

.. image:: https://img.shields.io/conda/vn/conda-forge/kedro.svg
    :target: https://anaconda.org/conda-forge/kedro
    :alt: Conda package version

.. image:: https://readthedocs.org/projects/kedro/badge/?version=stable
    :target: https://kedro.readthedocs.io/
    :alt: Docs build status

.. image:: https://img.shields.io/discord/778216384475693066.svg?color=7289da&label=Kedro%20Discord&logo=discord&style=flat-square
    :target: https://discord.gg/akJDeVaxnB
    :alt: Discord Server

.. image:: https://img.shields.io/badge/code%20style-black-black.svg
    :target: https://github.com/psf/black
    :alt: Code style is Black

.. toctree::
   :maxdepth: 2
   :caption: Introduction

   introduction/introduction


.. toctree::
   :maxdepth: 2
   :caption: Get started

   get_started/prerequisites
   get_started/install
   get_started/hello_kedro

.. toctree::
   :maxdepth: 2
   :caption: Make a project

   get_started/new_project
   get_started/example_project
   get_started/starters
   get_started/standalone_use_of_datacatalog

.. toctree::
   :maxdepth: 2
   :caption: Tutorial

   tutorial/spaceflights_tutorial
   tutorial/tutorial_template
   tutorial/set_up_data
   tutorial/create_pipelines
   tutorial/visualise_pipeline
   tutorial/namespace_pipelines
   tutorial/set_up_experiment_tracking
   tutorial/package_a_project

.. toctree::
   :maxdepth: 2
   :caption: Kedro project setup

   kedro_project_setup/dependencies
   kedro_project_setup/configuration
   kedro_project_setup/session
   kedro_project_setup/settings

.. toctree::
   :maxdepth: 2
   :caption: Data Catalog

   data/data_catalog
   data/kedro_io

.. toctree::
   :maxdepth: 2
   :caption: Nodes and pipelines

   nodes_and_pipelines/nodes
   nodes_and_pipelines/pipeline_introduction
   nodes_and_pipelines/modular_pipelines
   nodes_and_pipelines/micro_packaging
   nodes_and_pipelines/run_a_pipeline
   nodes_and_pipelines/slice_a_pipeline

.. toctree::
   :maxdepth: 2
   :caption: Extend Kedro

   extend_kedro/common_use_cases
   extend_kedro/hooks
   extend_kedro/custom_datasets
   extend_kedro/plugins
   extend_kedro/create_kedro_starters


.. toctree::
   :maxdepth: 2
   :caption: Logging

   logging/logging
   logging/experiment_tracking

.. toctree::
   :maxdepth: 2
   :caption: Development

   development/set_up_vscode
   development/set_up_pycharm
   development/commands_reference
   development/debugging

.. toctree::
   :maxdepth: 2
   :caption: Deployment

   deployment/deployment_guide
   deployment/single_machine
   deployment/distributed
   deployment/argo
   deployment/prefect
   deployment/kubeflow
   deployment/aws_batch
   deployment/databricks
   deployment/aws_sagemaker
   deployment/aws_step_functions
   deployment/airflow_astronomer

.. toctree::
   :maxdepth: 2
   :caption: Tools integration

   tools_integration/pyspark
   tools_integration/ipython

.. toctree::
   :maxdepth: 2
   :caption: FAQs

   faq/faq
   faq/architecture_overview
   faq/kedro_principles

.. toctree::
   :maxdepth: 2
   :caption: Resources

   resources/logos
   resources/glossary

.. toctree::
   :maxdepth: 2
   :caption: Contribute to Kedro

   contribution/contribute_to_kedro
   contribution/developer_contributor_guidelines
   contribution/backwards_compatibility
   contribution/documentation_contributor_guidelines

API documentation
=================

.. autosummary::
   :toctree:
   :caption: API documentation
   :template: autosummary/module.rst
   :recursive:

   kedro

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
