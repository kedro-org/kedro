# Set up the data

This section shows how to add datasets to the project's `data` folder. It also reviews how those datasets are registered in [Kedro's Data Catalog](../catalog-data/data_catalog.md), which is the registry of all data sources available for use by the project.

## Project datasets

The spaceflights tutorial makes use of three fictional datasets of companies shuttling customers to the Moon and back. The data comes in two different formats: `.csv` and `.xlsx`:

* `companies.csv` contains data about space travel companies, such as their location, fleet count and rating
* `reviews.csv` is a set of reviews from customers for categories, such as comfort and price
* `shuttles.xlsx` is a set of attributes for spacecraft across the fleet, such as their engine type and passenger capacity

The spaceflights starter has already added the datasets to the `data/01_raw` folder of your project.

## Dataset registration

The following information about a dataset must be registered before Kedro can load it:

* File location (path)
* Parameters for the given dataset
* Dataset type
* Versioning

Open `conf/base/catalog.yml` for the spaceflights project to inspect the contents. The two `csv` datasets are registered as follows:

<!-- vale off -->
<!-- vale off -->
??? example "View code"
    ```yaml
    companies:
      type: pandas.CSVDataset
      filepath: data/01_raw/companies.csv

    reviews:
      type: pandas.CSVDataset
      filepath: data/01_raw/reviews.csv
    ```
<!-- vale on -->

Likewise for the `xlsx` dataset:

<!-- vale off -->
??? example "View code"
    ```yaml
    shuttles:
      type: pandas.ExcelDataset
      filepath: data/01_raw/shuttles.xlsx
      load_args:
        engine: openpyxl # Use modern Excel engine (the default since Kedro 0.18.0)
    ```
<!-- vale on -->

The additional line, `load_args`, is passed to the excel file read method (`pd.read_excel`) as a [keyword argument](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_excel.html). Although not specified here, the corresponding output argument is `save_args` and the value would be passed to [`pd.DataFrame.to_excel` method](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_excel.html).

### Test that Kedro can load the data

Open a `kedro ipython` session in your terminal from the project root directory:

```bash
kedro ipython
```

Then type the following into the IPython prompt to test load some `csv` data:

```python
companies = catalog.load("companies")
companies.head()
```

* The first command creates a variable (`companies`) of type `pandas.DataFrame`. It loads the dataset (also named `companies` as per top-level key in `catalog.yml`) from the underlying filepath `data/01_raw/companies.csv`.
* The `head` method from `pandas` displays the first five rows of the DataFrame.

<!-- vale off -->
??? example "View code"
    ```
    INFO     Loading data from 'companies' (CSVDataset)
    Out[1]:
          id company_rating       company_location  total_fleet_count iata_approved
    0  35029           100%                   Niue                4.0             f
    1  30292            67%               Anguilla                6.0             f
    2  19032            67%     Russian Federation                4.0             f
    3   8238            91%               Barbados               15.0             t
    4  30342            NaN  Sao Tome and Principe                2.0             t

    ```
<!-- vale on -->

Similarly, to test that the `xlsx` data is loaded as expected:

```python
shuttles = catalog.load("shuttles")
shuttles.head()
```

You should see output such as the following:

??? example "View code"
    ```
    INFO     Loading data from 'shuttles' (ExcelDataset)
    Out[1]:
          id       shuttle_location shuttle_type engine_type  ... d_check_complete  moon_clearance_complete     price company_id
    0  63561                   Niue      Type V5     Quantum  ...                f                        f  $1,325.0      35029
    1  36260               Anguilla      Type V5     Quantum  ...                t                        f  $1,780.0      30292
    2  57015     Russian Federation      Type V5     Quantum  ...                f                        f  $1,715.0      19032
    3  14035               Barbados      Type V5      Plasma  ...                f                        f  $4,770.0       8238
    4  10036  Sao Tome and Principe      Type V2      Plasma  ...                f                        f  $2,820.0      30342
    ```
<!-- vale on -->

When you have finished, close `ipython` session with `exit()`.

## Further information

### Watch the video

<iframe width="100%" height="460" src="https://www.youtube.com/embed/rl2cncGxyts"
frameborder="0" allowfullscreen></iframe>



### Custom data

[Kedro supports a wide range of datasets](https://docs.kedro.org/projects/kedro-datasets/en/stable/) out of the box, but you can also add support for any proprietary data format or filesystem.

You can find further information about [how to add support for custom datasets](../extend/how_to_create_a_custom_dataset.md) in specific documentation covering advanced usage.

### Supported data locations

Kedro uses [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to read data from a variety of data stores including local file systems, network file systems, HDFS, and widely used cloud object stores.
