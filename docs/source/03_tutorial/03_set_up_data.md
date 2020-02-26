# Setting up the data

Kedro uses configuration to make your code reproducible when it has to reference datasets in different locations and / or in different environments. In this section of the tutorial we will describe the following:

* Adding datasets to your `data/` folder, according to [data engineering convention](../06_resources/01_faq.md#what-is-data-engineering-convention)
* Using the Data Catalog as a registry of all data sources available for use by the project `conf/base/catalog.yml`

For further information about the Data Catalog, please see the [User Guide](../04_user_guide/04_data_catalog.md).


## Adding your datasets to `data`

This tutorial will make use of fictional datasets for spaceflight companies shuttling customers to the Moon and back. You will use the data to train a model to predict the price of shuttle hire. However, before you get to train the model, you will need to prepare the data by doing some data engineering, which is the process of preparing data for model building by creating a master table.

The spaceflight tutorial has three files and uses two data formats: `.csv` and `.xlsx`. Download and save the files to the `data/01_raw/` folder of your project directory:

* [reviews.csv](https://quantumblacklabs.github.io/kedro/reviews.csv)
* [companies.csv](https://quantumblacklabs.github.io/kedro/companies.csv)
* [shuttles.xlsx](https://quantumblacklabs.github.io/kedro/shuttles.xlsx)

Here is an example of how you can [download the files from GitHub](https://www.quora.com/How-do-I-download-something-from-GitHub) to `data/01_raw` directory inside your project using [cURL](https://curl.haxx.se/download.html) in a Unix terminal:

<details>
<summary><b>Click to expand</b></summary>

```bash
# reviews
curl -o data/01_raw/reviews.csv https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/docs/source/03_tutorial/data/reviews.csv
# companies
curl -o data/01_raw/companies.csv https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/docs/source/03_tutorial/data/companies.csv
# shuttles
curl -o data/01_raw/shuttles.xlsx https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/docs/source/03_tutorial/data/shuttles.xlsx
```
</details>

Or through using [Wget](https://www.gnu.org/software/wget/):

<details>
<summary><b>Click to expand</b></summary>

```bash
# reviews
wget -O data/01_raw/reviews.csv https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/docs/source/03_tutorial/data/reviews.csv
# companies
wget -O data/01_raw/companies.csv https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/docs/source/03_tutorial/data/companies.csv
# shuttles
wget -O data/01_raw/shuttles.xlsx https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/docs/source/03_tutorial/data/shuttles.xlsx
```
</details>

Alternatively, if you are a Windows user, try [Wget for Windows](https://eternallybored.org/misc/wget/) and the following commands instead:

<details>
<summary><b>Click to expand</b></summary>

```bat
wget -O data\01_raw\reviews.csv https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/docs/source/03_tutorial/data/reviews.csv
wget -O data\01_raw\companies.csv https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/docs/source/03_tutorial/data/companies.csv
wget -O data\01_raw\shuttles.xlsx https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/docs/source/03_tutorial/data/shuttles.xlsx
```
</details>

or [cURL for Windows](https://curl.haxx.se/windows/):

<details>
<summary><b>Click to expand</b></summary>

```bat
curl -o data\01_raw\reviews.csv https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/docs/source/03_tutorial/data/reviews.csv
curl -o data\01_raw\companies.csv https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/docs/source/03_tutorial/data/companies.csv
curl -o data\01_raw\shuttles.xlsx https://raw.githubusercontent.com/quantumblacklabs/kedro/develop/docs/source/03_tutorial/data/shuttles.xlsx
```
</details>


## Reference all datasets

To work with the datasets provided you need to make sure they can be loaded by Kedro.

All Kedro projects have a `conf/base/catalog.yml` file where users register the datasets they use. Registering a dataset is as simple as adding a named entry into the `.yml` file, which includes:

* File location (path)
* Parameters for the given dataset
* Type of data
* Versioning

Kedro supports a number of different data types. The full list of supported datasets can be found in the API documentation. Kedro uses [`fssspec`](https://filesystem-spec.readthedocs.io/en/latest/) to read data from a variety of data stores including local file systems, network file systems, cloud object stores and HDFS.

Let’s start this process by registering the `csv` datasets by copying the following to the end of the `conf/base/catalog.yml` file:

```yaml
companies:
  type: pandas.CSVDataSet
  filepath: data/01_raw/companies.csv

reviews:
  type: pandas.CSVDataSet
  filepath: data/01_raw/reviews.csv
```

If you want to check whether Kedro loads the data correctly, open a `kedro ipython` session and run:

```python
context.catalog.load("companies").head()
```

This will load the dataset named `companies` (as per top-level key in `catalog.yml`), from the underlying filepath `data/01_raw/companies.csv`, and show you the first five rows of the dataset. It is loaded into a `pandas` DataFrame and you can play with it as you wish.

When you have finished, simply close `ipython` session by typing the following:

```python
exit()
```


## Creating custom datasets

Often, real world data is stored in formats that are not supported by Kedro. We will illustrate this with `shuttles.xlsx`. In fact, Kedro has built-in support for Microsoft Excel files, but we will take the opportunity to demonstrate how to use Kedro to implement support for custom data formats.

Let’s create a custom dataset implementation which will allow you to load and save `.xlsx` files.

To keep your code well-structured you should create a Python sub-package called **`kedro_tutorial.io`**. You can do that by running this in your Unix terminal:

```bash
mkdir -p src/kedro_tutorial/io && touch src/kedro_tutorial/io/__init__.py
```

Or, if you are a Windows user:

```bat
mkdir src\kedro_tutorial\io && type nul > src\kedro_tutorial\io\__init__.py
```

Creating new custom dataset implementations is done by creating a class that extends and implements all methods from `kedro.io.AbstractDataSet`. To implement a class that will allow you to load and save Excel files, you need to create the file `src/kedro_tutorial/io/xls_local.py` by running the following in your Unix terminal:

```bash
touch src/kedro_tutorial/io/xls_local.py
```
For Windows, try:
```bat
type nul > src\kedro_tutorial\io\xls_local.py
```

and paste the following into the newly created file:

```python
"""ExcelDataSet loads and saves data to a local Excel file. The
underlying functionality is supported by pandas, so it supports all
allowed pandas options for loading and saving Excel files.
"""
from os.path import isfile
from typing import Any, Union, Dict

import pandas as pd

from kedro.io import AbstractDataSet

class ExcelDataSet(AbstractDataSet):
    """``ExcelDataSet`` loads and saves data to a local Excel file. The
    underlying functionality is supported by pandas, so it supports all
    allowed pandas options for loading and saving Excel files.

    Example:
    ::

        >>> import pandas as pd
        >>>
        >>> data = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5],
        >>>                      'col3': [5, 6]})
        >>> data_set = ExcelDataSet(filepath="test.xlsx",
        >>>                              load_args={'sheet_name':"Sheet1"},
        >>>                              save_args=None)
        >>> data_set.save(data)
        >>> reloaded = data_set.load()
        >>>
        >>> assert data.equals(reloaded)

    """

    def _describe(self) -> Dict[str, Any]:
        return dict(
            filepath=self._filepath,
            engine=self._engine,
            load_args=self._load_args,
            save_args=self._save_args,
        )

    def __init__(
        self,
        filepath: str,
        engine: str = "xlsxwriter",
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new instance of ``ExcelDataSet`` pointing to a concrete
        filepath.

        Args:
            engine: The engine used to write to excel files. The default
                          engine is 'xlswriter'.

            filepath: path to an Excel file.

            load_args: Pandas options for loading Excel files.
                Here you can find all available arguments:
                https://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_excel.html
                The default_load_arg engine is 'xlrd', all others preserved.

            save_args: Pandas options for saving Excel files.
                Here you can find all available arguments:
                https://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.to_excel.html
                All defaults are preserved.

        """
        self._filepath = filepath
        default_save_args = {}
        default_load_args = {"engine": "xlrd"}

        self._load_args = (
            {**default_load_args, **load_args}
            if load_args is not None
            else default_load_args
        )
        self._save_args = (
            {**default_save_args, **save_args}
            if save_args is not None
            else default_save_args
        )
        self._engine = engine

    def _load(self) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        return pd.read_excel(self._filepath, **self._load_args)

    def _save(self, data: pd.DataFrame) -> None:
        writer = pd.ExcelWriter(self._filepath, engine=self._engine)
        data.to_excel(writer, **self._save_args)
        writer.save()

    def _exists(self) -> bool:
        return isfile(self._filepath)
```

> _Note:_ This dataset will only work with Excel files on local file systems as it does not have an integration with [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/), a tool that we use to abstract file storage.

Update the `conf/base/catalog.yml` file by adding the following full import path:

```yaml
shuttles:
  type: kedro_tutorial.io.xls_local.ExcelDataSet
  filepath: data/01_raw/shuttles.xlsx
```

The `type` specified is `kedro_tutorial.io.xls_local.ExcelDataSet` which points Kedro to use the custom dataset implementation. To use Kedro's internal support for reading Excel datasets, you can simply specify `pandas.ExcelDataSet`, which is implemented as in the code below:

```yaml
shuttles:
  type: pandas.ExcelDataSet
  filepath: data/01_raw/shuttles.xlsx
```

A good way to test that everything works as expected is by trying to load the dataset within a new `kedro ipython` session:

```python
context.catalog.load("shuttles").head()
```

### Contributing a custom dataset implementation

Kedro users create many custom dataset implementations while working on real-world projects, and it makes sense that they should be able to share their work with each other. That is why Kedro has a `kedro.extras.datasets` sub-package, where users can add new custom dataset implementations to help others in our community. Sharing your custom datasets implementations is possibly the easiest way to contribute back to Kedro and if you are interested in doing so, you can check out the Kedro [contribution guide](https://github.com/quantumblacklabs/kedro/blob/develop/CONTRIBUTING.md) on the GitHub repo.

For a complete guide on how to create and contribute a custom dataset, please read [this article](../04_user_guide/14_create_a_new_dataset.md).
