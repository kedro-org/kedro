# Decorators

## Memory Profiler

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
