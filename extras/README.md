> This directory contains extra scripts that can help improve your Kedro experience for certain use cases. Those are not essential for using Kedro CLI or library components.

## `kedro_project_loader.py`

This script helps to locate Kedro project and run IPython startup scripts in
it when working with Jupyter Notebooks and IPython sessions. This script will automatically identify your Kedro project root directory and execute all Python scripts from `<project_dir>/.ipython/profile_default/startup` directory.

### Installation

To install this script simply download it into your default IPython config directory:

```bash
mkdir -p ~/.ipython/profile_default/startup
wget https://raw.githubusercontent.com/quantumblacklabs/kedro/master/extras/kedro_project_loader.py -O ~/.ipython/profile_default/startup/kedro_project_loader.py
```

### Prerequisites

In order for this script to work, the following conditions must be met:

1. You Kedro project must contain `kedro_cli.py` file in its root directory.
2. Jupyter notebook should be saved inside Kedro project root directory or any nested subdirectory.
3. IPython interactive session should be started with the working directory inside Kedro project root directory or any nested subdirectory.

For example, given the following Kedro project structure:
```console
new-kedro-project/
├── conf/
├── data/
├── docs/
├── kedro_cli.py
├── logs/
├── notebooks
│   └── subdir1
│       └── subdir2
├── setup.cfg
└── src/
```

Placing your `Notebook.ipynb` file anywhere in `new-kedro-project/notebooks/`, `new-kedro-project/notebooks/subdir1/`, `new-kedro-project/notebooks/subdir1/subdir2/` or even `new-kedro-project/` (although strongly discouraged) will work.

> *Note:* Given the example structure above, this script *will not* load your Kedro project context if the notebook is saved anywhere *outside* `new-kedro-project` directory.

### Error handling

In case this script fails to execute any of your Kedro project startup scripts, global variable `load_kedro_errors` will contain a dictionary with the key pointing to the failed script path and the value containing exception object. 
