# Transformers

Welcome to `kedro.extras.transformers`, the home of Kedro's dataset transformers. Transformers intercept the load and save operations on Kedro datasets. Use cases that transformers enable include:
 - Performing data validation,
 - Tracking operation performance,
 - And, converting data between formats (although we would recommend [transcoding](https://kedro.readthedocs.io/en/stable/04_user_guide/04_data_catalog.html#transcoding-datasets) for this).

Further information on [transformers](https://kedro.readthedocs.io/en/stable/04_user_guide/04_data_catalog.html#transforming-datasets) has been added to the documentation.

## What transformers are currently supported?
View a full list of supported transformers [**here**](https://kedro.readthedocs.io/en/stable/kedro.extras.transformers.html).

Examples of transformers supported include:
 - **A dataset time profiler**: A transformer that logs the runtime of data set load and save calls
 - **A dataset memory profiler**: A transformer that logs the maximum memory consumption during load and save calls

### What pre-requisites are required for the dataset memory profiler?

On Unix-like operating systems, you will need to install a C-compiler and related build tools for your platform.

 #### macOS
 To install `Command Line Tools for Xcode`, run the following from the terminal:

 ```bash
 xcode-select --install
 ```

 #### GNU / Linux

 ##### Debian / Ubuntu

 The following command (run with root permissions) will install the `build-essential` metapackage for Debian-based distributions:

 ```bash
 apt-get update && apt-get install build-essential
 ```

 ##### Red Hat Enterprise Linux / Centos
 The following command (run with root permissions) will install the "Develop Tools" group of packages on RHEL / Centos:

 ```bash
 yum groupinstall 'Development Tools'
 ```
