## Description
A dataset class to save matplotlib figures/plt objects to images locally, MatplotlibWriter. 


## Context
In the process of making documentation of features, programmatically making plots of all features in a standardised way 
and embedding links in .md files has been a big timesaver.


## Implementation
```python

``MatplotlibWriter`` saves matplotlib objects as image files.

Example:
::

    >>> import matplotlib.pyplot as plt
    >>> from kedro.contrib.io.matplotlib import MatplotlibWriter
    >>>
    >>> plt.plot([1,2,3],[4,5,6])
    >>>
    >>> single_plot_writer = MatplotlibWriter(filepath="docs/new_plot.png")
    >>> single_plot_writer.save(plt)
    >>>
    >>> plt.close()
    >>>
    >>> plots = dict()
    >>>
    >>> for colour in ['blue', 'green', 'red']:
    >>>     plots[colour] = plt.figure()
    >>>     plt.plot([1,2,3],[4,5,6], color=colour)
    >>>     plt.close()
    >>>
    >>> multi_plot_writer = MatplotlibWriter(filepath="docs/",
    >>>                                      save_args={'multiFile': True})
    >>> multi_plot_writer.save(plots)
```
