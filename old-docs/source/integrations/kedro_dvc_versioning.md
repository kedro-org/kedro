# Data and pipeline versioning with Kedro and DVC

This document explains how to use [DVC](https://dvc.org/) to version datasets and pipelines in your Kedro project. DVC is a tool to develop reproducible machine learning projects. It can be installed on Visual Studio Code, any system terminal, and used as a Python library.

This tutorial assumes you have experience with the Git CLI and Kedro CLI commands but does not require any prior knowledge of DVC.

## Versioning data with .dvc files

### Initialising the repository

For this example, you will be using a Kedro `spaceflights-pandas` starter project, which includes pre-configured datasets and pipelines. To create this starter project locally, use the command:

`kedro new --starter=spaceflights-pandas --name=space-dvc`

For more information about starter projects, see the [Kedro starters documentation](https://docs.kedro.org/en/stable/starters/starters.html) page.

To use DVC as a Python library, install it using `pip` or `conda`, for example:

```bash
`pip install dvc`
```

Since DVC works alongside Git to track data changes, initialise the Kedro project as a git repository:

```bash
`git init`
```

Then, initialise DVC in the project:

```bash
`dvc init`
```

This will create the `.dvc` directory inside the project. You should see a message such as:

```bash
Initialized DVC repository.

You can now commit the changes to git.

+---------------------------------------------------------------------+
|                                                                     |
|        DVC has enabled anonymous aggregate usage analytics.         |
|     Read the analytics documentation (and how to opt-out) here:     |
|             <https://dvc.org/doc/user-guide/analytics>              |
|                                                                     |
+---------------------------------------------------------------------+
```

Since you initialised a new Git repository with `git init` on the previous step, you can now make an initial commit containing all of the files in the project:

```bash
git add .
git commit -m "First commit, initial structure from the starter"
```

### Tracking your data with DVC

DVC helps manage large datasets that should not be stored directly in Git. Instead of adding dataset files to Git, DVC generates small metadata files that Git tracks instead.

These metadata files store information about the actual dataset, such as its hash and location. More information about the structure of the `.dvc` file can be found in the [DVC documentation](https://dvc.org/doc/user-guide/project-structure/dvc-files#dvc-files).

Verify that your project catalog contains this dataset definition:

```yaml
companies:
  type: pandas.CSVDataset
  filepath: data/01_raw/companies.csv
```

Due to the location of the dataset files in the project template, you must ensure the following line is present in the `.gitignore` file to allow `.dvc` files to be committed:

```bash
!*.dvc
```

We want to use DVC to track and version our dataset file, so you remove it from Git and commit the change:

 ```bash
 git rm -r --cached 'data/01_raw/companies.csv'
 git commit -m "Stop tracking data/01_raw/companies.csv"
 ```

 We can then start tracking it with DVC:

 ```bash
 dvc add data/01_raw/companies.csv
 ```

This generates the `companies.csv.dvc` file which can be committed to git. This small, human-readable metadata file acts as a placeholder for the original data for Git tracking.

Once updated, add the `.dvc` file to Git and commit the changes:

```bash
git add data/01_raw/companies.csv.dvc
git commit -m "Track companies.csv dataset with DVC"
```

### Going back to a previous version of the data

First, let's create a different version of the `companies.csv` file by adding a dummy line to it.

```bash
echo "000,100%,Example,1.0,f" >> data/01_raw/companies.csv
```

By using the command `tail data/01_raw/companies.csv`, you can verify that the line has been added to the file:

```bash
6957,,Rwanda,1.0,t
7554,100%,,1105.0,f
34243,95%,Uzbekistan,1.0,f
12502,89%,Denmark,1.0,f
20213,,Russian Federation,1.0,f
2235,100%,Guinea,1.0,f
2353,100%,Senegal,2.0,t
49772,100%,Jersey,1.0,f
16548,90%,,2.0,f
000,100%,Example,1.0,f
```

Then you can track the changes with DVC, and commit them to Git:

```bash
dvc add data/01_raw/companies.csv
git add data/01_raw/companies.csv.dvc
git commit -m "Track dataset changes with DVC"
```

DVC integrates with Git to manage different dataset versions. If you need to restore a previous version of a dataset, first identify the commit containing the desired version. You can use:

```bash
git log -- data/01_raw/companies.csv.dvc
```

To display the commit hashes associated with this file. Once you find the desired commit, run:

```bash
git checkout <commit_hash> data/01_raw/companies.csv.dvc
dvc checkout
```

The first command will restore the `.dvc` metadata file to its previous version. The second uses the metadata file to restore the corresponding dataset.

```bash
Building workspace index
Comparing indexes
Applying changes
M       data/01_raw/companies.csv
```

Using the command `tail data/01_raw/companies.csv` again shows that the dataset file has been restored to a previous version.

```bash
1618,100%,,1.0,t
6957,,Rwanda,1.0,t
7554,100%,,1105.0,f
34243,95%,Uzbekistan,1.0,f
12502,89%,Denmark,1.0,f
20213,,Russian Federation,1.0,f
2235,100%,Guinea,1.0,f
2353,100%,Senegal,2.0,t
49772,100%,Jersey,1.0,f
16548,90%,,2.0,f
```

## Advanced use cases

### How to store data remotely

DVC remotes provide access to external storage locations to track and share your data and ML models with the `dvc push` and `dvc pull` commands. Those will be shared between devices or team members who are working on a project. It supports several different storage types, like Amazon S3, Azure Blob Storage or Google Cloud Storage, as well as self-hosted options. For more detail on this subject, see the [DVC documentation on remote storage](https://dvc.org/doc/user-guide/data-management/remote-storage#supported-storage-types).

For example:

```bash
dvc remote add myremote s3://mybucket
kedro run
git add .
git commit -m "Update"
dvc push
```

### How to go back to a previous version of the data, stored remotely

```bash
git checkout <commit hash> data/01_raw/companies.csv.dvc
dvc checkout
dvc pull
```

### How to version with DVC data pipelines

While the previous method allows you to version datasets, it comes with some limitations, as DVC requires the files to be tracked to be added manually:

- Intermediate and output datasets must be added to DVC individually.
- Parameters and code changes are not explicitly tracked.
- Artifacts and metrics can be cumbersome to track.

To address these issues, you can define Kedro pipelines as DVC stages in the dvc.yaml file. The list of stages is typically the most important part of a dvc.yaml file. The file can also be used to configure artifacts, metrics, parameters, and plots, either as part of a stage definition or on their own.

For more information on the configuration of those files, see [the documentation on dvc.yaml](https://dvc.org/doc/user-guide/project-structure/dvcyaml-files#dvcyaml).

### How to define Kedro pipelines as DVC stages


Here is an example configuration for dvc.yaml:

```yaml
stages:
  data_processing:
    cmd: kedro run --pipeline data_processing
    deps:
      - data/01_raw/companies.csv
      - data/01_raw/reviews.csv
      - data/01_raw/shuttles.xlsx
    outs:
      - data/02_intermediate/preprocessed_companies.parquet
      - data/02_intermediate/preprocessed_shuttles.parquet
      - data/03_primary/model_input_table.parquet

  data_science:
    cmd: kedro run --pipeline data_science
    deps:
      - data/03_primary/model_input_table.parquet
    outs:
      - data/06_models/regressor.pickle
```

Run the pipeline with:

```bash
dvc repro
```

### How to update a dataset

If one of the datasets is updated, you can rerun only the pipelines affected by the change.

The command `dvc repro` executes pipelines where outputs or dependencies have changed.

### How to track code changes

You can track changes to your code by adding the relevant files to the `deps` section in `dvc.yaml`.

```yaml
stages:
  data_processing:
    cmd: kedro run --pipeline data_processing
    deps:
      - data/01_raw/companies.csv
      - data/01_raw/reviews.csv
      - data/01_raw/shuttles.xlsx
      - src/space_dvc/pipelines/data_processing/nodes.py
      - src/space_dvc/pipelines/data_processing/pipeline.py
    outs:
      - data/02_intermediate/preprocessed_companies.parquet
      - data/02_intermediate/preprocessed_shuttles.parquet
      - data/03_primary/model_input_table.parquet
```

After applying the desired code changes, run `dvc repro`. The output should confirm the updates on the `dvc.lock` file, if any:

```bash
Updating lock file 'dvc.lock'
Use `dvc push` to send your updates to remote storage.
```

After that, they can be pushed to remote storage with the `dvc push` command.

### How to track parameters

To track parameters, you can include them under the `params` section in `dvc.yaml`.

```yaml
stages:
  data_science:
    cmd: kedro run --pipeline data_science
    deps:
      - data/03_primary/model_input_table.parquet
      - src/space_dvc/pipelines/data_science/nodes.py
      - src/space_dvc/pipelines/data_science/pipeline.py
    params:
      - conf/base/parameters_data_science.yaml:
          - model_options
    outs:
      - data/06_models/regressor.pickle
```

Run the pipeline and push the changes:

```bash
dvc repro
dvc push
```

### How to run experiments with different parameters

To experiment with different parameter values, update the parameter in `parameters.yaml` and then run the pipelines with `dvc repro`.

Compare parameter changes between runs with `dvc params diff`:

```bash
Path                                   Param                       HEAD    workspace
conf/base/parameters_data_science.yml  model_options.features      -       ['engines', 'passenger_capacity', 'crew', 'd_check_complete', 'moon_clearance_complete', 'iata_approved', 'company_rating', 'review_scores_rating']
conf/base/parameters_data_science.yml  model_options.random_state  -       3
conf/base/parameters_data_science.yml  model_options.test_size     -       0.2
```
