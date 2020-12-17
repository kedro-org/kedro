![Kedro Logo Banner](https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/static/img/kedro_banner.png)

[![Python version](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8-blue.svg)](https://pypi.org/project/kedro/) [![PyPI version](https://badge.fury.io/py/kedro.svg)](https://pypi.org/project/kedro/) [![Conda version](https://img.shields.io/conda/vn/conda-forge/kedro.svg)](https://anaconda.org/conda-forge/kedro) [![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/quantumblacklabs/kedro/blob/master/LICENSE.md) [![Discourse users](https://img.shields.io/discourse/users?server=https%3A%2F%2Fdiscourse.kedro.community%2F)](https://discourse.kedro.community/) ![CircleCI - Master Branch](https://img.shields.io/circleci/build/github/quantumblacklabs/kedro/master?label=master) ![Develop Branch Build](https://img.shields.io/circleci/build/github/quantumblacklabs/kedro/develop?label=develop) [![Documentation](https://readthedocs.org/projects/kedro/badge/?version=stable)](https://kedro.readthedocs.io/)


## What is Kedro?

Kedro is an open-source Python framework for creating reproducible, maintainable and modular data science code. It borrows concepts from software engineering and applies them to machine-learning code; applied concepts include modularity, separation of concerns and versioning.


## How do I install Kedro?

To install Kedro from the Python Package Index (PyPI) simply run:

```
pip install kedro
```

It is also possible to install Kedro using `conda`:

```
conda install -c conda-forge kedro
```

Our [Get Started guide](https://kedro.readthedocs.io/en/stable/02_get_started/01_prerequisites.html) contains full installation instructions, and includes how to set up Python virtual environments.


## What are the main features of Kedro?

![Kedro-Viz Pipeline Visualisation](https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/static/img/pipeline_visualisation.png)
*A pipeline visualisation generated using [Kedro-Viz](https://github.com/quantumblacklabs/kedro-viz)*


| Feature | What is this? |
|----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Project Template | A standard, modifiable and easy-to-use project template based on [Cookiecutter Data Science](https://github.com/drivendata/cookiecutter-data-science/). |
| Data Catalog | A series of lightweight data connectors used to save and load data across many different file formats and file systems, including local and network file systems, cloud object stores, and HDFS. The Data Catalog also includes data and model versioning for file-based systems. |
| Pipeline Abstraction | Automatic resolution of dependencies between pure Python functions and data pipeline visualisation using [Kedro-Viz](https://github.com/quantumblacklabs/kedro-viz). |
| Coding Standards | Test-driven development using [`pytest`](https://github.com/pytest-dev/pytest), produce well-documented code using [Sphinx](http://www.sphinx-doc.org/en/master/), create linted code with support for [`flake8`](https://github.com/PyCQA/flake8), [`isort`](https://github.com/timothycrosley/isort) and [`black`](https://github.com/psf/black) and make use of the standard Python logging library. |
| Flexible Deployment | Deployment strategies that include single or distributed-machine deployment as well as additional support for deploying on Argo, Prefect, Kubeflow, AWS Batch and Databricks. |


## How do I use Kedro?

The [Kedro documentation](https://kedro.readthedocs.io/en/stable/) includes three examples to help get you started:
- A typical "Hello World" example, for an [entry-level description of the main Kedro concepts](https://kedro.readthedocs.io/en/stable/02_get_started/03_hello_kedro.html)
- An [introduction to the product template](https://kedro.readthedocs.io/en/stable/02_get_started/05_example_project.html) using the Iris dataset
- A more detailed [spaceflights tutorial](https://kedro.readthedocs.io/en/stable/03_tutorial/02_tutorial_template.html) to give you hands-on experience


## Why does Kedro exist?

Kedro is built upon our collective best-practice (and mistakes) trying to deliver real-world ML applications that have vast amounts of raw unvetted data. We developed Kedro to achieve the following:
 - To address the main shortcomings of Jupyter notebooks, one-off scripts, and glue-code because there is a focus on
  creating **maintainable data science code**
 - To enhance **team collaboration** when different team members have varied exposure to software engineering concepts
 - To increase efficiency, because applied concepts like modularity and separation of concerns inspire the creation of
  **reusable analytics code**


## The humans behind Kedro

Kedro is maintained by a [product team from QuantumBlack](https://kedro.readthedocs.io/en/stable/12_faq/01_faq.html) and a number of [contributors from across the world](https://github.com/quantumblacklabs/kedro/releases).


## Can I contribute?

Yes! Want to help build Kedro? Check out our [guide to contributing to Kedro](https://github.com/quantumblacklabs/kedro/blob/master/CONTRIBUTING.md).


## Where can I learn more?

There is a growing community around Kedro. Have a look at the [Kedro FAQs](https://kedro.readthedocs.io/en/stable/12_faq/01_faq.html#how-can-i-find-out-more-about-kedro) to find projects using Kedro and links to articles, podcasts and talks.


## Who likes Kedro?

There are Kedro users across the world, who work at start-ups, major enterprises and academic institutions like [Absa](https://www.absa.co.za/), [AI Singapore](https://makerspace.aisingapore.org/2020/08/leveraging-kedro-in-100e/), [Caterpillar](https://www.caterpillar.com/), [Dendra Systems](https://www.dendra.io/), [ElementAI](https://www.elementai.com/), [Imperial College London](https://github.com/dssg/barefoot-winnie-public), [Jungle Scout](https://junglescouteng.medium.com/jungle-scout-case-study-kedro-airflow-and-mlflow-use-on-production-code-150d7231d42e), [McKinsey & Company](https://www.mckinsey.com/alumni/news-and-insights/global-news/firm-news/kedro-from-proprietary-to-open-source), [Mercado Libre Argentina](https://www.mercadolibre.com.ar), [Modec](https://www.modec.com/), [Mosaic Data Science](https://www.youtube.com/watch?v=fCWGevB366g), [NaranjaX](https://www.youtube.com/watch?v=_0kMmRfltEQ), [Open Data Science LatAm](https://www.odesla.org/), [QuantumBlack](https://medium.com/quantumblack/introducing-kedro-the-open-source-library-for-production-ready-machine-learning-code-d1c6d26ce2cf), [Retrieva](https://tech.retrieva.jp/entry/2020/07/28/181414), [Roche](https://www.roche.com/), [UrbanLogiq](https://urbanlogiq.com/), [Universidad Rey Juan Carlos](https://github.com/vchaparro/MasterThesis-wind-power-forecasting/blob/master/thesis.pdf) and [XP](https://youtu.be/wgnGOVNkXqU?t=2210).

Kedro has also won [Best Technical Tool or Framework for AI](https://awards.ai/the-awards/previous-awards/the-4th-ai-award-winners/) in the 2019 Awards AI competition and a merit award for the 2020 [UK Technical Communication Awards](https://uktcawards.com/announcing-the-award-winners-for-2020/). It is listed on the 2020 [ThoughtWorks Technology Radar](https://www.thoughtworks.com/radar/languages-and-frameworks/kedro) and the 2020 [Data & AI Landscape](https://mattturck.com/data2020/).
