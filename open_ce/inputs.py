"""
# *****************************************************************
# (C) Copyright IBM Corp. 2020, 2022. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# *****************************************************************
"""

import os

import argparse
from enum import Enum, unique
from open_ce import utils
from open_ce.errors import OpenCEError, Error, show_warning, log
from open_ce import __version__ as open_ce_version

class OpenCEFormatter(argparse.ArgumentDefaultsHelpFormatter):
    """
    Default help text formatter class used within Open-CE.
    Allows the use of raw text argument descriptions by
    prepending 'R|' to the description text.
    """
    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        return super()._split_lines(text, width)

@unique
class Argument(Enum):
    '''Enum for Arguments'''
    CONDA_BUILD_CONFIG = (lambda parser: parser.add_argument(
                                        '--conda_build_configs',
                                        type=str,
                                        default=None,
                                        help="Comma delimited list of locations of "
                                             "conda_build_config.yaml files. Can "
                                             "be a valid URL."))

    OUTPUT_FOLDER = (lambda parser: parser.add_argument(
                                        '--output_folder',
                                        type=str,
                                        default=utils.DEFAULT_OUTPUT_FOLDER,
                                        help='Path where built conda packages will be saved.'))

    CHANNELS = (lambda parser: parser.add_argument(
                                        '--channels',
                                        dest='channels_list',
                                        action='append',
                                        type=str,
                                        default=list(),
                                        help='Conda channels to be used.'))

    ENV_FILE = (lambda parser: parser.add_argument(
                                        'env_config_file',
                                        nargs='+',
                                        type=str,
                                        help="""R|Path to the environment configuration YAML file. The configuration
file describes the package environment you wish to build.

A collection of files exist at https://github.com/open-ce/open-ce.

This argument can be a URL, in which case imported_envs and the conda_build_config
will be automatically discovered in the same remote directory. E.g.:
>$ open-ce build env https://raw.githubusercontent.com/open-ce/open-ce/main/envs/opence-env.yaml

If the provided file doesn't exist locally, a URL will be generated to pull down from
https://raw.githubusercontent.com/open-ce/open-ce/main/envs. If the --git_tag_for_env argument
is provided, it will pull down from the provided tag instead of main. E.g:
>$ open-ce build env opence-env

For complete documentation on Open-CE environment files see:
https://github.com/open-ce/open-ce/blob/main/doc/README.yaml.md"""))

    REPOSITORY_FOLDER = (lambda parser: parser.add_argument(
                                        '--repository_folder',
                                        type=str,
                                        default="",
                                        help="Directory that contains the repositories. If the "
                                             "repositories don't exist locally, they will be "
                                             "downloaded from OpenCE's git repository. If no value is provided, "
                                             "repositories will be downloaded to the current working directory."))

    PYTHON_VERSIONS = (lambda parser: parser.add_argument(
                                        '--python_versions',
                                        type=str,
                                        default=utils.DEFAULT_PYTHON_VERS,
                                        help='Comma delimited list of python versions to build for '
                                             ', such as "3.8" or "3.9".'))

    BUILD_TYPES = (lambda parser: parser.add_argument(
                                        '--build_types',
                                        type=str,
                                        default=utils.DEFAULT_BUILD_TYPES,
                                        help='Comma delimited list of build types, such as "cpu" or "cuda".'))

    MPI_TYPES = (lambda parser: parser.add_argument(
                                        '--mpi_types',
                                        type=str,
                                        default=utils.DEFAULT_MPI_TYPES,
                                        help='Comma delimited list of mpi types, such as "openmpi" or "system".'))

    CUDA_VERSIONS = (lambda parser: parser.add_argument(
                                        '--cuda_versions',
                                        type=str,
                                        default=utils.DEFAULT_CUDA_VERS,
                                        help='CUDA version to build for '
                                             ', such as "11.2".'))

    CONTAINER_BUILD = (lambda parser: parser.add_argument(
                                        '--container_build',
                                        '--docker_build',
                                        action='store_true',
                                        help="Perform a build within a container. "
                                             "NOTE: When the --container_build flag is used, all arguments with paths "
                                             "should be relative to the directory containing root level open-ce "
                                             "directory. Only files within the root level open-ce directory and "
                                             "local_files will be visible at build time."))

    DEBUG = (lambda parser: parser.add_argument(
                                        '--debug',
                                        action='store_true',
                                        help="Creates debug environment and provides a single command line that "
                                             "one can copy/paste to enter that environment."))

    SKIP_BUILD_PACKAGES = (lambda parser: parser.add_argument(
                                        '--skip_build_packages',
                                        action='store_true',
                                        help="Do not perform builds of packages."))

    RUN_TESTS = (lambda parser: parser.add_argument(
                                        '--run_tests',
                                        action='store_true',
                                        help="Run Open-CE tests for each potential conda environment"))

    CONDA_ENV_FILE = (lambda parser: parser.add_argument(
                                        '--conda_env_files',
                                        type=str,
                                        help='Comma delimited list of paths to conda environment files.' ))
    PPC_ARCH = (lambda parser: parser.add_argument(
                                        '--ppc_arch',
                                        type=str,
                                        default=utils.DEFAULT_PPC_ARCH,
                                        help="""R|Power Architecture to build for. Values: p9 or p10.
p9: Libraries can be used on Power8, Power9 and Power 10,
    but do not use MMA acceleration.
p10: Libraries can be used on Power9 and Power10, and use
    MMA acceleration on Power10."""))


    LOCAL_CONDA_CHANNEL = (lambda parser: parser.add_argument(
                                        '--local_conda_channel',
                                        type=str,
                                        default=utils.DEFAULT_OUTPUT_FOLDER,
                                        help='Path where built conda packages are present.'))

    TEST_WORKING_DIRECTORY = (lambda parser: parser.add_argument(
                                        '--test_working_dir',
                                        type=str,
                                        default=utils.DEFAULT_TEST_WORKING_DIRECTORY,
                                        help="Directory where tests will be executed."))

    RECIPE_CONFIG_FILE = (lambda parser: parser.add_argument(
                                        '--recipe-config-file',
                                        type=str,
                                        default=None,
                                        help="""R|Path to the recipe configuration YAML file. The configuration
file lists paths to recipes to be built within a feedstock.

Below is an example stating that there are two recipes to build,
one named my_project and one named my_variant.

recipes:
  - name : my_project
    path : recipe

  - name : my_variant
    path: variants

If no path is given, the default value is build-config.yaml.
If build-config.yaml does not exist, and no value is provided,
it will be assumed there is a single recipe with the
path of \"recipe\"."""))

    RECIPES = (lambda parser: parser.add_argument(
                                        '--recipes',
                                        dest='recipe_list',
                                        action='store',
                                        default=None,
                                        help='Comma separated list of recipe names to build.'))

    WORKING_DIRECTORY = (lambda parser: parser.add_argument(
                                        '--working_directory',
                                        type=str,
                                        help='Directory to run the script in.'))

    LOCAL_SRC_DIR = (lambda parser: parser.add_argument(
                                        '--local_src_dir',
                                        type=str,
                                        required=False,
                                        help='Path where package source is downloaded in the form of RPM/Debians/Tar.'))

    GIT_LOCATION = (lambda parser: parser.add_argument(
                                        '--git_location',
                                        type=str,
                                        default=utils.DEFAULT_GIT_LOCATION,
                                        help='The default location to clone git repositories from.'))

    GIT_TAG_FOR_ENV = (lambda parser: parser.add_argument(
                                        '--git_tag_for_env',
                                        type=str,
                                        default=None,
                                        help='Git tag to be checked out for all of the packages in an environment.'))

    # Use the most recent commits from the branch that the provided tag is in.
    GIT_UP_TO_DATE = (lambda parser: parser.add_argument(
                                        '--git_up_to_date',
                                        action='store_true',
                                        help=argparse.SUPPRESS))

    DEBUG_OUTPUT_ID = (lambda parser:  parser.add_argument(
                                        '--debug_output_id',
                                         type=str,
                                         default=None,
                                         help="Output ID in case of multiple output recipe, "
                                              "for which debug envs and scripts should be created."))

    TEST_LABELS = (lambda parser: parser.add_argument(
                                        '--test_labels',
                                        type=str,
                                        default="",
                                        help="Comma delimited list of labels indicating what tests to run."))

    CONTAINER_BUILD_ARGS = (lambda parser: parser.add_argument(
                                        '--container_build_args',
                                        type=str,
                                        default="",
                                        help="Container build arguments like environment variables "
                                             " to be set in the container or cpus or gpus to be used "
                                             " such as \"--build-arg ENV1=test1 --cpuset-cpus 0,1\"."))

    PACKAGES = (lambda parser: parser.add_argument(
                               '--packages',
                               type=str,
                               default=None,
                               help="Only build this list of comma delimited packages (plus their dependencies)."))

    CONTAINER_TOOL = (lambda parser: parser.add_argument(
                                        '--container_tool',
                                        type=str,
                                        default=utils.DEFAULT_CONTAINER_TOOL,
                                        help="Container tool to be used. Default is taken from the "
                                             " system, podman has preference over docker. "))

    TEMPLATE_FILES = (lambda parser: parser.add_argument(
                                     '--template_files',
                                     type=str,
                                     default=None,
                                     help="Comma delimited list of template files to initialize with Open-CE "
                                          " information."))

    LICENSES_FILE = (lambda parser: parser.add_argument(
                                    '--licenses_file',
                                    type=str,
                                    default=None,
                                    help="Path to a licenses.csv file. This file will be used as the input to the template "
                                         " provided in the --template_files argument. The format should be tab delimeted "
                                         " and match the format of the licenses.csv file outputed by the licenses tool. "
                                         " When this argument is provided, the licenses tool won't search packages for "
                                         " license information. It will only use what is in the csv file."))

    VERSION = (lambda parser: parser.add_argument(
                                     '-v',
                                     '--version',
                                     action='version',
                                     version="Open-CE Builder {}".format(open_ce_version)))

    CONDA_PKG_FORMAT = (lambda parser: parser.add_argument(
                                        '--conda_pkg_format',
                                        type=str,
                                        default=utils.DEFAULT_PKG_FORMAT,
                                        help='Conda package format to be used, such as "tarball" or "conda".'))
    WIDTH = (lambda parser: parser.add_argument(
                                     '--width',
                                     type=int,
                                     default=50,
                                     help="Width of output graph."))

    HEIGHT = (lambda parser: parser.add_argument(
                                     '--height',
                                     type=int,
                                     default=50,
                                     help="Height of output graph."))

VARIANT_ARGS = [Argument.PYTHON_VERSIONS,
                Argument.BUILD_TYPES,
                Argument.MPI_TYPES,
                Argument.CUDA_VERSIONS]

GIT_ARGS = [Argument.REPOSITORY_FOLDER,
            Argument.GIT_LOCATION,
            Argument.GIT_TAG_FOR_ENV,
            Argument.GIT_UP_TO_DATE]

PRIMARY_BUILD_ARGS = [Argument.CONDA_BUILD_CONFIG,
                      Argument.OUTPUT_FOLDER,
                      Argument.CHANNELS] + \
                     VARIANT_ARGS

ENV_BUILD_ARGS = PRIMARY_BUILD_ARGS + \
                 GIT_ARGS + \
                 [Argument.ENV_FILE,
                  Argument.PACKAGES]

def make_parser(arguments, *args, formatter_class=OpenCEFormatter, **kwargs):
    '''
    Make a parser from a list of OPEN-CE Arguments.
    '''
    parser = argparse.ArgumentParser(*args, formatter_class=formatter_class, **kwargs)
    for argument in arguments:
        argument(parser)
    return parser

def add_subparser(subparsers, command, arguments, *args, formatter_class=OpenCEFormatter, **kwargs):
    '''
    Make a parser from a list of OPEN-CE Arguments.
    '''
    subparser = subparsers.add_parser(command, *args, formatter_class=formatter_class, **kwargs)
    for argument in arguments:
        argument(subparser)
    return subparser

def _create_env_config_paths(args):
    '''
    If the provided env_config_file's don't exist locally, convert the paths to
    URLs pointing to the GitHub repository for environemnt files.
    '''
    if "env_config_file" in vars(args).keys():
        if not "provided_env_files" in vars(args).keys():
            args.__dict__["provided_env_files"] = []

        for index, config_file in enumerate(args.env_config_file):
            args.provided_env_files.append(config_file)
            if not os.path.exists(config_file) and not utils.is_url(config_file):
                # Determine the organization name from the git_location argument
                organization = os.path.basename(args.git_location)

                # Grab the branch name from the git_tag_for_env argument
                if "git_tag_for_env" in vars(args).keys() and args.git_tag_for_env:
                    branch = args.git_tag_for_env
                else:
                    branch = "main"

                # Determine the file name
                file_name, extension = os.path.splitext(config_file)
                if not extension:
                    file_name = file_name + ".yaml"
                else:
                    file_name = file_name + extension

                new_url = "https://raw.githubusercontent.com/{}/{}/{}/envs/{}".format(
                                                  organization, utils.DEFAULT_ENVS_REPO, branch, file_name)

                log.info("Unable to find '%s' locally. Attempting to use '%s'.", config_file, new_url)
                args.env_config_file[index] = new_url

def _check_ppc_arch(args):
    '''
    This will check if ppc_arch is p10 and set the corresponding
    needed environment variable GCC_11_HOME
    '''
    if "ppc_arch" in vars(args).keys() and args.ppc_arch:
        if args.ppc_arch == "p10":
            if "GCC_11_HOME" not in os.environ:
                os.environ["GCC_11_HOME"] = utils.DEFAULT_GCC_11_HOME_DIR
            if os.path.exists(utils.DEFAULT_GCC_11_HOME_DIR):
                PATH = os.environ["PATH"]
                os.environ["PATH"] = "{0}:{1}".format(os.path.join(os.environ["GCC_11_HOME"], "bin"), PATH)
                print("Path variable set to : ", os.environ["PATH"])
            else:
                raise OpenCEError(Error.GCC11_COMPILER_NOT_FOUND)

def parse_args(parser, arg_strings=None):
    '''
    Parses input arguments and handles more complex defaults.
    - conda_build_configs: If not passed in the default is with the env file,
                          if is passed in, otherwise it is  expected to be in
                          the local path.
    '''
    args = parser.parse_args(arg_strings)
    _create_env_config_paths(args)

    if "container_build" not in vars(args).keys() or not args.container_build:
        _check_ppc_arch(args)

    if "conda_build_configs" in vars(args).keys():
        if args.conda_build_configs is None:
            if "env_config_file" in vars(args).keys() and args.env_config_file:
                args.conda_build_configs = os.path.join(os.path.dirname(args.env_config_file[0]),
                                                       utils.CONDA_BUILD_CONFIG_FILE)
            else:
                args.conda_build_configs = utils.DEFAULT_CONDA_BUILD_CONFIG

        configs = utils.get_conda_build_configs(parse_arg_list(args.conda_build_configs))
        args.conda_build_configs = configs

        if not configs:
            show_warning(Error.CONDA_BUILD_CONFIG_NOT_FOUND, utils.CONDA_BUILD_CONFIG_FILE)

    return args

def parse_arg_list(arg_list):
    ''' Turn a comma delimited string into a python list'''
    if isinstance(arg_list, list):
        return arg_list
    return arg_list.split(",") if not arg_list is None else list()
