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