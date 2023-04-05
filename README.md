![Kedro Logo Banner](https://raw.githubusercontent.com/kedro-org/kedro/develop/static/img/kedro_banner.png)
[![Python version](https://img.shields.io/badge/python-3.7%20%7C%203.8%20%7C%203.9%20%7C%203.10-blue.svg)](https://pypi.org/project/kedro/)
[![PyPI version](https://badge.fury.io/py/kedro.svg)](https://pypi.org/project/kedro/)
[![Conda version](https://img.shields.io/conda/vn/conda-forge/kedro.svg)](https://anaconda.org/conda-forge/kedro)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/kedro-org/kedro/blob/main/LICENSE.md)
[![Slack Organisation](https://img.shields.io/badge/slack-chat-blueviolet.svg?label=Kedro%20Slack&logo=slack)](https://slack.kedro.org)
![CircleCI - Main Branch](https://img.shields.io/circleci/build/github/kedro-org/kedro/main?label=main)
![Develop Branch Build](https://img.shields.io/circleci/build/github/kedro-org/kedro/develop?label=develop)
[![Documentation](https://readthedocs.org/projects/kedro/badge/?version=stable)](https://docs.kedro.org/)
[![OpenSSF Best Practices](https://bestpractices.coreinfrastructure.org/projects/6711/badge)](https://bestpractices.coreinfrastructure.org/projects/6711)


## What is Kedro?

Kedro is an open-source Python framework to create reproducible, maintainable, and modular data science code. It uses software engineering best practices to help you build production-ready data engineering and data science pipelines.

Kedro is hosted by the [LF AI & Data Foundation](https://lfaidata.foundation/).

## How do I install Kedro?

To install Kedro from the Python Package Index (PyPI) run:

```
pip install kedro
```

It is also possible to install Kedro using `conda`:

```
conda install -c conda-forge kedro
```

Our [Get Started guide](https://docs.kedro.org/en/stable/get_started/install.html) contains full installation instructions, and includes how to set up Python virtual environments.


## What are the main features of Kedro?

![Kedro-Viz Pipeline Visualisation](https://github.com/kedro-org/kedro-viz/blob/main/.github/img/banner.png)
*A pipeline visualisation generated using [Kedro-Viz](https://github.com/kedro-org/kedro-viz)*


| Feature | What is this? |
|----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Project Template | A standard, modifiable and easy-to-use project template based on [Cookiecutter Data Science](https://github.com/drivendata/cookiecutter-data-science/). |
| Data Catalog | A series of lightweight data connectors used to save and load data across many different file formats and file systems, including local and network file systems, cloud object stores, and HDFS. The Data Catalog also includes data and model versioning for file-based systems. |
| Pipeline Abstraction | Automatic resolution of dependencies between pure Python functions and data pipeline visualisation using [Kedro-Viz](https://github.com/kedro-org/kedro-viz). |
| Coding Standards | Test-driven development using [`pytest`](https://github.com/pytest-dev/pytest), produce well-documented code using [Sphinx](http://www.sphinx-doc.org/en/master/), create linted code with support for [`flake8`](https://github.com/PyCQA/flake8), [`isort`](https://github.com/PyCQA/isort) and [`black`](https://github.com/psf/black) and make use of the standard Python logging library. |
| Flexible Deployment | Deployment strategies that include single or distributed-machine deployment as well as additional support for deploying on Argo, Prefect, Kubeflow, AWS Batch and Databricks. |


## How do I use Kedro?

The [Kedro documentation](https://docs.kedro.org/en/stable/) first explains [how to install Kedro](https://docs.kedro.org/en/stable/get_started/install.html) and then introduces [key Kedro concepts](https://docs.kedro.org/en/stable/get_started/kedro_concepts.html).

- The first example illustrates the [basics of a Kedro project](https://docs.kedro.org/en/stable/get_started/new_project.html) using the Iris dataset
- You can then review the [spaceflights tutorial](https://docs.kedro.org/en/stable/tutorial/tutorial_template.html) to build a Kedro project for hands-on experience

For new and intermediate Kedro users, there's a comprehensive section on [how to visualise Kedro projects using Kedro-Viz](https://docs.kedro.org/en/stable/visualisation/kedro-viz_visualisation.html) and [how to work with Kedro and Jupyter notebooks](https://docs.kedro.org/en/stable/notebooks_and_ipython/kedro_and_notebooks).

Further documentation is available for more advanced Kedro usage and deployment. We also recommend the [glossary](https://docs.kedro.org/en/stable/resources/glossary.html) and the [API reference documentation](/kedro) for additional information.


## Why does Kedro exist?

Kedro is built upon our collective best-practice (and mistakes) trying to deliver real-world ML applications that have vast amounts of raw unvetted data. We developed Kedro to achieve the following:
 - To address the main shortcomings of Jupyter notebooks, one-off scripts, and glue-code because there is a focus on
  creating **maintainable data science code**
 - To enhance **team collaboration** when different team members have varied exposure to software engineering concepts
 - To increase efficiency, because applied concepts like modularity and separation of concerns inspire the creation of
  **reusable analytics code**


## The humans behind Kedro

The [Kedro product team](https://docs.kedro.org/en/stable/contribution/technical_steering_committee.html#kedro-maintainers) and a number of [open source contributors from across the world](https://github.com/kedro-org/kedro/releases) maintain Kedro.


## Can I contribute?

Yes! Want to help build Kedro? Check out our [guide to contributing to Kedro](https://github.com/kedro-org/kedro/blob/main/CONTRIBUTING.md).


## Where can I learn more?

There is a growing community around Kedro. Have a look at the [Kedro FAQs](https://docs.kedro.org/en/stable/faq/faq.html#how-can-i-find-out-more-about-kedro) to find projects using Kedro and links to articles, podcasts and talks.


## Who likes Kedro?

There are Kedro users across the world, who work at start-ups, major enterprises and academic institutions like [Absa](https://www.absa.co.za/),
[Acensi](https://acensi.eu/page/home),
[Advanced Programming Solutions SL](https://www.linkedin.com/feed/update/urn:li:activity:6863494681372721152/),
[AI Singapore](https://makerspace.aisingapore.org/2020/08/leveraging-kedro-in-100e/),
[AMAI GmbH](https://www.am.ai/),
[Augment Partners](https://www.linkedin.com/posts/augment-partners_kedro-cheat-sheet-by-augment-activity-6858927624631283712-Ivqk),
[AXA UK](https://www.axa.co.uk/),
[Belfius](https://www.linkedin.com/posts/vangansen_mlops-machinelearning-kedro-activity-6772379995953238016-JUmo),
[Beamery](https://medium.com/hacking-talent/production-code-for-data-science-and-our-experience-with-kedro-60bb69934d1f),
[Caterpillar](https://www.caterpillar.com/),
[CRIM](https://www.crim.ca/en/),
[Dendra Systems](https://www.dendra.io/),
[Element AI](https://www.elementai.com/),
[GetInData](https://getindata.com/blog/running-machine-learning-pipelines-kedro-kubeflow-airflow),
[GMO](https://recruit.gmo.jp/engineer/jisedai/engineer/jisedai/engineer/jisedai/engineer/jisedai/engineer/jisedai/blog/kedro_and_mlflow_tracking/),
[Indicium](https://medium.com/indiciumtech/how-to-build-models-as-products-using-mlops-part-2-machine-learning-pipelines-with-kedro-10337c48de92),
[Imperial College London](https://github.com/dssg/barefoot-winnie-public),
[ING](https://www.ing.com),
[Jungle Scout](https://junglescouteng.medium.com/jungle-scout-case-study-kedro-airflow-and-mlflow-use-on-production-code-150d7231d42e),
[Helvetas](https://www.linkedin.com/posts/lionel-trebuchon_mlflow-kedro-ml-ugcPost-6747074322164154368-umKw),
[Leapfrog](https://www.lftechnology.com/blog/ai-pipeline-kedro/),
[McKinsey & Company](https://www.mckinsey.com/alumni/news-and-insights/global-news/firm-news/kedro-from-proprietary-to-open-source),
[Mercado Libre Argentina](https://www.mercadolibre.com.ar),
[Modec](https://www.modec.com/),
[Mosaic Data Science](https://www.youtube.com/watch?v=fCWGevB366g),
[NaranjaX](https://www.youtube.com/watch?v=_0kMmRfltEQ),
[NASA](https://github.com/nasa/ML-airport-taxi-out),
[NHS AI Lab](https://nhsx.github.io/skunkworks/synthetic-data-pipeline),
[Open Data Science LatAm](https://www.odesla.org/),
[Prediqt](https://prediqt.co/),
[QuantumBlack](https://medium.com/quantumblack/introducing-kedro-the-open-source-library-for-production-ready-machine-learning-code-d1c6d26ce2cf),
[ReSpo.Vision](https://neptune.ai/customers/respo-vision),
[Retrieva](https://tech.retrieva.jp/entry/2020/07/28/181414),
[Roche](https://www.roche.com/),
[Sber](https://www.linkedin.com/posts/seleznev-artem_welcome-to-kedros-documentation-kedro-activity-6767523561109385216-woTt),
[Société Générale](https://www.societegenerale.com/en),
[Telkomsel](https://medium.com/life-at-telkomsel/how-we-build-a-production-grade-data-pipeline-7004e56c8c98),
[Universidad Rey Juan Carlos](https://github.com/vchaparro/MasterThesis-wind-power-forecasting/blob/master/thesis.pdf),
[UrbanLogiq](https://urbanlogiq.com/),
[Wildlife Studios](https://wildlifestudios.com),
[WovenLight](https://www.wovenlight.com/) and
[XP](https://youtu.be/wgnGOVNkXqU?t=2210).

Kedro won [Best Technical Tool or Framework for AI](https://awards.ai/the-awards/previous-awards/the-4th-ai-award-winners/) in the 2019 Awards AI competition and a merit award for the 2020 [UK Technical Communication Awards](https://uktcawards.com/announcing-the-award-winners-for-2020/). It is listed on the 2020 [ThoughtWorks Technology Radar](https://www.thoughtworks.com/radar/languages-and-frameworks/kedro) and the 2020 [Data & AI Landscape](https://mattturck.com/data2020/). Kedro has received an [honorable mention in the User Experience category in Fast Company’s 2022 Innovation by Design Awards](https://www.fastcompany.com/90772252/user-experience-innovation-by-design-2022).


## How can I cite Kedro?

If you're an academic, Kedro can also help you, for example, as a tool to solve the problem of reproducible research. Use the "Cite this repository" button on [our repository](https://github.com/kedro-org/kedro) to generate a citation from the [CITATION.cff file](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files).
