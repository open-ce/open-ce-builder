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

import os
import pathlib
import pytest

import helpers
from importlib.util import spec_from_loader, module_from_spec
from importlib.machinery import SourceFileLoader

test_dir = pathlib.Path(__file__).parent.absolute()

spec = spec_from_loader("open_ce", SourceFileLoader("open_ce", os.path.join(test_dir, '..', 'open_ce', 'open-ce-builder')))
opence = module_from_spec(spec)
spec.loader.exec_module(opence)

import open_ce.validate_config as validate_config
from open_ce.errors import OpenCEError
import open_ce.utils as utils

def conda_search_result():
    output = '''
Loading channels: done
some_package 0.3.10 0
-----------------
file name   : some_package-0.3.10-0.conda
name        : some_package
version     : 0.3.10
build       : 0
build number: 0
size        : 20 KB
license     : BSD
subdir      : linux-ppc64le
url         : https://repo.anaconda.com/pkgs/main/linux-ppc64le/
md5         : 4691146ff587f371f83f0e7bab93b63b
dependencies: 

some_package 0.3.10 0
-----------------
file name   : some_package-0.3.10-1.conda
name        : some_package
version     : 0.3.10
build       : 0
build number: 0
size        : 20 KB
license     : BSD
subdir      : linux-ppc64le
url         : https://repo.anaconda.com/pkgs/main/linux-ppc64le/
md5         : 4691146ff587f371f83f0e7bab93b63b
timestamp   : 2020-07-08 07:05:32 UTC
dependencies: 

some_package 0.3.13 h6ffa863_0
--------------------------
file name   : some_package-0.3.13-h6ffa863_0.conda
name        : some_package
version     : 0.3.13
build       : h6ffa863_0
build number: 0
size        : 21 KB
license     : BSD
subdir      : linux-ppc64le
url         : https://repo.anaconda.com/pkgs/main/linux-ppc64le/
md5         : 37995ea3f8a1432752243716118cf9e1
timestamp   : 2021-03-22 19:19:31 UTC
dependencies: 



'''
    return output, "", 0

def test_validate_config(mocker):
    '''
    This is a complete test of `validate_config`.
    '''
    dirTracker = helpers.DirTracker()
    mocker.patch(
        'os.mkdir',
        return_value=0 #Don't worry about making directories.
    )
    mocker.patch(
        'os.system',
        return_value=0
    )
    mocker.patch(
        'open_ce.utils.run_command_capture',
        side_effect=(lambda x: helpers.validate_cli(x, expect=["conda create --dry-run",
                                                               "upstreamdep1 2.3.*",
                                                               "upstreamdep2 2.*"],
                                                       reject=["package"], #No packages from the env files should show up in the create command.
                                                       retval=[True, "", ""]))
    )
    mocker.patch(
        'conda.cli.python_api.run_command',
        side_effect=(lambda command, *arguments, **kwargs: conda_search_result())
    )
    mocker.patch(
        'os.getcwd',
        side_effect=dirTracker.mocked_getcwd
    )
    mocker.patch(
        'os.chdir',
        side_effect=dirTracker.validate_chdir
    )
    package_deps = {"package11": ["package15"],
                    "package12": ["package11"],
                    "package13": ["package12", "package14"],
                    "package14": ["package15", "package16"],
                    "package15": [],
                    "package16": ["package15"],
                    "package21": ["package13"],
                    "package22": ["package21", "__virtual_pack"]}
    mocker.patch(
        'conda_build.api.render',
        side_effect=(lambda path, *args, **kwargs: helpers.mock_renderer(os.getcwd(), package_deps))
    )
    mocker.patch(
        'conda_build.api.get_output_file_paths',
        side_effect=(lambda meta, *args, **kwargs: helpers.mock_get_output_file_paths(meta))
    )

    env_file = os.path.join(test_dir, 'test-env2.yaml')
    opence._main(["validate", validate_config.COMMAND, "--conda_build_configs", "./tests/conda_build_config.yaml", env_file, "--python_versions", utils.DEFAULT_PYTHON_VERS, "--build_types", "cuda"])

def test_validate_negative(mocker):
    '''
    This is a negative test of `validate_config` where the dry-run fails.
    '''
    dirTracker = helpers.DirTracker()
    mocker.patch(
        'os.mkdir',
        return_value=0 #Don't worry about making directories.
    )
    mocker.patch(
        'os.system',
        return_value=0
    )
    mocker.patch(
        'open_ce.utils.run_command_capture',
        side_effect=(lambda x: helpers.validate_cli(x, expect=["conda create --dry-run",
                                                               "upstreamdep1 2.3.*", #Checks that the value from the default config file is used.
                                                               "external_dep1", # Checks that the external dependencies were used.
                                                               "external_dep2 5.2.*", # Checks that the external dependencies were used.
                                                               "external_dep3=5.6.*"], # Checks that the external dependencies were used.
                                                       reject=["package"],
                                                       retval=[False, "", ""]))
    )
    mocker.patch(
        'conda.cli.python_api.run_command',
        side_effect=(lambda command, *arguments, **kwargs: conda_search_result())
    )
    mocker.patch(
        'os.getcwd',
        side_effect=dirTracker.mocked_getcwd
    )
    mocker.patch(
        'os.chdir',
        side_effect=dirTracker.validate_chdir
    )
    package_deps = {"package11": ["package15"],
                    "package12": ["package11"],
                    "package13": ["package12", "package14"],
                    "package14": ["package15", "package16"],
                    "package15": [],
                    "package16": ["package15"],
                    "package21": ["package13"],
                    "package22": ["package21"]}
    mocker.patch(
        'conda_build.api.render',
        side_effect=(lambda path, *args, **kwargs: helpers.mock_renderer(os.getcwd(), package_deps))
    )
    mocker.patch(
        'conda_build.api.get_output_file_paths',
        side_effect=(lambda meta, *args, **kwargs: helpers.mock_get_output_file_paths(meta))
    )

    env_file = os.path.join(test_dir, 'test-env2.yaml')
    with pytest.raises(OpenCEError) as err:
        opence._main(["validate", validate_config.COMMAND, "--conda_build_configs", "./tests/conda_build_config.yaml", env_file, "--python_versions", utils.DEFAULT_PYTHON_VERS, "--build_types", "cuda"])
    assert "Error validating \"" in str(err.value)
    assert "conda_build_config.yaml\']\" for " in str(err.value)
    assert "Dependencies are not compatible.\nCommand:\nconda create" in str(err.value)

def test_validate_bad_env(mocker):
    '''
    This is a negative test of `validate_config` where the env file is bad.
    '''
    dirTracker = helpers.DirTracker()
    mocker.patch(
        'os.mkdir',
        return_value=0 #Don't worry about making directories.
    )
    mocker.patch(
        'os.system',
        return_value=0
    )
    mocker.patch(
        'os.getcwd',
        side_effect=dirTracker.mocked_getcwd
    )
    mocker.patch(
        'os.chdir',
        side_effect=dirTracker.validate_chdir
    )
    package_deps = {"package11": ["package15"],
                    "package12": ["package11"],
                    "package13": ["package12", "package14"],
                    "package14": ["package15", "package16"],
                    "package15": [],
                    "package16": ["package15"],
                    "package21": ["package13"],
                    "package22": ["package21"]}
    mocker.patch(
        'conda_build.api.render',
        side_effect=(lambda path, *args, **kwargs: helpers.mock_renderer(os.getcwd(), package_deps))
    )
    env_file = os.path.join(test_dir, 'test-env-invalid1.yaml')
    with pytest.raises(OpenCEError) as err:
        opence._main(["validate", validate_config.COMMAND, "--conda_build_configs", "./tests/conda_build_config.yaml", env_file, "--python_versions", utils.DEFAULT_PYTHON_VERS, "--build_types", "cuda"])
    assert "Error validating \"" in str(err.value)
    assert "conda_build_config.yaml\']\" for " in str(err.value)
    assert "Unexpected key chnnels was found in " in str(err.value)
