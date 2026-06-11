# Quick start with Kedro

## 0. Prerequisites
Before you begin, make sure the following are installed:

* **Python**: Kedro requires Python 3.10+. To confirm this, open **Terminal**, enter `python3 --version`, it should return the installed Python version (e.g. `Python 3.13.13`). If not, you can download Python from its [official website](https://www.python.org/).

* **Git**: In **Terminal**, enter `git --version`, it should return the installed Git version (e.g. `git version 2.50.1`). If not, you can download Git from its [official website](https://git-scm.com/).

* **uv**: `uv`, a very fast Python package and project manager, is used in this quick start. In **Terminal**, enter `uv --version`, it should return the installed uv version (e.g. `uv 0.11.20`). If not, you can download uv from its [official website](https://docs.astral.sh/uv/getting-started/installation/).


## 1. Download the Kedro starter project
**Navigate to a folder** where you want to download the Kedro project.

In **Terminal**, enter the following command. This creates a fully functioning Kedro project from a template without installing Kedro globally.
```bash
uvx kedro new --starter spaceflights-pandas --name spaceflights
```

https://github.com/user-attachments/assets/2fd1fc3e-54a7-44f5-99ab-33708097f057


## 2. Navigate to the project folder
**Navigate to the newly created folder** with the contents of the project:
```bash
cd spaceflights
```

https://github.com/user-attachments/assets/bd5f3802-7768-4eee-8e65-22ea4e359ae1


## 3. Verification
To **check Kedro is installed** in your project, enter the following command in **Terminal**:
```bash
uv run kedro info
```

https://github.com/user-attachments/assets/09564951-ff86-4a52-bd6f-8db095883ea7


## 4. Run the default pipeline
To **run the default pipeline** of this starter project, enter the following command in **Terminal**:
```bash
uv run kedro run --pipeline __default__
```

https://github.com/user-attachments/assets/8723dd72-5bfc-496d-9e77-6a120e4c90b0


## 5. Visualise the default pipeline
To **visualise the default pipeline** with **Kedro-Viz**, our interactive development tool for building data pipelines with Kedro, enter the following command in **Terminal**:
```bash
uv run kedro viz run
```

https://github.com/user-attachments/assets/a7de2248-1cee-4d2f-9c0d-e2a0ed98ed50

![kedro-viz](image.png)
