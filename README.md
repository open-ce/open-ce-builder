[![Open-CE Stars](https://img.shields.io/github/stars/open-ce?style=social)](https://github.com/open-ce/open-ce/stargazers)

<p align="center">
  <img src="https://avatars0.githubusercontent.com/u/68873540?s=400&u=a02dc4156e50cdffb23172aba7133e44381885d4&v=4" alt="Open-CE Logo" width="30%">
</p>

[![Installation Options](https://img.shields.io/badge/Install%20with-conda%20%7C%20pip-brightgreen)](#installing-the-open-ce-build-tools)
[![Python Support](https://img.shields.io/badge/python-3.8%20%7C%203.9-blue.svg)](#requirements)
[![Cuda Support](https://img.shields.io/badge/cuda-11.2%20%7C%2011.4-blue)](doc/README.cuda_support.md)

[![Builder Unit Tests](https://github.com/open-ce/open-ce/workflows/Open-CE%20Builder%20Unit%20Tests/badge.svg)](https://github.com/open-ce/open-ce-builder/actions?query=workflow%3A%22Open-CE+Builder+Unit+Tests%22+branch%3Amain)
[![Builder Unit Test Coverage](https://codecov.io/gh/open-ce/open-ce-builder/branch/main/graph/badge.svg)](https://codecov.io/gh/open-ce/open-ce-builder)
[![GitHub Licence](https://img.shields.io/github/license/open-ce/open-ce.svg)](LICENSE)
[![Open in Visual Studio Code](https://open.vscode.dev/badges/open-in-vscode.svg)](https://open.vscode.dev/open-ce/open-ce-builder)
---

# Open-CE Builder

This repository contains the tools needed to build the [Open-CE](https://github.com/open-ce/open-ce) project.

The `open-ce` tool allows a user to build collections of conda recipes described within a collection of feedstocks. It also provides tools for validating potential conda environments and running tests for feedstocks.

## GETTING STARTED

### Requirements

* `conda` == 4.12
  * The conda tool can either be installed through [Anaconda](https://www.anaconda.com/products/individual#Downloads) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html).
* `conda-build` == 3.21.7
  * Once `conda` is installed, `conda-build` can be installed with the command: `conda install conda-build`
* `networkx` >= 2.5
* `python` >= 3.8
* `junit-xml` >= 1.9
* `docker` >= 1.13 or `podman` >= 2.0.5
  * docker or podman required only when building within a container (see below).
* `matplotlib` >= 3.3
  * Required only when exporting the dependency graph.

### CUDA Requirements

Currently CUDA 11.2 and 11.4 is supported by the recipes in Open-CE. Please see [`doc/README.cuda_support.md`](doc/README.cuda_support.md) for details on setting
up a proper build enviornment for CUDA support.

Open-CE expects the `CUDA_HOME` environment variable to be set to the location of the CUDA installation. Note that not all recipes work when `CUDA_HOME` references a non-standard CUDA installation location. Reference the [cuda README](doc/README.cuda_support.md) for more information.

When building packages that use CUDA, a tar package of TensorRT for the intended CUDA version will need to be [downloaded](https://developer.nvidia.com/nvidia-tensorrt-7x-download) ahead of time. The downloaded file should be placed in a new local directory called `local_files`. The [cuda README](doc/README.cuda_support.md) has more information.

### Installing the Open-CE Build Tools

To get the Open-CE build tools, one can either install them via `conda` from the [Open-CE channel](https://conda.anaconda.org/open-ce), install them via `pip` from [github](https://github.com/open-ce/open-ce-builder) or clone the source code from [github](https://github.com/open-ce/open-ce-builder) as below - 

```bash
# Conda install from the open-ce channel
conda install -c open-ce open-ce-builder
```
OR
```bash
# Pip install from the main branch
pip install git+https://github.com/open-ce/open-ce-builder.git@main
```
OR
```bash
# Clone Open-CE from GitHub
git clone https://github.com/open-ce/open-ce-builder.git
cd open-ce-builder
pip install -e .
```

#### Open-CE compatibility with Open-CE Builder
| Open-CE version         | Open-CE Builder version |
|-------------------------|-------------------------|
| All releases upto 1.5.2 | <=9.0.0                 |
| >= 1.5.3                | 9.0.0                   |
| 1.6.0                   | 10.0.0                  |
| 1.6.1                   | 10.0.2                  |
| 1.7.0                   | TODO


### Building a Collection of Packages
To build an entire integrated and functional conda channel using Open-CE, start by installing the needed tools in the [Requirements](#requirements) section above.
The `open-ce build env` command can then be used to build a collection of Open-CE packages. An Open-CE environment file needs to be passed in as input. A selection of environment files are provided within the [`open-ce` repo](https://github.com/open-ce/open-ce) for different frameworks such as TensorFlow and PyTorch. The output from running `open-ce build env` will be a local conda channel (by default called `condabuild`) and one or more conda environment file(s) in the output folder depending on the selected build configuration. For more details on `open-ce build env`, please see [`doc/README.open_ce_build.md`](doc/README.open_ce_build.md#open-ce-build-env-sub-command).

The following commands will use the `opence-env.yaml` Open-CE environment file to build all of the Open-CE packages for Python 3.8 (the default), including CUDA builds and cpu-only builds (also the default). The commands should be run from within the same directory that contains `local_files`.

```bash
# Clone Open-CE from GitHub
git clone https://github.com/open-ce/open-ce.git
# Build packages
open-ce build env ./open-ce/envs/opence-env.yaml
```

The `open-ce` tool will also automatically look for environment files within the open-ce repo's env [directory](https://github.com/open-ce/open-ce/tree/main/envs) if an environment file isn't found locally.

The following commands will build the `opence-env.yaml` environment file:

```bash
# Build packages
open-ce build env opence-env
```

A specific version of an environment file from the open-ce repo can be built using the `--git_tag` flag.

The following commands will build version 1.1.4 of the open-ce environment file provided within the open-ce [repo](https://github.com/open-ce/open-ce):

```bash
# Build packages
open-ce build env --git_tag open-ce-v1.1.4 opence-env
```

The following commands will use the `opence-env.yaml` Open-CE environment file from a specific Open-CE release to build all of the Open-CE packages for Python 3.8 and 3.9, including only CUDA builds. The commands should be run from within the same directory that contains `local_files`.

```bash
# Build packages
open-ce build env --python_versions 3.8,3.9 --build_types cuda opence-env
```

Note that having _conda-forge_ in your channel list may sometime cause conflicts or unexpected errors due to dependencies' versions mismatch. So, it is recommended to avoid mixing the channels during the build as well as at runtime.


### Power10 MMA Optimization
#### Building Packages

One can build the major Open-CE libraries like TensorFlow, Pytorch, Xgboost, etc. with Power10 MMA optimization.
For details, please see [`doc/README.open_ce_build.md`](doc/README.open_ce_build.md).

#### Running Packages

These packages will work on Power9 or Power10, but not on Power8.

### Building within a container

Passing the `--container_build` argument to the `open-ce build env` command will create a container image and perform the actual build inside of a container based on that image. This will provide a "clean" environment for the builds and make builds more system independent. It is recommended to build with this option as opposed to running on a bare metal machine. For more information on the `--container_build` option, please see [`doc/README.open_ce_build.md`](doc/README.open_ce_build.md#open-ce-build-env-sub-command).

### Building a Single Feedstock

The `open-ce build feedstock` command can be used to build a single feedstock (which could produce one or more conda packages). The output from running `open-ce build feedstock` will be a local conda channel (by default called `condabuild`). For more details on `open-ce build feedstock`, please see [`doc/README.open_ce_build.md`](doc/README.open_ce_build.md#open-ce-build-feedstock-sub-command).

The following commands will build all of the packages within a feedstock named `MY_FEEDSTOCK`.

```bash
# Clone Open-CE Environments from GitHub
git clone https://github.com/open-ce/open-ce.git
# Clone MY_FEEDSTOCK from GitHub
git clone https://github.com/open-ce/MY_FEEDSTOCK-feedstock.git
# Build packages
cd MY_FEEDSTOCK-feedstock
open-ce build feedstock --conda_build_config ../open-ce/envs/conda_build_config.yaml
```

### Installing Packages

After performing a build, a local conda channel will be created. By default, this will be within a folder called `condabuild` (it can be changed using the `--output_folder` argument). After the build, packages can be installed within a conda environment from this local channel. If the packages are built using `open-ce build env` script, then a conda environment file will also be generated which can be used to generate a conda environment with the built packages installed in it. See conda's [documentation](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html) for more information on conda environments.

The following command will install a package named `PACKAGE` from the local conda channel `condabuild` into the currently active conda environment.

```bash
conda install -c ./condabuild PACKAGE
```

The following command can be used to create a conda environment using a conda environment file.

```bash
conda env create -f <conda_environment_file>
```

### Testing Packages

After performing the build using the `open-ce build env` tool, the `open-ce test` tool can be used to either test a package or a collection of packages. For more details on `open-ce test`, please see [`doc/README.open_ce_test.md`](doc/README.open_ce_test.md).

### Creating Container Image with Open-CE Packages installed

After performing the build using `open-ce build env`, the `open-ce build image` command can be used to create a runtime container image containing the newly created conda channel, as well as a conda environment with the newly build Open-CE packages. For more details on `open-ce build image`, please see [`doc/README.open_ce_build.md`](doc/README.open_ce_build.md#open-ce-build-image-sub-command).


### Contributions

For contribution information, please see the [CONTRIBUTING.md](CONTRIBUTING.md) page.
