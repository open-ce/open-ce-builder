"""
# *****************************************************************
# (C) Copyright IBM Corp. 2020, 2021. All Rights Reserved.
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

import sys
import logging
from enum import Enum, unique

log = logging.getLogger("OPEN-CE")
log.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(name)s-%(levelname)s]%(message)s')
log_out_handler = logging.StreamHandler(sys.stdout)
log_out_handler.setLevel(logging.DEBUG)
log_out_handler.addFilter(lambda record: record.levelno < logging.WARNING)
log_out_handler.setFormatter(formatter)
log_warn_handler = logging.StreamHandler(sys.stderr)
log_warn_handler.setLevel(logging.WARNING)
log_warn_handler.addFilter(lambda record: record.levelno < logging.ERROR)
log_warn_handler.setFormatter(formatter)
log_err_handler = logging.StreamHandler(sys.stderr)
log_err_handler.setLevel(logging.ERROR)
log.addHandler(log_out_handler)
log.addHandler(log_warn_handler)
log.addHandler(log_err_handler)


@unique
class Error(Enum):
    '''Enum for Error Messages'''
    ERROR = (0, "Unexpected Error: {}")
    CREATE_CONTAINER = (1, "Error creating container: \"{}\"")
    COPY_DIR_TO_CONTAINER = (2, "Error copying \"{}\" directory into container: \"{}\"")
    START_CONTAINER = (3, "Error starting container: \"{}\"")
    BUILD_IN_CONTAINER = (4, "Error executing build in container: \"{}\"")
    BUILD_IMAGE = (5, "Failure building image: \"{}\"")
    VALIDATE_ENV = (6, "Error validating \"{}\" for variant {}\n{}")
    VALIDATE_CONFIG = (7, "Error validating \"{}\" for \"{}\":\n{}")
    CONFIG_CONTENT = (8, "Content Error!:\n"
                         "An environment file needs to specify packages or "
                         "import another environment file.")
    CLONE_REPO = (9, "Unable to clone repository: {}")
    CREATE_BUILD_TREE = (10, "Error creating Build Tree\n{}")
    BUILD_RECIPE = (11, "Unable to build recipe: {}\n{}")
    CONFIG_FILE = (12, "Unable to open provided config file: {}")
    LOCAL_SRC_DIR = (13, "local_src_dir path \"{}\" specified doesn't exist")
    BUILD_TREE_CYCLE = (14, "Build dependencies should form a Directed Acyclic Graph.\n"
                            "The following dependency cycles were detected in the build tree:\n{}")
    INCORRECT_INPUT_PATHS = (15, "Input paths specified don't exist")
    LOCAL_CHANNEL_NOT_IN_CONTEXT = (16, "Specified local conda channel directory is not" +
              " in the current build context. \n Either move the local conda channel" +
              " directory in the current directory or run the script from the path" +
              " which contains local conda channel directory.")
    VALIDATE_BUILD_TREE = (17, "Dependencies are not compatible.\nCommand:\n{}\nOutput:\n{}\nError:\n{}")
    INCOMPAT_CUDA = (18, "Driver level \"{}\" is not new enough to support cuda \"{}\"")
    UNSUPPORTED_CUDA = (19, "Cannot build using container image for cuda \"{}\" no Dockerfile currently exists")
    TOO_MANY_CUDA = (20, "Only one cuda version allowed to be built with container build at a time")
    FAILED_TESTS = (21, "There were {} test failures. The following tests failed: {}")
    CONDA_ENV_FILE_REQUIRED = (22, "The '--conda_env_file' argument is required.")
    PATCH_APPLICATION = (23, "Failed to apply patch {} on feedstock {}")
    GET_LICENSES = (24, "Error generating licenses file.\nCommand:\n{}\nOUTPUT:\n{}Error:\n{}")
    FILE_DOWNLOAD = (25, "Failed to download {} with error:\n{}")
    CONDA_BUILD_CONFIG_FILE_NOT_FOUND = (26, "Failed to locate conda_build_config file: {}.")
    NO_CONTAINER_TOOL_FOUND = (27, "No container tool found on the system.")
    CONDA_PACKAGE_INFO = (28, "Conda Package Info Failed.\nCommand:\n{}\nOutput:\n{}")
    REMOTE_PACKAGE_DEPENDENCIES = (29, "Failure getting remote dependencies for the following packages:\n{}\nError:\n{}")
    WARNING = (30, "Unexpected Warning: {}")
    SCHEMA_VERSION_NOT_FOUND = (31, "'{}' does not provide '{}'. Possible schema mismatch.")
    CONTAINER_VERSION = (32, "Could not retrieve version of {} container tool.")
    CONDA_BUILD_CONFIG_NOT_FOUND = (33, "No valid '{}' file was found. Some recipes may fail to build.")
    CONDA_IO_ERROR = (34, "IO error occurred while reading version information from conda environment file '{}'.")
    SCHEMA_VERSION_MISMATCH = (35, "Open-CE Env file '{}' expects to be built with Open-CE Builder [{}]. " +
                                    "But this version is '{}'.")
    PACKAGE_NOT_FOUND = (36, "Cannot find `{}`, please see https://github.com/open-ce/open-ce-builder#requirements" +
                             " for a list of requirements.")
    TEMP_BUILD_IMAGE_FILES = (37, "Error removing temporary files created during build image.")
    UNABLE_DOWNLOAD_SOURCE = (38, "Unable to download source for '{}'.")
    UNABLE_CLONE_SOURCE = (39, "Unable to clone source for '{}'.")
    GCC_COMPILER_NOT_FOUND = (40, "Please check if GCC is installed. If not, install" +
                                       " gcc-toolset-12. Also, set environment variables" +
                                       " GCC_HOME to point to the installed location." +
                                       " For e.g. GCC_HOME=\"/opt/rh/gcc-toolset-12/root/usr\"")

    GIT_TAG_MISSING = (41, "git_tag attribute is missing for '{}'")
    FIPS_PACKAGES_NOT_BUILT = (42, "FIPS Compliant OpenSSL env failed to build")
    FFMPEG_PACKAGE_NOT_BUILT = (43, "ffmpeg env failed to build")

class OpenCEError(Exception):
    """
    Exception class for errors that occur in an Open-CE tool.
    """
    def __init__(self, error, *additional_args, **kwargs):
        # When pickling, error can already be a string.
        if isinstance(error, str):
            msg = error
        else:
            msg = f"[OPEN-CE-ERROR]-{error.value[0]} {error.value[1].format(*additional_args)}"
        super().__init__(msg, **kwargs)
        self.msg = msg

def show_warning(warning, *additional_args, **kwargs):
    """
    Prints an Open-CE Warning.
    """
    msg = f"-{warning.value[0]} {warning.value[1].format(*additional_args)}"
    log.warning(msg, **kwargs)
