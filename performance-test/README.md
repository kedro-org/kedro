# performance-test

## Overview

This is a test project meant to simulate delays in specific parts of a Kedro pipeline. It's supposed to be a tool to gauge pipeline performance and be used to compare in-development changes to Kedro with an already stable release version.

## Usage

There are three delay parameters that can be set in this project:

**hook_delay** - Simulates slow-loading hooks due to it performing complex operations or accessing external services that can suffer from latency.

**dataset_load_delay** - Simulates a delay in loading a dataset, because of a large size or connection latency, for example.

**file_save_delay** - Simulates a delay in saving an output file, because of, for example, connection delay in accessing remote storage.

When invoking the `kedro run` command, you can pass the desired value in seconds for each delay as a parameter using the `--params` flag. For example:

`kedro run --params=hook_delay=5,dataset_load_delay=5,file_save_delay=5`
