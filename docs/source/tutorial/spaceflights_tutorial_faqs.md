# Spaceflights tutorial FAQs


## How do I resolve these common errors?

### Data Catalog setup
You're [testing whether Kedro can load the companies or reviews data](./set_up_data.md#test-that-kedro-can-load-the-csv-data) and see the following:

```python
DataSetError: Failed while loading data from data set 
CSVDataSet(filepath=...).
[Errno 2] No such file or directory: '.../companies.csv'
```

Have you downloaded [the three sample data files](./set_up_data.md#download-datasets) and stored them in the `data/raw` folder?

Or maybe you see the following:

```python
DataSetNotFoundError: DataSet 'companies' not found in the catalog
```

Make sure you have saved `catalog.yml`. Call `exit()` within the ipython session and restart `kedro ipython`. Then try again.

You're [testing whether Kedro can load the shuttles data](./set_up_data.md#test-that-kedro-can-load-the-csv-data) and see the following:

```python
DataSetNotFoundError: DataSet 'shuttles' not found in the catalog
```

Make sure you have saved `catalog.yml`. Call `exit()` within the ipython session and restart `kedro ipython`. Then try again.

### Pipeline run

To successfully run the pipeline, all required input datasets must already exist, otherwise you may get an error similar to this:


```bash
kedro run --pipeline=data_science

2019-10-04 12:36:12,135 - root - INFO - ** Kedro project kedro-tutorial
2019-10-04 12:36:12,158 - kedro.io.data_catalog - INFO - Loading data from `model_input_table` (CSVDataSet)...
2019-10-04 12:36:12,158 - kedro.runner.sequential_runner - WARNING - There are 3 nodes that have not run.
You can resume the pipeline run with the following command:
kedro run
Traceback (most recent call last):
  ...
  File "pandas/_libs/parsers.pyx", line 382, in pandas._libs.parsers.TextReader.__cinit__
  File "pandas/_libs/parsers.pyx", line 689, in pandas._libs.parsers.TextReader._setup_parser_source
FileNotFoundError: [Errno 2] File b'data/03_primary/model_input_table.csv' does not exist: b'data/03_primary/model_input_table.csv'

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  ...
    raise DataSetError(message) from exc
kedro.io.core.DataSetError: Failed while loading data from data set CSVDataSet(filepath=data/03_primary/model_input_table.csv, save_args={'index': False}).
[Errno 2] File b'data/03_primary/model_input_table.csv' does not exist: b'data/03_primary/model_input_table.csv'
```
