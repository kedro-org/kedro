from codecs import open
from glob import glob
from itertools import chain
from os import path

from setuptools import setup

name = "kedro"
here = path.abspath(path.dirname(__file__))

# at least 1.3 to be able to use XMLDataSet and pandas integration with fsspec
PANDAS = "pandas~=1.3"
SPARK = "pyspark>=2.2, <4.0"
HDFS = "hdfs>=2.5.8, <3.0"
S3FS = "s3fs>=0.3.0, <0.5"

# get the dependencies and installs
with open("dependency/requirements.txt", encoding="utf-8") as f:
    requires = [x.strip() for x in f if x.strip()]

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
dask_require = {"dask.ParquetDataSet": ["dask[complete]~=2021.10", "triad>=0.6.7, <1.0"]}
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
    "pandas.GBQTableDataSet": [PANDAS, "pandas-gbq>=0.12.0, <0.18.0"],
    "pandas.GBQQueryDataSet": [PANDAS, "pandas-gbq>=0.12.0, <0.18.0"],
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
pickle_require = {"pickle.PickleDataSet": ["compress-pickle[lz4]~=2.1.0"]}
pillow_require = {"pillow.ImageDataSet": ["Pillow~=9.0"]}
video_require = {
    "video.VideoDataSet": ["opencv-python~=4.5.5.64"]
}
plotly_require = {
    "plotly.PlotlyDataSet": [PANDAS, "plotly>=4.8.0, <6.0"],
    "plotly.JSONDataSet": ["plotly>=4.8.0, <6.0"],
}
redis_require = {"redis.PickleDataSet": ["redis~=4.1"]}
spark_require = {
    "spark.SparkDataSet": [SPARK, HDFS, S3FS],
    "spark.SparkHiveDataSet": [SPARK, HDFS, S3FS],
    "spark.SparkJDBCDataSet": [SPARK, HDFS, S3FS],
    "spark.DeltaTableDataSet": [SPARK, HDFS, S3FS, "delta-spark>=1.0, <3.0"],
}
svmlight_require = {"svmlight.SVMLightDataSet": ["scikit-learn~=1.0.2", "scipy~=1.7.3"]}
tensorflow_required = {
    "tensorflow.TensorflowModelDataset": [
        # currently only TensorFlow V2 supported for saving and loading.
        # V1 requires HDF5 and serialises differently
        "tensorflow~=2.0"
    ]
}
yaml_require = {"yaml.YAMLDataSet": [PANDAS, "PyYAML>=4.2, <7.0"]}

extras_require = {
    "api": _collect_requirements(api_require),
    "biosequence": _collect_requirements(biosequence_require),
    "dask": _collect_requirements(dask_require),
    "docs": [
        # docutils>=0.17 changed the HTML
        # see https://github.com/readthedocs/sphinx_rtd_theme/issues/1115
        "docutils==0.16",
        "sphinx~=5.3.0",
        "sphinx_rtd_theme==1.2.0",
        # Regression on sphinx-autodoc-typehints 1.21
        # that creates some problematic docstrings
        "sphinx-autodoc-typehints==1.20.2",
        "sphinx_copybutton==0.3.1",
        "sphinx-notfound-page",
        "ipykernel>=5.3, <7.0",
        "sphinxcontrib-mermaid~=0.7.1",
        "myst-parser~=1.0.0",
        "Jinja2<3.1.0",
        # https://github.com/kedro-org/kedro-plugins/issues/141
        # https://github.com/kedro-org/kedro-plugins/issues/143
        "kedro-datasets[api,biosequence,dask,geopandas,matplotlib,holoviews,networkx,pandas,pillow,polars,video,plotly,redis,spark,svmlight,yaml]==1.1.1",
        "kedro-datasets[tensorflow]==1.1.1; platform_system != 'Darwin' or platform_machine != 'arm64'",
        "tensorflow-macos~=2.0; platform_system == 'Darwin' and platform_machine == 'arm64'",
    ],
    "geopandas": _collect_requirements(geopandas_require),
    "matplotlib": _collect_requirements(matplotlib_require),
    "holoviews": _collect_requirements(holoviews_require),
    "networkx": _collect_requirements(networkx_require),
    "pandas": _collect_requirements(pandas_require),
    "pickle": _collect_requirements(pickle_require),
    "pillow": _collect_requirements(pillow_require),
    "video": _collect_requirements(video_require),
    "plotly": _collect_requirements(plotly_require),
    "redis": _collect_requirements(redis_require),
    "spark": _collect_requirements(spark_require),
    "svmlight": _collect_requirements(svmlight_require),
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
    **pickle_require,
    **pillow_require,
    **video_require,
    **plotly_require,
    **spark_require,
    **svmlight_require,
    **tensorflow_required,
    **yaml_require,
}

extras_require["all"] = _collect_requirements(extras_require)

setup(
    package_data={
        name: ["py.typed", "test_requirements.txt"] + template_files
    },
    extras_require=extras_require,
)
