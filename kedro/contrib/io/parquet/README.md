## Description
A dataset class to load and save Parquet files on AWS S3.


## Context
If you want to use Pandas for smaller data sizes to deal with parquet files on S3. `ParquetS3DataSet ` class can be used.



## Implementation
```python

`ParquetS3DataSet` loads and saves data to a file in S3. It uses s3fs
to read and write from S3 and pandas to handle the parquet file.

Example:
::
    >>> from kedro.contrib.io.parquet.parquet_s3 import ParquetS3DataSet
    >>> import pandas as pd
    >>>
    >>> data = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5],
    >>>                      'col3': [5, 6]})
    >>>
    >>> data_set = ParquetS3DataSet(
    >>>                         filepath="temp3.parquet",
    >>>                         bucket_name="test_bucket",
    >>>                         credentials={
    >>>                             'aws_access_key_id': 'YOUR_KEY',
    >>>                             'aws_access_secredt_key': 'YOUR SECRET'},
    >>>                         save_args={"compression": "GZIP"})
    >>> data_set.save(data)
    >>> reloaded = data_set.load()
    >>>
    >>> assert data.equals(reloaded)

```
