"""
# *****************************************************************
# (C) Copyright IBM Corp. 2022. All Rights Reserved.
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

DEFAULT_BUILD_TYPES = "cpu,cuda"
SUPPORTED_BUILD_TYPES = DEFAULT_BUILD_TYPES
DEFAULT_PYTHON_VERS = "3.10"
SUPPORTED_PYTHON_VERS = "3.8,3.9,3.10"
DEFAULT_MPI_TYPES = "openmpi"
SUPPORTED_MPI_TYPES = "system,openmpi"
DEFAULT_CUDA_VERS = "11.8"
SUPPORTED_CUDA_VERS = "11.2,11.8"
CONDA_BUILD_CONFIG_FILE = "conda_build_config.yaml"
DEFAULT_CONDA_BUILD_CONFIG = os.path.abspath(os.path.join(os.getcwd(), CONDA_BUILD_CONFIG_FILE))
DEFAULT_GIT_LOCATION = "https://github.com/open-ce"
DEFAULT_ENVS_REPO = "open-ce"
SUPPORTED_GIT_PROTOCOLS = ["https:", "http:", "git@"]
DEFAULT_RECIPE_CONFIG_FILE = "config/build-config.yaml"
CONDA_ENV_FILENAME_PREFIX = "opence-conda-env-"
DEFAULT_OUTPUT_FOLDER = "condabuild"
DEFAULT_TEST_CONFIG_FILE = "tests/open-ce-tests.yaml"
DEFAULT_GIT_TAG = None
OPEN_CE_VARIANT = "open-ce-variant"
DEFAULT_TEST_WORKING_DIRECTORY = "./"
KNOWN_VARIANT_PACKAGES = ["python", "cudatoolkit"]
DEFAULT_LICENSES_FILE = "licenses.csv"
TMP_LICENSE_DIR = "tmp_license_src"
OPEN_CE_INFO_FILE = "open-ce-info.yaml"
CONTAINER_TOOLS = ["podman", "docker"]
DEFAULT_CONTAINER_TOOL = next(filter(lambda tool: os.system(f"which {tool} &> /dev/null")
                                      == 0, CONTAINER_TOOLS), None)
DEFAULT_PKG_FORMAT = "conda"  # use .conda output format
NUM_THREAD_POOL = 16
OPEN_CE_VERSION_STRING = "Open-CE Version"
DEFAULT_GRAPH_FILE = "graph.png"
DEFAULT_TEST_RESULT_FILE = "test_results.xml"
DEFAULT_PPC_ARCH = "p9"
DEFAULT_GCC_11_HOME_DIR = "/opt/rh/gcc-toolset-11/root/usr"
OPENSSL_ENV_FILE = "openssl-env.yaml"
FFMPEG_ENV_FILE = "ffmpeg-env.yaml"
