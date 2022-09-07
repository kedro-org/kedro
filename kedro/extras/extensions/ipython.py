"""
This file and directory exists purely for backwards compatibility of the following:
%load_ext kedro.extras.extensions.ipython
from kedro.extras.extensions.ipython import reload_kedro

Any modifications to the IPython extension should now be made in kedro/ipython/.
The Kedro IPython extension should always be loaded as %load_ext kedro.ipython.
Line magics such as reload_kedro should always be called as line magics rather than
importing the underlying Python functions.
"""
from ...ipython import load_ipython_extension, reload_kedro
