# Release 0.15.0

## Major features and improvements
* Added a new CLI command `kedro jupyter convert` to facilitate converting Jupyter notebook cells into Kedro nodes. 
* Added `KedroContext` base class which holds the configuration and Kedro's main functionality (catalog, pipeline, config).
* New I/O module `ParquetS3DataSet` when using Pandas. (by [@mmchougule](https://github.com/mmchougule)) 

## Bug fixes and other changes
* Documentation improvements
* `anyconfig` default log level changed from `INFO` to `WARNING`

## Breaking changes to the API
* Merged `FilepathVersionMixIn` and `S3VersionMixIn` under one abstract class `AbstractVersionedDataSet` which extends`AbstractDataSet`.

#### Migration guide from Kedro 0.14.* to Kedro 0.15.0
If you defined any custom dataset classes which support versioning in your project, you need to apply the following changes:

1. Make sure your dataset inherits from `AbstractVersionedDataSet` only.
2. Call `super().__init__()` with the appropriate arguments in the dataset's `__init__`. If storing on local filesystem, providing the filepath and the version is enough. Otherwise, you should also pass in an `exists_function` and a `glob_function` that emulate `exists` and `glob` in a different filesystem (see `CSVS3DataSet` as an example). 
3. Remove setting of the `_filepath` and `_version` attributes in the dataset's `__init__`, as this is take care of in the base abstract class.
4. Any calls to `_get_load_path` and `_get_save_path` methods should take no arguments.
5. Ensure you convert the output of `_get_load_path` and `_get_save_path` appropriately, as these now return [`PurePath`s](https://docs.python.org/3/library/pathlib.html#pure-paths) instead of strings.
6. Make sure `_check_paths_consistency` is called with [`PurePath`s](https://docs.python.org/3/library/pathlib.html#pure-paths) as input arguments, instead of strings.

## Thanks for supporting contributions
[Dmitry Vukolov](https://github.com/dvukolov), [Jo Stichbury](https://github.com/stichbury), [Angus Williams](https://github.com/awqb), [Deepyaman Datta](https://github.com/deepyaman), [Mayur Chougule](https://github.com/mmchougule)

# Release 0.14.3

## Major features and improvements
* Tab completion for catalog datasets in `ipython` or `jupyter` sessions. (Thank you [@datajoely](https://github.com/datajoely) and [@WaylonWalker](https://github.com/WaylonWalker))
* Added support for transcoding, an ability to decouple loading/saving mechanisms of a dataset from its storage location, denoted by adding '@' to the dataset name.
* Datasets have a new `release` function that instructs them to free any cached data. The runners will call this when the dataset is no longer needed downstream.

## Bug fixes and other changes
* Add support for pipeline nodes made up from partial functions.
* Expand user home directory `~` for TextLocalDataSet (see issue #19).
* Add a `short_name` property to `Node`s for a display-friendly (but not necessarily unique) name.
* Add Kedro project loader for IPython: `extras/kedro_project_loader.py`.
* Fix source file encoding issues with Python 3.5 on Windows.
* Fix local project source not having priority over the same source installed as a package, leading to local updates not being recognised.

## Breaking changes to the API
* Remove the max_loads argument from the `MemoryDataSet` constructor and from the `AbstractRunner.create_default_data_set` method.

## Thanks for supporting contributions
[Joel Schwarzmann](https://github.com/datajoely), [Alex Kalmikov](https://github.com/kalexqb)

# Release 0.14.2

## Major features and improvements
* Added Data Set transformer support in the form of AbstractTransformer and DataCatalog.add_transformer.

## Breaking changes to the API
* Merged the `ExistsMixin` into `AbstractDataSet`.
* `Pipeline.node_dependencies` returns a dictionary keyed by node, with sets of parent nodes as values; `Pipeline` and `ParallelRunner` were refactored to make use of this for topological sort for node dependency resolution and running pipelines respectively.
* `Pipeline.grouped_nodes` returns a list of sets, rather than a list of lists.

## Thanks for supporting contributions

[Darren Gallagher](https://github.com/dazzag24), [Zain Patel](https://github.com/mzjp2)

# Release 0.14.1

## Major features and improvements
* New I/O module `HDFS3DataSet`.

## Bug fixes and other changes
* Improved API docs.
* Template `run.py` will throw a warning instead of error if `credentials.yml`
  is not present.

## Breaking changes to the API
None


# Release 0.14.0:

The initial release of Kedro.

## Thanks to our main contributors

[Nikolaos Tsaousis](https://github.com/tsanikgr), [Ivan Danov](https://github.com/idanov), [Dmitrii Deriabin](https://github.com/DmitryDeryabin), [Gordon Wrigley](https://github.com/tolomea), [Yetunde Dada](https://github.com/yetudada), [Nasef Khan](https://github.com/nakhan98), [Kiyohito Kunii](https://github.com/921kiyo), [Nikolaos Kaltsas](https://github.com/nikos-kal), [Meisam Emamjome](https://github.com/misamae), [Peteris Erins](https://github.com/Pet3ris), [Lorena Balan](https://github.com/lorenabalan), [Richard Westenra](https://github.com/richardwestenra)

## Thanks for supporting contributions

Jo Stichbury, Aris Valtazanos, Fabian Peters, Guilherme Braccialli, Joel Schwarzmann, Miguel Beltre, Mohammed ElNabawy, Deepyaman Datta, Shubham Agrawal, Oleg Andreyev, Mayur Chougule, William Ashford, Ed Cannon, Nikhilesh Nukala, Sean Bailey, Vikram Tegginamath, Thomas Huijskens, Musa Bilal

We are also grateful to everyone who advised and supported us, filed issues or helped resolve them, asked and answered questions and were part of inspiring discussions.
