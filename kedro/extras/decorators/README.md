# Decorators


## Retry

A function decorator which catches exceptions from the wrapped function at most `n_times`, after which it bundles and propagates them. By default, all exceptions are caught, but you can narrow your scope using the `exceptions` argument. You can also specify the time delay (in seconds) between a failure and the next retry, using the `delay_sec` parameter.


## Memory Profiler

A function decorator which profiles the memory used when executing the function. The logged memory is collected by taking memory snapshots every 100ms, and includes memory used by children processes. The implementation uses the `memory_profiler` Python package under the hood.
 >*Note*: This decorator will only work with functions taking at least 0.5s to execute, due to a bug in the `memory_profiler` package (see https://github.com/pythonprofilers/memory_profiler/issues/216).

### Build tools

 On Unix-like operating systems, you will need to install a C compiler and related build tools for your platform. This is due to the inclusion of the [memory-profiler](https://pypi.org/project/memory-profiler/) library in our dependencies. If your operating system is not mentioned, please refer to its documentation.

 #### macOS
 To install Command Line Tools for Xcode, run the following from the terminal:

 ```bash
 xcode-select --install
 ```

 #### GNU/Linux

 ##### Debian/Ubuntu

 The following command (run with root permissions) will install the `build-essential` metapackage for Debian-based distributions:

 ```bash
 apt-get update && apt-get install build-essential
 ```

 ##### Red Hat Enterprise Linux / Centos
 The following command (run with root permissions) will install the "Develop Tools" group of packages on RHEL/Centos:

 ```bash
 yum groupinstall 'Development Tools'
 ```
