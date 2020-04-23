# Journal

> *Note:* This documentation is based on `Kedro 0.15.9`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

## Overview
Journal in Kedro allows you to save the history of pipeline. This functionality helps you reproduce results and gives you an ability to investigate failures in your workflow.
Each pipeline run creates a log file formatted as `journal_YYYY-MM-DDThh.mm.ss.sssZ.log`, which is saved in the `logs/journals` directory. The log file contains two kinds of journal records.

### Context journal record

A context journal record captures all the necessary information to reproduce the pipeline run, and has the following JSON format:

```json
{
    "type": "ContextJournalRecord",
    "run_id": "2019-10-01T09.15.57.289Z",
    "project_path": "<path-to-project>/src/kedro-tutorial",
    "env": "local",
    "kedro_version": "0.15.9",
    "tags": [],
    "from_nodes": [],
    "to_nodes": [],
    "node_names": [],
    "from_inputs": [],
    "load_versions": {},
    "pipeline_name": null,
    "git_sha": "48dd0d3"
}
```

You will observe `run_id`, a unique timestamp used to identify a pipeline run, in the context journal record, as well as a `git_sha`, that corresponds to the current git commit hash when your project is tracked by `git`. If your project is not tracked by `git`, then the `git_sha` will be `null`, and you'll see a warning message in your `logs/info.log` as follows:

```bash
2019-10-01 10:31:13,352 - kedro.versioning.journal - WARNING - Unable to git describe /<path-to-project>/src/kedro-tutorial
```

### Dataset journal record

A dataset journal record tracks versioned dataset `load` and `save` operations, it is tied to the dataset name and `run_id`. The `version` attribute stores the exact timestamp used by the `load` or `save` operation. Dataset journal currently records `load` and `save` operations only for the datasets with enabled versioning. Please see [Versioning section](./08_advanced_io.md#versioning) for more information about data versioning feature and the list of currently supported datasets.

The dataset journal record has the following JSON format:

```json
{
    "type": "DatasetJournalRecord",
    "run_id": "2019-10-01T09.15.57.289Z",
    "name": "example_train_x",
    "operation": "load",
    "version": "2019-10-01T09.15.57.289Z"
}
```

> ❗While the context journal record is always logged at every run time of your pipeline, dataset journal record is only logged when `load` or `save` method is invoked for [versioned](./04_data_catalog.md#versioning-datasets-and-ml-models) dataset in `DataCatalog`.

## Steps to manually reproduce your code and run the previous pipeline

Journals must be persisted to manually reproduce your specific pipeline run. You can keep journals corresponding to checkpoints in your development workflow in your source control repo. Once you have found a version you would like to revert to, follow the below steps:

1. Checkout a commit from `git_sha` in the context journal record by running the following `git` command in your terminal:
```bash
git checkout <git_sha>
```
> *Note:* If you want to go back to the latest commit in the current branch, you can run `git checkout <branch-name>`.

2. Verify that the installed Kedro version is the same as the `project_version` in `src/<project-package>/run.py` by running `kedro --version`.
    - If the installed Kedro version does not match the `project_version`, verify that there are no changes that affect your project between the different Kedro versions by looking at [`RELEASE.md`](https://github.com/quantumblacklabs/kedro/blob/master/RELEASE.md), then update the Kedro version by pinning the `kedro==project_version` in `requirements.txt` and run `kedro install` in your terminal.

3. Run the pipeline with the corresponding versioned datasets' load versions fixed. Open the corresponding journal log file found in `logs/journals`, find dataset journal record, list all the dataset load versions and run the following command in your terminal:
```bash
kedro run --load-version="dataset1:YYYY-MM-DDThh.mm.ss.sssZ" --load-version="dataset2:YYYY-MM-DDThh.mm.ss.sssZ"
```
where `--load-version` should contain a dataset name and load version timestamp separated by `:`.
