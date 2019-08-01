# PySpark

In this tutorial we talk about how Kedro integrates with `pyspark` using the `SparkDataSet`.

We also present brief instructions on how to set-up pyspark to read from `AWS S3` and `Azure Blob storage`.

Relevant API:
[SparkDataSet](https://kedro.readthedocs.io/en/latest/kedro.contrib.io.pyspark.html)


## Install spark

There are two ways of installing pyspark. The first one is to create a python virtual environment and do `pip install pyspark` in there. Doing so allows you to have an isolated installation which you can easily experiment with,
in the expense of having a proper, fully configurable Spark installation (see below).

If you would like to have full control over Spark's configuration, and you plan on using (scala or python) Spark long-term, we suggest you perform the following steps:

- Download the latest version of Spark from [hear](https://spark.apache.org/downloads.html)
- Extract your download in an appropriate location. If you are on linux, a good candidate is `/opt`
- If you extracted spark in `/opt/spark-2.3.0-bin-hadoop2.7`, maybe create a symlink: `ln -s /opt/spark-2.3.0-bin-hadoop2.7 /opt/spark`
- Set the following environment variables:
```bash
export SPARK_HOME=/opt/spark
export PATH=${SPARK_HOME}/bin:${PATH}
export PYTHONPATH=${SPARK_HOME}/python:${SPARK_HOME}/python/lib/py4j-0.10.6-src.zip
# change appropriately:
# export PYSPARK_PYTHON=/change/to/appropriate/python/path/bin/python
```

> If you have multiple installations of pyspark (eg. a manual one and one after doing `pip install pyspark`), make sure that your python path is appropriately set to first look to your installation of choice. Keep in mind that python will look into multiple places according to the `sys.path` variable, including your virtual environment and the `PYTHONPATH` environment variable.

- Then you can set system-wide spark configuration in `/opt/spark/conf/...`

## Initialise spark

To use pyspark, you should use either the [`findspark` package](https://github.com/minrk/findspark) (install using `pip install findspark`), or add `pyspark` to your python path manually, making also sure to set all appropriate environment variables. Have a look at [this file](https://github.com/minrk/findspark/blob/master/findspark.py) for details.
Then, you can initialise `pyspark` as follows:


```python
# uncomment the following two lines if you did not
# install pyspark using `pip install pyspark`

# import findspark
# findspark.init()

from pyspark.sql import SparkSession
spark = SparkSession.builder\
    .master("local[*]") \
    .appName("kedro") \
    .getOrCreate()
```

## SparkDataSet

Loading and saving spark `DataFrame`s using Kedro can be easily done using the [`SparkDataSet`](https://kedro.readthedocs.io/en/latest/kedro.contrib.io.pyspark.html) class, as shown below:

### Load a csv from your local disk

```python
from kedro.contrib.io.pyspark import SparkDataSet

csv = SparkDataSet('../data/01_raw/2015_points_old.csv',
                   file_format='csv',
                   load_args={'header': True})

df = csv.load() \
    .limit(3) \
    .select(['name', 'point_1', 'point_2'])

df.show()
```

### Save it as parquet to your local disk

```python
parquet = SparkDataSet('../data/01_raw/2015_points_old_parquet',
                       file_format='parquet',
                       save_args={'mode': 'overwrite',
                                  'compression': 'none'})
parquet.save(df)
```

## Using SparkDataSet with the DataCatalog

Since `SparkDataSet` is a concrete implementation of [`AbstractDataSet`](https://kedro.readthedocs.io/en/latest/kedro.io.AbstractDataSet.html), it integrates nicely with the `DataCatalog` and with Kedro's pipelines.

Similarly to all other datasets, you can specify your spark datasets in `catalog.yml` as follows:

#### catalog.yml:

```yaml
sensor_data:
   type: kedro.contrib.io.pyspark.SparkDataSet
   path: data/01_raw/sensors_raw
   file_format: parquet
   load_args:
      header: Yes
   save_args:
      mode: overwrite
```


Then, as previously mentioned you can use this data set as follows:

```python
from kedro.config import load_config
from kedro.io import DataCatalog

conf = load_config('path/to/conf')
catalog = DataCatalog.from_config(conf['catalog'])

df = catalog.load('sensor_data')  #df is a pyspark.sql.DataFrame
```

## Using `SparkDataSet` with AWS S3
### Setting-up spark for AWS

At the time of this writing, the most recent configuration between AWS and Spark known to work well is as follows:

* Spark 2.3.0
* hadoop-aws-2.7.5

The simplest approach is to download Spark in the /opt directory, extract it, create a symlink /opt/spark pointing to it, and then use `spark-shell` or `spark-submit` with the `--packages` option.
You will also have to exclude the joda-time package, as there are conflicting dependencies:

In linux:
```bash
cd /opt
wget http://apache.mirror.anlx.net/spark/spark-2.3.0/spark-2.3.0-bin-hadoop2.7.tgz
tar xzf spark-2.3.0-bin-hadoop2.7.tgz
rm spark-2.3.0-bin-hadoop2.7.tgz
ln -s spark-2.3.0-bin-hadoop2.7 spark
cd spark/bin
spark-shell --packages 'org.apache.hadoop:hadoop-aws:2.7.5' --exclude-packages 'joda-time:joda-time'
```

Don't forget export in your `~/.bashrc`/`~/bash_profile`/`~/.zshrc` or any other initialisation script Spark's environment variables:
```bash
export SPARK_HOME=/opt/spark
export PATH=${SPARK_HOME}/bin:${PATH}
export PYTHONPATH=${SPARK_HOME}/python:${SPARK_HOME}/python/lib/py4j-0.10.6-src.zip
# change appropriately:
# export PYSPARK_PYTHON=/change/to/appropriate/python/path/bin/python
```


### Configuring Kedro with AWS


> Note: If your server is preconfigured to access S3 without the need for credentials (e.g. by storing the credentials in the `.aws` directory), you may skip this step.


First, within your kedro project, navigate to the file `conf/local/credentials.yml`, and place in it the following:

**IMPORTANT:** Credentials should be placed in the `conf/local` directory. This directory is automatically `.gitignored`. As already mentioned earlier, sensitive information **should never** be placed in the `conf/project` directory.

#### conf/local/credentials.yml
```yaml
aws:
   aws_access_key_id: your_access_key
   aws_secret_access_key: here_goes_your_secret_key_which_you_should_never_commit_to_git
```

Now, during initialisation of the `SparkSession`, configure your `aws` credentials as shown below:

```python
from kedro.config import load_config
from pyspark.sql import SparkSession
from pyspark import SparkContext

conf = load_config('path/to/conf')

aws_access_key_id = conf['credentials']['aws']['aws_access_key_id']
aws_secret_access_key = conf['credentials']['aws']['aws_secret_access_key']

spark = SparkSession.builder\
    .master("local[*]") \
    .appName("kedro") \
    .config("fs.s3a.access.key", aws_access_key_id) \
    .config("fs.s3a.secret.key", aws_secret_access_key) \
    .getOrCreate()
```

You should now be able to read data from `aws s3`, using hadoop's `s3a` file system.
Example:

```python
from kedro.contrib.io.pyspark import SparkDataSet

bucket_name = 'your-bucket-name'
filepath = 's3a://' + bucket_name + '/dir_with_parquet_files'
aws_parquet = SparkDataSet(filepath, file_format='parquet')
aws_parquet.load()
```

## Using `SparkDataSet` with Azure Blob Storage

### Setting-up spark for Azure

At the time of this writing, the most recent configuration between Azure and Spark known to work well is as follows:

* Spark 2.3.0
* org.apache.hadoop:hadoop-azure:2.7.5
* com.microsoft.azure:azure-storage:2.2.0

The simplest approach is to download Spark in the /opt directory, extract it, create a symlink /opt/spark pointing to it, and then use `spark-shell` or `spark-submit` with the `--packages` option.
In linux:
```bash
cd /opt
wget http://apache.mirror.anlx.net/spark/spark-2.3.0/spark-2.3.0-bin-hadoop2.7.tgz
tar xzf spark-2.3.0-bin-hadoop2.7.tgz
rm spark-2.3.0-bin-hadoop2.7.tgz
ln -s spark-2.3.0-bin-hadoop2.7 spark
cd spark/bin
spark-shell --packages 'org.apache.hadoop:hadoop-azure:2.7.5,com.microsoft.azure:azure-storage:2.2.0'
```

Don't forget export in your `~/.bashrc`/`~/bash_profile`/`~/.zshrc` or any other initialisation script Spark's environment variables:
```bash
export SPARK_HOME=/opt/spark
export PATH=${SPARK_HOME}/bin:${PATH}
export PYTHONPATH=${SPARK_HOME}/python:${SPARK_HOME}/python/lib/py4j-0.10.6-src.zip
# change appropriately:
# export PYSPARK_PYTHON=/change/to/appropriate/python/path/bin/python
```


### Configuring Kedro with Azure

First, within your kedro project, navigate to the file `conf/local/credentials.yml`, and place in it the following:

**IMPORTANT:** Credentials should be placed in the `conf/local` directory. This directory is automatically `.gitignored`. As already mentioned earlier, sensitive information **should never** be placed in the `conf/project` directory.

#### conf/local/credentials.yml
```yaml
azure:
   account_name: your_account_name
   access_key: here_goes_your_long_private_key_which_you_should_never_commit_to_git
```

Now, during initialisation of the `SparkSession`, configure your `azure` credentials as shown below:

```python
from kedro.config import load_config
from pyspark.sql import SparkSession

conf = load_config('path/to/conf')

account_name = conf['credentials']['azure']['account_name']
access_key = conf['credentials']['azure']['access_key']

spark = SparkSession.builder\
    .master("local[*]") \
    .appName("kedro") \
    .config('fs.azure.account.key.' + account_name + '.blob.core.windows.net', access_key) \
    .getOrCreate()
```

You should now be able to read data from `azure blob storage`, using hadoop's `awsbs` file system.
Example:

```python
from kedro.contrib.io.pyspark import SparkDataSet

bucket_name = 'your-bucket-name'
filepath = 'wasbs://' + bucket_name + '@' + account_name + '.blob.core.windows.net/dir_with_parquet_files'
azure_parquet = SparkDataSet(filepath, file_format='parquet')
azure_parquet.load()
```
