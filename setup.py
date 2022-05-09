import re
from codecs import open
from glob import glob
from itertools import chain
from os import path

from setuptools import find_packages, setup

name = "kedro"
here = path.abspath(path.dirname(__file__))

# at least 1.3 to be able to use XMLDataSet and pandas integration with fsspec
PANDAS = "pandas~=1.3"
SPARK = "pyspark>=2.2, <4.0"
HDFS = "hdfs>=2.5.8, <3.0"
S3FS = "s3fs>=0.3.0, <0.5"

# get package version
with open(path.join(here, name, "__init__.py"), encoding="utf-8") as f:
    result = re.search(r'__version__ = ["\']([^"\']+)', f.read())

    if not result:
        raise ValueError("Can't find the version in kedro/__init__.py")

    version = result.group(1)

# get the dependencies and installs
with open("requirements.txt", encoding="utf-8") as f:
    requires = [x.strip() for x in f if x.strip()]

# get test dependencies and installs
with open("test_requirements.txt", encoding="utf-8") as f:
    test_requires = [x.strip() for x in f if x.strip() and not x.startswith("-r")]


# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    readme = f.read()

template_files = []
for pattern in ["**/*", "**/.*", "**/.*/**", "**/.*/.**"]:
    template_files.extend(
        [
            name.replace("kedro/", "", 1)
            for name in glob("kedro/templates/" + pattern, recursive=True)
        ]
    )


def _collect_requirements(requires):
    return sorted(set(chain.from_iterable(requires.values())))


api_require = {"api.APIDataSet": ["requests~=2.20"]}
biosequence_require = {"biosequence.BioSequenceDataSet": ["biopython~=1.73"]}
dask_require = {"dask.ParquetDataSet": ["dask[complete]~=2021.10"]}
geopandas_require = {
    "geopandas.GeoJSONDataSet": ["geopandas>=0.6.0, <1.0", "pyproj~=3.0"]
}
matplotlib_require = {"matplotlib.MatplotlibWriter": ["matplotlib>=3.0.3, <4.0"]}
holoviews_require = {"holoviews.HoloviewsWriter": ["holoviews~=1.13.0"]}
networkx_require = {"networkx.NetworkXDataSet": ["networkx~=2.4"]}
pandas_require = {
    "pandas.CSVDataSet": [PANDAS],
    "pandas.ExcelDataSet": [PANDAS, "openpyxl>=3.0.6, <4.0"],
    "pandas.FeatherDataSet": [PANDAS],
    "pandas.GBQTableDataSet": [PANDAS, "pandas-gbq>=0.12.0, <1.0"],
    "pandas.GBQQueryDataSet": [PANDAS, "pandas-gbq>=0.12.0, <1.0"],
    "pandas.HDFDataSet": [
        PANDAS,
        "tables~=3.6.0; platform_system == 'Windows'",
        "tables~=3.6; platform_system != 'Windows'",
    ],
    "pandas.JSONDataSet": [PANDAS],
    "pandas.ParquetDataSet": [PANDAS, "pyarrow>=1.0, <7.0"],
    "pandas.SQLTableDataSet": [PANDAS, "SQLAlchemy~=1.2"],
    "pandas.SQLQueryDataSet": [PANDAS, "SQLAlchemy~=1.2"],
    "pandas.XMLDataSet": [PANDAS, "lxml~=4.6"],
    "pandas.GenericDataSet": [PANDAS],
}
pillow_require = {"pillow.ImageDataSet": ["Pillow~=9.0"]}
plotly_require = {
    "plotly.PlotlyDataSet": [PANDAS, "plotly>=4.8.0, <6.0"],
    "plotly.JSONDataSet": ["plotly>=4.8.0, <6.0"],
}
redis_require = {"redis.PickleDataSet": ["redis~=4.1"]}
spark_require = {
    "spark.SparkDataSet": [SPARK, HDFS, S3FS],
    "spark.SparkHiveDataSet": [SPARK, HDFS, S3FS],
    "spark.SparkJDBCDataSet": [SPARK, HDFS, S3FS],
    "spark.DeltaTableDataSet": [SPARK, HDFS, S3FS, "delta-spark~=1.0"],
}
tensorflow_required = {
    "tensorflow.TensorflowModelDataset": [
        # currently only TensorFlow V2 supported for saving and loading.
        # V1 requires HDF5 and serialises differently
        "tensorflow~=2.0"
    ]
}
yaml_require = {"yaml.YAMLDataSet": [PANDAS, "PyYAML>=4.2, <6.0"]}

extras_require = {
    "api": _collect_requirements(api_require),
    "biosequence": _collect_requirements(biosequence_require),
    "dask": _collect_requirements(dask_require),
    "docs": [
        "docutils==0.16",
        "sphinx~=3.4.3",
        "sphinx_rtd_theme==0.4.1",
        "nbsphinx==0.8.1",
        "nbstripout~=0.4",
        "recommonmark==0.7.1",
        "sphinx-autodoc-typehints==1.11.1",
        "sphinx_copybutton==0.3.1",
        "ipykernel>=5.3, <7.0",
    ],
    "geopandas": _collect_requirements(geopandas_require),
    "matplotlib": _collect_requirements(matplotlib_require),
    "holoviews": _collect_requirements(holoviews_require),
    "networkx": _collect_requirements(networkx_require),
    "pandas": _collect_requirements(pandas_require),
    "pillow": _collect_requirements(pillow_require),
    "plotly": _collect_requirements(plotly_require),
    "redis": _collect_requirements(redis_require),
    "spark": _collect_requirements(spark_require),
    "tensorflow": _collect_requirements(tensorflow_required),
    "yaml": _collect_requirements(yaml_require),
    **api_require,
    **biosequence_require,
    **dask_require,
    **geopandas_require,
    **matplotlib_require,
    **holoviews_require,
    **networkx_require,
    **pandas_require,
    **pillow_require,
    **plotly_require,
    **spark_require,
    **tensorflow_required,
    **yaml_require,
}

extras_require["all"] = _collect_requirements(extras_require)

setup(
    name=name,
    version=version,
    description="Kedro helps you build production-ready data and analytics pipelines",
    license="Apache Software License (Apache 2.0)",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/kedro-org/kedro",
    python_requires=">=3.7, <3.11",
    packages=find_packages(exclude=["docs*", "tests*", "tools*", "features*"]),
    include_package_data=True,
    tests_require=test_requires,
    install_requires=requires,
    author="Kedro",
    entry_points={"console_scripts": ["kedro = kedro.framework.cli:main"]},
    package_data={
        name: ["py.typed", "test_requirements.txt"] + template_files
    },
    zip_safe=False,
    keywords="pipelines, machine learning, data pipelines, data science, data engineering",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    extras_require=extras_require,
)
