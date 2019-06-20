# Release 0.14.3

## Major features and improvements
* Tab completion for catalog datasets in `ipython` or `jupyter` sessions.
* Added support for transcoding, an ability to decouple loading/saving mechanisms of a dataset from its storage location. It is denoted by adding '@' to the dataset name. This will allow you to read the same dataset or file in two different ways.

## Bug fixes and other changes
* Add support for pipeline nodes made up from partial functions
* Any custom `AbstractDataSet` may be aware of how many times a pipeline run is going to load it by implementing `set_remaining_loads()`

## Breaking changes to the API

## Bug fixes and other changes
* Added Kedro project loader for IPython: `extras/kedro_project_loader.py`.

## Thanks for supporting contributions
[Nikolaos Tsaousis](https://github.com/tsanikgr), [Ivan Danov](https://github.com/idanov), [Gordon Wrigley](https://github.com/tolomea), [Yetunde Dada](https://github.com/yetudada), [Kiyohito Kunii](https://github.com/921kiyo), [Lorena Balan](https://github.com/lorenabalan), [Richard Westenra](https://github.com/richardwestenra), [Dmitrii Deriabin](https://github.com/DmitryDeryabin), [Joel Schwarzmann](https://github.com/datajoely)

# Release 0.14.2

## Major features and improvements
* Added Data Set transformer support in the form of AbstractTransformer and DataCatalog.add_transformer.

## Breaking changes to the API
* Merged the `ExistsMixin` into `AbstractDataSet`.
* `Pipeline.node_dependencies` returns a dictionary keyed by node, with sets of parent nodes as values; `Pipeline` and `ParallelRunner` were refactored to make use of this for topological sort for node dependency resolution and running pipelines respectively.
* `Pipeline.grouped_nodes` returns a list of sets, rather than a list of lists.

## Thanks for supporting contributions

[Nikolaos Tsaousis](https://github.com/tsanikgr), [Ivan Danov](https://github.com/idanov), [Gordon Wrigley](https://github.com/tolomea), [Yetunde Dada](https://github.com/yetudada), [Kiyohito Kunii](https://github.com/921kiyo), [Lorena Balan](https://github.com/lorenabalan), [Richard Westenra](https://github.com/richardwestenra), [Darren Gallagher](https://github.com/dazzag24), [Zain Patel](https://github.com/mzjp2)

# Release 0.14.1

## Major features and improvements
* New I/O module `HDFS3DataSet`.

## Bug fixes and other changes
* Improved API docs.
* Template `run.py` will throw a warning instead of error if `credentials.yml`
  is not present.

## Breaking changes to the API
None

## Thanks for supporting contributions

[Nikolaos Tsaousis](https://github.com/tsanikgr), [Ivan Danov](https://github.com/idanov), [Dmitrii Deriabin](https://github.com/DmitryDeryabin), [Gordon Wrigley](https://github.com/tolomea), [Nasef Khan](https://github.com/nakhan98), [Kiyohito Kunii](https://github.com/921kiyo), [Lorena Balan](https://github.com/lorenabalan), [Richard Westenra](https://github.com/richardwestenra)

# Release 0.14.0:

The initial release of Kedro.

## Thanks to our main contributors

[Nikolaos Tsaousis](https://github.com/tsanikgr), [Ivan Danov](https://github.com/idanov), [Dmitrii Deriabin](https://github.com/DmitryDeryabin), [Gordon Wrigley](https://github.com/tolomea), [Yetunde Dada](https://github.com/yetudada), [Nasef Khan](https://github.com/nakhan98), [Kiyohito Kunii](https://github.com/921kiyo), [Nikolaos Kaltsas](https://github.com/nikos-kal), [Meisam Emamjome](https://github.com/misamae), [Peteris Erins](https://github.com/Pet3ris), [Lorena Balan](https://github.com/lorenabalan), [Richard Westenra](https://github.com/richardwestenra)

## Thanks for supporting contributions

Jo Stichbury, Aris Valtazanos, Fabian Peters, Guilherme Braccialli, Joel Schwarzmann, Miguel Beltre, Mohammed ElNabawy, Deepyaman Datta, Shubham Agrawal, Oleg Andreyev, Mayur Chougule, William Ashford, Ed Cannon, Nikhilesh Nukala, Sean Bailey, Vikram Tegginamath, Thomas Huijskens, Musa Bilal

We are also grateful to everyone who advised and supported us, filed issues or helped resolve them, asked and answered questions and were part of inspiring discussions.
