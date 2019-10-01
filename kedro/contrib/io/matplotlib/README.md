## Description
A dataset class to save matplotlib figures/plot objects as image files.


## Implementation
```python

`MatplotlibWriter` saves matplotlib objects as image files.

Example:
::

    >>> import matplotlib.pyplot as plt
    >>> from kedro.contrib.io.matplotlib import MatplotlibWriter
    >>>
    >>> plt.plot([1,2,3],[4,5,6])
    >>>
    >>> single_plot_writer = MatplotlibWriter(filepath="data/new_plot.png")
    >>> single_plot_writer.save(plt)
    >>>
    >>> plt.close()
    >>>
    >>> plots_dict = dict()
    >>>
    >>> for colour in ['blue', 'green', 'red']:
    >>>     plots_dict[colour] = plt.figure()
    >>>     plt.plot([1,2,3],[4,5,6], color=colour)
    >>>     plt.close()
    >>>
    >>> dict_plot_writer = MatplotlibWriter(filepath="data/")
    >>> dict_plot_writer.save(plots_dict)
    >>>
    >>> plots_list = []
    >>> for index in range(5):
    >>>    plots_list.append(plt.figure())
    >>>    plt.plot([1,2,3],[4,5,6], color=colour)
    >>> list_plot_writer = MatplotlibWriter(filepath="data/")
    >>> list_plot_writer.save(plots_list)

```
