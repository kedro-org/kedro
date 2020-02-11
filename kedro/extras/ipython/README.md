> This directory contains extra scripts that can help improve your Kedro experience for certain use cases. Those are not essential for using Kedro CLI or library components.


## `ipython_loader.py`

This script helps to locate `.ipython` directory and run IPython startup scripts in it when working with Jupyter Notebooks and IPython sessions. This script will automatically locate `.ipython/profile_default/startup` directory starting from the current working directory and going up the directory tree. If the directory was found, all Python scripts in it are be executed.

The details can be found in [the user guide](https://kedro.readthedocs.io/en/latest/04_user_guide/11_ipython.html#ipython-loader).
