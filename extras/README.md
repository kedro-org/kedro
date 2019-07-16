> This directory contains extra scripts that can help improve your Kedro experience for certain use cases. Those are not essential for using Kedro CLI or library components.


## `kedro_project_loader.py`

This script helps to locate Kedro project and run IPython startup scripts in
it when working with Jupyter Notebooks and IPython sessions.
This script will automatically identify your Kedro project root directory and execute all Python scripts from `<project_dir>/.ipython/profile_default/startup` directory.
The details can be found in [the user guide](](https://kedro.readthedocs.io/en/latest/04_user_guide/10_ipython.html)).