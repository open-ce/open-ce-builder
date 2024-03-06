
# *****************************************************************
# (C) Copyright IBM Corp. 2021, 2022. All Rights Reserved.
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
from importlib.util import spec_from_loader, module_from_spec
from importlib.machinery import SourceFileLoader

test_dir = pathlib.Path(__file__).parent.absolute()

spec = spec_from_loader("opence", SourceFileLoader("opence", os.path.join(test_dir, '..', 'open_ce', 'open-ce')))
opence = module_from_spec(spec)
spec.loader.exec_module(opence)

from open_ce.inputs import make_parser, _create_env_config_paths, Argument, _check_ppc_arch, parse_args
from open_ce.errors import OpenCEError, Error

def test_create_env_config_paths(mocker):
    '''
    Test the _create_env_config_paths function.
    '''
    mocker.patch('os.path.exists', return_value=0)
    envs_repo = "open-ce"

    parser = make_parser([Argument.ENV_FILE, Argument.GIT_LOCATION, Argument.GIT_TAG_FOR_ENV])

    args = parser.parse_args(["test-env.yaml"])
    _create_env_config_paths(args)
    assert args.env_config_file[0] == "https://raw.githubusercontent.com/open-ce/" + envs_repo + "/main/envs/test-env.yaml"

    args = parser.parse_args(["test-env"])
    _create_env_config_paths(args)
    assert args.env_config_file[0] == "https://raw.githubusercontent.com/open-ce/" + envs_repo + "/main/envs/test-env.yaml"

    args = parser.parse_args(["test-env", "--git_tag_for_env", "my_tag"])
    _create_env_config_paths(args)
    assert args.env_config_file[0] == "https://raw.githubusercontent.com/open-ce/" + envs_repo + "/my_tag/envs/test-env.yaml"

    args = parser.parse_args(["test-env", "--git_location", "https://github.com/my_org"])
    _create_env_config_paths(args)
    assert args.env_config_file[0] == "https://raw.githubusercontent.com/my_org/" + envs_repo + "/main/envs/test-env.yaml"

def test_check_ppc_arch_for_p9(mocker):
    '''
    Test if needed environment variables are set if ppc_arch is p9
    '''
    mocker.patch(
        'os.path.exists',
        return_value=True
    )
    if 'GCC_HOME' in os.environ:
        del os.environ["GCC_HOME"]

    parser = make_parser([Argument.ENV_FILE, Argument.PPC_ARCH])

    args = parser.parse_args(["test-env.yaml", "--ppc_arch=p9"])
    _check_ppc_arch(args)    
    assert "GCC_HOME" not in os.environ

def test_check_ppc_arch_for_p10(mocker):
    '''
    Test if needed environment variables are set if ppc_arch is p10
    '''
    mocker.patch(
        'os.path.exists',
        return_value=True
    )

    parser = make_parser([Argument.ENV_FILE, Argument.PPC_ARCH])

    args = parser.parse_args(["test-env.yaml", "--ppc_arch=p10"])
    _check_ppc_arch(args)
    assert "GCC_HOME" in os.environ
    del os.environ["GCC_HOME"]

def test_check_ppc_arch_for_p10_container_build(mocker):
    '''
    Test if needed environment variables are set if ppc_arch is p10 with container_build
    '''
    mocker.patch(
        'os.path.exists',
        return_value=True
    )

    parser = make_parser([Argument.ENV_FILE, Argument.PPC_ARCH, Argument.CONTAINER_BUILD])
    args_str = ["test-env.yaml", "--container_build", "--ppc_arch=p10"]
    parse_args(parser, args_str)
    assert "GCC_HOME" not in os.environ

def test_check_ppc_arch_for_p10_with_no_gcc_path(mocker):
    '''
    Test if GCC_HOME don't exist, an error is thrown
    '''
    mocker.patch(
        'os.path.exists',
        return_value=False
    )

    parser = make_parser([Argument.ENV_FILE, Argument.PPC_ARCH])

    args = parser.parse_args(["test-env.yaml", "--ppc_arch=p10"])

    with pytest.raises(OpenCEError) as exc:
        _check_ppc_arch(args)
    assert Error.GCC12_COMPILER_NOT_FOUND.value[1] in str(exc.value)

