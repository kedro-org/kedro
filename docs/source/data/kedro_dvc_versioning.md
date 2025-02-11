# Data and pipeline versioning with Kedro and DVC

This document explains how to use [DVC](https://dvc.org/), a command line tool and VS Code Extension to help you develop reproducible machine learning projects, to version datasets and pipelines in your Kedro project.

This tutorial assumes you have experience with the Git CLI and Kedro CLI commands but does not require any prior knowledge of DVC.

## Versioning data with .dvc files

### Initialising the repository

For this example, we will be using a Kedro `spaceflights-pandas` starter project, which includes preconfigured datasets and pipelines. To create this starter project locally, use the command:

`kedro new --starter=spaceflights-pandas --name=space-dvc`

For more information about starter projects, visit the [Kedro starters documentation](https://docs.kedro.org/en/stable/starters/starters.html) page.

To use DVC as a Python library, install it using `pip` or `conda`, for example:
`pip install dvc`

Since DVC works alongside Git to track data changes, initialise the Kedro project as a git repository: `git init`.

Then, initialize DVC in the project: `dvc init`. This will create the `.dvc` directory inside the project.

You should see a message such as:

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

### First commits

DVC helps manage large datasets that should not be stored directly in Git. Instead of adding dataset files to Git, DVC generates small metadata files that Git tracks instead.

These metadata files store information about the actual dataset, such as its hash and location. More information about the structure of the .dvc file can be found in the [DVC documentation](https://dvc.org/doc/user-guide/project-structure/dvc-files#dvc-files).

Suppose you have a dataset in your project, such as:

```yaml
companies:
  type: pandas.CSVDataset
  filepath: data/01_raw/companies.csv
```

Since we initialized a new Git repository with `git init` on the previous step, we can now make an initial commit containing all of the files in the project:

```bash
git add .
git commit -m "First commit, initial structure from the starter"
```

Because of the location of the datasets files in the project template, it will be necessary to make sure that the following line is present in the projectg's `.gitignore` file so we allow for the `.dvc` files to be commited:

```bash
!*.dvc
```

We want to use DVC to track and version our dataset file, so we remove it from Git and commit the change:

 ```bash
 git rm -r --cached 'data/01_raw/companies.csv'
 git commit -m "Stop tracking data/01_raw/companies.csv"
 ```

 Finally, we start tracking it with DVC:

 ```bash
 dvc add data/01_raw/companies.csv
 ```

This generates the `companies.csv.dvc` file which can be committed to git. This small, human-readable metadata file acts as a placeholder for the original data for the purpose of Git tracking.

Once updated, add the `.dvc` file to Git and commit the changes:

```bash
git add data/01_raw/companies.csv.dvc
git commit -m "Track companies.csv dataset with DVC"
```

### Going back to a previous version of the data

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

### Storing data remotely

DVC remotes provide access to external storage locations to track and share your data and ML models with the `dvc push` and `dvc pull` commands. Usually, those will be shared between devices or team members who are working on a project. It supports [several different storage types](https://dvc.org/doc/user-guide/data-management/remote-storage#supported-storage-types).

For example:

```bash
dvc remote add myremote s3://mybucket
kedro run
git add .
git commit -m "Update"
dvc push
```

### Going back to a previous version of the data, stored remotely

```bash
git checkout <commit hash> data/01_raw/companies.csv.dvc
dvc checkout
dvc pull
```

## Versioning with DVC data pipelines

While the previous method allows you to version datasets, it comes with some limitations:

- Intermediate and output datasets must be added to DVC manually.
- Parameters and code changes are not explicitly tracked.
- Artefacts and metrics cannot be tracked effectively.

To address these issues, you can define Kedro pipelines as DVC stages in the dvc.yaml file. The list of stages is typically the most important part of a dvc.yaml file, though the file can also be used to configure artifacts, metrics, params, and plots, either as part of a stage definition or on their own.

### Defining Kedro pipelines as DVC stages

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

### Updating a dataset

If one of the datasets is updated, you can rerun only the pipelines affected by the change.

The command `dvc repro` executes pipelines where outputs or dependencies have changed.

### Tracking code changes

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

### Tracking parameters

To track parameters, you can include them under the params section in `dvc.yaml`.

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

### Running experiments with different parameters

To experiment with different parameter values, update the parameter in `parameters.yaml` and then run the pipelines with `dvc repro`.

Compare parameter changes between runs with `dvc params diff`:

```bash
Path                                   Param                       HEAD    workspace
conf/base/parameters_data_science.yml  model_options.features      -       ['engines', 'passenger_capacity', 'crew', 'd_check_complete', 'moon_clearance_complete', 'iata_approved', 'company_rating', 'review_scores_rating']
conf/base/parameters_data_science.yml  model_options.random_state  -       3
conf/base/parameters_data_science.yml  model_options.test_size     -       0.2
```
