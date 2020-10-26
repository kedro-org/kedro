# Dataset transformers (deprecated)

> _Note_: The transformer API will be deprecated in 0.18.0. We recommend using the `before_dataset_loaded`/`after_dataset_loaded` and `before_dataset_saved`/`after_dataset_saved` [Hooks](./02_hooks.md) to customise the dataset `load` and `save` methods where appropriate.

As we describe in the [documentation about how Kedro works with data](../05_data/01_data_catalog.html#transforming-datasets), Kedro transformers intercept the load and save operations on Kedro `DataSet`s.

Use cases for Kedro transformers include:

 - Data validation
 - Operation performance tracking
 - Data format conversion (although we would recommend [Transcoding](../05_data/01_data_catalog.md#transcoding-datasets) for this)

### Develop your own dataset transformer

To illustrate the use case for operation performance tracking, this section demonstrates how to build a transformer to track memory consumption. In fact, Kedro provides a built-in memory profiler, but this example shows how to build your own, using [memory-profiler](https://github.com/pythonprofilers/memory_profiler).

> Note: To work with this example, you need to `pip install memory_profiler` before you start.


A custom transformer should:

* Inherit from the `kedro.io.AbstractTransformer` base class
* Implement the `load` and `save` method

Within the project in which you want to use the transformer, create a file in `src/<package_name>/` called `memory_profile.py` and paste the following code into it:

<details>
<summary><b>Click to expand</b></summary>

```python
import logging
from typing import Callable, Any

from kedro.io import AbstractTransformer
from memory_profiler import memory_usage


def _normalise_mem_usage(mem_usage):
    # memory_profiler < 0.56.0 returns list instead of float
    return mem_usage[0] if isinstance(mem_usage, (list, tuple)) else mem_usage


class ProfileMemoryTransformer(AbstractTransformer):
    """ A transformer that logs the maximum memory consumption during load and save calls """

    @property
    def _logger(self):
        return logging.getLogger(self.__class__.__name__)

    def load(self, data_set_name: str, load: Callable[[], Any]) -> Any:
        mem_usage, data = memory_usage(
            (load, [], {}),
            interval=0.1,
            max_usage=True,
            retval=True,
            include_children=True,
        )
        # memory_profiler < 0.56.0 returns list instead of float
        mem_usage = _normalise_mem_usage(mem_usage)

        self._logger.info(
            "Loading %s consumed %2.2fMiB memory at peak time", data_set_name, mem_usage
        )
        return data

    def save(self, data_set_name: str, save: Callable[[Any], None], data: Any) -> None:
        mem_usage = memory_usage(
            (save, [data], {}),
            interval=0.1,
            max_usage=True,
            retval=False,
            include_children=True,
        )
        mem_usage = _normalise_mem_usage(mem_usage)

        self._logger.info(
            "Saving %s consumed %2.2fMiB memory at peak time", data_set_name, mem_usage
        )
```
</details>

Next, you need to update `TransformerHooks` to apply your custom transformer. Add the following to a `hooks.py` file in your project.

<details>
<summary><b>Click to expand</b></summary>

```python
...
from .memory_profile import ProfileMemoryTransformer # new import

class TransformerHooks:
    @hook_impl
    def after_catalog_created(self, catalog: DataCatalog) -> None:
        catalog.add_transformer(ProfileTimeTransformer())

        # as memory tracking is quite time-consuming, for demonstration purposes
        # let's apply profile_memory only to the master_table
        catalog.add_transformer(ProfileMemoryTransformer(), "master_table")
```
</details>

Finally, update `ProjectContext` in `run.py` as follows:

```
class ProjectContext(KedroContext):

    ...
    hooks = (TransformerHooks(),)
```


Then re-run the pipeline:

```console
$ kedro run
```

The output should look similar to the following:

```
...
2019-11-13 15:55:01,674 - kedro.io.data_catalog - INFO - Saving data to `master_table` (CSVDataSet)...
2019-11-13 15:55:12,322 - ProfileMemoryTransformer - INFO - Saving master_table consumed 606.98MiB memory at peak time
2019-11-13 15:55:12,322 - ProfileTimeTransformer - INFO - Saving master_table took 10.648 seconds
2019-11-13 15:55:12,357 - kedro.runner.sequential_runner - INFO - Completed 3 out of 6 tasks
2019-11-13 15:55:12,358 - kedro.io.data_catalog - INFO - Loading data from `master_table` (CSVDataSet)...
2019-11-13 15:55:13,933 - ProfileMemoryTransformer - INFO - Loading master_table consumed 533.05MiB memory at peak time
2019-11-13 15:55:13,933 - ProfileTimeTransformer - INFO - Loading master_table took 1.576 seconds
...
```
