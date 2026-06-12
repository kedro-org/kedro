# Quick start with Kedro
This quick-start guide uses the **CLI**.
<br>
If you prefer a **GUI-based approach**, [try our interactive Kedro Builder](https://demo.kedro.org/kedro-builder/)!

## 0. Prerequisites
Before you begin, make sure the following are installed:

* **Python**: Kedro requires Python 3.10+. To confirm this, open **Terminal**, enter `python3 --version`, it should return the installed Python version (e.g. `Python 3.13.13`). If not, you can download Python from its [official website](https://www.python.org/).

* **Git**: In **Terminal**, enter `git --version`, it should return the installed Git version (e.g. `git version 2.50.1`). If not, you can download Git from its [official website](https://git-scm.com/).

* **uv**: `uv`, a very fast Python package and project manager, is used in this quick start. In **Terminal**, enter `uv --version`, it should return the installed uv version (e.g. `uv 0.11.20`). If not, you can download uv from its [official website](https://docs.astral.sh/uv/getting-started/installation/).


## 1. Download the Kedro starter project
**Navigate to a folder** where you want to download the Kedro project.
<br>
In **Terminal**, enter the following command. This creates a fully functioning Kedro project from a template without installing Kedro globally.
```bash
uvx kedro new --starter spaceflights-pandas --name spaceflights
```
![Download the Kedro starter project](01-download-the-kedro-starter-project.gif)


## 2. Navigate to the project folder
**Navigate to the newly created folder** with the contents of the project:
```bash
cd spaceflights
```
![Navigate to the project folder](02-navigate-to-the-project-folder.gif)


## 3. Verification
To **check Kedro is installed** in your project, enter the following command in **Terminal**:
```bash
uv run kedro info
```
![Verification](03-verification.gif)


## 4. Run the default pipeline
To **run the default pipeline** of this starter project, enter the following command in **Terminal**:
```bash
uv run kedro run --pipeline __default__
```
![Run the default pipeline](04-run-the-default-pipeline.gif)


## 5. Visualise the default pipeline
To **visualise the default pipeline** with **Kedro-Viz**, our interactive development tool for building data pipelines with Kedro, enter the following command in **Terminal**. Kedro-Viz will open separately in your browser.:
```bash
uv run kedro viz run
```
![Visualise the default pipeline](05-visualise-the-default-pipeline.gif)

## 4 key concepts
### 01 Project template
An opinionated, standardized layout. Every Kedro project looks the same — new team members are on the same page from day one.
### 02 Data catalog
Data catalog is the central registry of all data sources used in a Kedro project. Instead of hardcoding file paths, data formats, and credentials directly into the Python code, datasets are defined in a single YAML file `catalog.yml`, which specifies how your project should load and save data.
### 03 Node
Just a pure Python function, with same input and same output. Building blocks of pipelines. Functions you can unit test in isolation.
### 04 Pipeline
Compose nodes into DAG. It resolves dependencies automatically from dataset names.

## Project template
### One layout. Every project.
`kedro new` bootstraps your Kedro project with the same layout. Walk into any Kedro repos and know where things live.


```bash
project-dir
├── conf
│       ├── base/
│       ├── local/
├── data
│       ├── 01_raw
│       ├── 02_intermediate
│       ├── 03_primary
│       ├── 04_feature
│       ├── 05_model_input
│       ├── 06_models
│       ├── 07_model_output
│       ├── 08_reporting
├── docs
├── notebooks
├── src
│       ├── pipeline/
│              ├── nodes.py
│              ├── pipeline.py
├── tests
├── .gitignore
├── pyproject.toml
├── READ.md
├── requirements.txt
```

**conf/**

* **base**: Settings to be shared across different installations (e.g. `catalog.yml`, `parameters.yml`)
* **local**: Settings specific to each user (e.g. `credentials.yml`)

**data/**

* Data in layered progression from **raw → output**

**src/**

* Contains different pipeline source codes (e.g. nodes.py, pipeline.py)