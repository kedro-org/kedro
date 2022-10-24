# Spaceflights tutorial FAQs





## Common errors

### Setting up the data catalog
You're [testing whether Kedro can load the companies or reviews data](./set_up_data.html#test-that-kedro-can-load-the-csv-data) and see the following:

```python
DataSetError: Failed while loading data from data set 
CSVDataSet(filepath=...).
[Errno 2] No such file or directory: '.../companies.csv'
```

Have you downloaded [the three sample data files](./set_up_data#download-datasets) and stored them in the `data/raw` folder?

Or maybe you see the following:

```python
DataSetNotFoundError: DataSet 'companies' not found in the catalog
```

Make sure you have saved `catalog.yml`. Call `exit()` within the ipython session and restart `kedro ipython`. Then try again.

You're [testing whether Kedro can load the shuttles data](./set_up_data.html#test-that-kedro-can-load-the-csv-data) and see the following:

```python
DataSetNotFoundError: DataSet 'shuttles' not found in the catalog
```

Make sure you have saved `catalog.yml`. Call `exit()` within the ipython session and restart `kedro ipython`. Then try again.