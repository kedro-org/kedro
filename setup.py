from glob import glob
from itertools import chain

from setuptools import setup

# at least 1.3 to be able to use XMLDataSet and pandas integration with fsspec
PANDAS = "pandas~=1.3"
SPARK = "pyspark>=2.2, <3.4"
HDFS = "hdfs>=2.5.8, <3.0"
S3FS = "s3fs>=0.3.0, <0.5"

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
holoviews_require = {"holoviews.HoloviewsWriter": ["holoviews>=1.13.0"]}
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
        "tensorflow~=2.0; platform_system != 'Darwin' or platform_machine != 'arm64'",
        # https://developer.apple.com/metal/tensorflow-plugin/
        "tensorflow-macos~=2.0; platform_system == 'Darwin' and platform_machine == 'arm64'",
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
        "kedro-datasets[all]~=1.7.0",
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
extras_require["test"] = [
    "adlfs>=2021.7.1, <=2022.2; python_version == '3.7'",
    "adlfs~=2023.1; python_version >= '3.8'",
    "bandit>=1.6.2, <2.0",
    "behave==1.2.6",
    "biopython~=1.73",
    "blacken-docs==1.9.2",
    "black~=22.0",
    "compress-pickle[lz4]~=2.1.0",
    "coverage[toml]",
    "dask[complete]~=2021.10",  # pinned by Snyk to avoid a vulnerability
    "delta-spark>=1.2.1; python_version >= '3.11'",  # 1.2.0 has a bug that breaks some of our tests: https://github.com/delta-io/delta/issues/1070
    "delta-spark~=1.2.1; python_version < '3.11'",
    "dill~=0.3.1",
    "filelock>=3.4.0, <4.0",
    "gcsfs>=2021.4, <=2023.1; python_version == '3.7'",
    "gcsfs>=2023.1, <2023.3; python_version >= '3.8'",
    "geopandas>=0.6.0, <1.0",
    "hdfs>=2.5.8, <3.0",
    "holoviews>=1.13.0",
    "import-linter[toml]==1.8.0",
    "ipython>=7.31.1, <8.0; python_version < '3.8'",
    "ipython~=8.10; python_version >= '3.8'",
    "isort~=5.0",
    "Jinja2<3.1.0",
    "joblib>=0.14",
    "jupyterlab_server>=2.11.1, <2.16.0",  # 2.16.0 requires importlib_metedata >= 4.8.3 which conflicts with flake8 requirement
    "jupyterlab~=3.0, <3.6.0",  # 3.6.0 requires jupyterlab_server~=2.19
    "jupyter~=1.0",
    "lxml~=4.6",
    "matplotlib>=3.0.3, <3.4; python_version < '3.10'",  # 3.4.0 breaks holoviews
    "matplotlib>=3.5, <3.6; python_version >= '3.10'",
    "memory_profiler>=0.50.0, <1.0",
    "moto==1.3.7; python_version < '3.10'",
    "moto==4.1.12; python_version >= '3.10'",
    "networkx~=2.4",
    "opencv-python~=4.5.5.64",
    "openpyxl>=3.0.3, <4.0",
    "pandas-gbq>=0.12.0, <0.18.0; python_version < '3.11'",
    "pandas-gbq>=0.18.0; python_version >= '3.11'",
    "pandas~=1.3  # 1.3 for read_xml/to_xml",
    "Pillow~=9.0",
    "plotly>=4.8.0, <6.0",
    "pre-commit>=2.9.2, <3.0",  # The hook `mypy` requires pre-commit version 2.9.2.
    "pyarrow>=1.0; python_version < '3.11'",
    "pyarrow>=7.0; python_version >= '3.11'",  # Adding to avoid numpy build errors
    "pylint>=2.17.0, <3.0",
    "pyproj~=3.0",
    "pyspark>=2.2, <3.4; python_version < '3.11'",
    "pyspark>=3.4; python_version >= '3.11'",
    "pytest-cov~=3.0",
    "pytest-mock>=1.7.1, <2.0",
    "pytest-xdist[psutil]~=2.2.1",
    "pytest~=7.2",
    "redis~=4.1",
    "requests-mock~=1.6",
    "requests~=2.20",
    "s3fs>=0.3.0, <0.5",  # Needs to be at least 0.3.0 to make use of `cachable` attribute on S3FileSystem.
    "scikit-learn>=1.0.2,<2",
    "scipy>=1.7.3",
    "semver",
    "SQLAlchemy~=1.2",
    "tables~=3.6.0; platform_system == 'Windows' and python_version<'3.8'",
    "tables~=3.8.0; platform_system == 'Windows' and python_version>='3.8'",  # Import issues with python 3.8 with pytables pinning to 3.8.0 fixes this https://github.com/PyTables/PyTables/issues/933#issuecomment-1555917593
    "tables~=3.6; platform_system != 'Windows'",
    "tensorflow~=2.0; platform_system != 'Darwin' or platform_machine != 'arm64'",
    # https://developer.apple.com/metal/tensorflow-plugin/
    "tensorflow-macos~=2.0; platform_system == 'Darwin' and platform_machine == 'arm64'",
    "triad>=0.6.7, <1.0",
    "trufflehog~=2.1",
    "xlsxwriter~=1.0",
]

setup(
    package_data={
        "kedro": ["py.typed"] + template_files
    },
    extras_require=extras_require,
)
