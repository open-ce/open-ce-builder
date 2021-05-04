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
from importlib.util import spec_from_loader, module_from_spec
from importlib.machinery import SourceFileLoader

test_dir = pathlib.Path(__file__).parent.absolute()

spec = spec_from_loader("opence", SourceFileLoader("opence", os.path.join(test_dir, '..', 'open_ce', 'open-ce')))
opence = module_from_spec(spec)
spec.loader.exec_module(opence)

import open_ce.validate_env as validate_env
from open_ce.errors import OpenCEError

def test_validate_env(mocker, capsys):
    '''
    Positive test for validate_env.
    '''
    from sys import stderr
    # Apparently the `file` default was being set before capsys mocked sys.stderr. This mocks the default for the function.
    mocker.patch('open_ce.errors.show_warning.__kwdefaults__', {'file': stderr})
    env_file = os.path.join(test_dir, 'test-env2.yaml')
    opence._main(["validate", validate_env.COMMAND, env_file])
    captured = capsys.readouterr()
    assert "OPEN-CE-WARNING" in captured.err
    assert "test-env2.yaml' does not provide 'builder_version'. Possible schema mismatch." in captured.err
    assert "test-env1.yaml' does not provide 'builder_version'. Possible schema mismatch." in captured.err

def test_validate_env_negative():
    '''
    Negative test for validate_env.
    '''
    env_file = os.path.join(test_dir, 'test-env-invalid1.yaml')
    with pytest.raises(OpenCEError) as exc:
        opence._main(["validate", validate_env.COMMAND, env_file])
    assert "Unexpected key chnnels was found in " in str(exc.value)

def test_validate_env_wrong_external_deps(mocker,):
    '''
    Test that validate env correctly handles invalid data for external dependencies.
    '''
    unused_env_for_arg = os.path.join(test_dir, 'test-env-invalid1.yaml')
    env_file = { 'packages' : [{ 'feedstock' : 'test1' }], 'external_dependencies' : 'ext_dep' }
    mocker.patch('conda_build.metadata.MetaData.get_rendered_recipe_text', return_value=env_file)

    with pytest.raises(OpenCEError) as exc:
        opence._main(["validate", validate_env.COMMAND, unused_env_for_arg])
    assert "ext_dep is not of expected type <class 'list'>" in str(exc.value)

def test_validate_env_dict_for_external_deps(mocker,):
    '''
    Test that validate env correctly handles erroneously passing a dict for external dependencies.
    '''
    unused_env_for_arg = os.path.join(test_dir, 'test-env-invalid1.yaml')
    env_file = { 'packages' : [{ 'feedstock' : 'test1' }], 'external_dependencies' : [{ 'feedstock' : 'ext_dep'}] }
    mocker.patch('conda_build.metadata.MetaData.get_rendered_recipe_text', return_value=env_file)

    with pytest.raises(OpenCEError) as exc:
        opence._main(["validate", validate_env.COMMAND, unused_env_for_arg])
    assert "{'feedstock': 'ext_dep'} is not of expected type <class 'str'>" in str(exc.value)

def test_validate_env_schema_mismatch(mocker):
    '''
    Positive test for validate_env.
    '''
    mocker.patch('open_ce.conda_utils.version_matches_spec.__defaults__', ("0.1.0",))
    env_file = os.path.join(test_dir, 'test-env3.yaml')
    with pytest.raises(OpenCEError) as exc:
        opence._main(["validate", validate_env.COMMAND, env_file])
    assert "test-env3.yaml' expects to be built with Open-CE Builder [>=1]. But this version is " in str(exc.value)
