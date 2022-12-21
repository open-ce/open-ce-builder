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
import shutil
import xml.etree.ElementTree as ET

from importlib.util import spec_from_loader, module_from_spec
from importlib.machinery import SourceFileLoader

test_dir = pathlib.Path(__file__).parent.absolute()

spec = spec_from_loader("opence", SourceFileLoader("opence", os.path.join(test_dir, '..', 'open_ce', 'open-ce')))
opence = module_from_spec(spec)
spec.loader.exec_module(opence)

import open_ce.test_feedstock as test_feedstock
import open_ce.constants as constants
from open_ce.errors import OpenCEError

orig_load_test_file = test_feedstock.load_test_file
def mock_load_test_file(x, y):
    return orig_load_test_file(x, y)

def validate_junit(required_test_results,
                   excluded_test_results,
                   expected_test_cases,
                   junit_file=os.path.join("./", constants.DEFAULT_TEST_RESULT_FILE),
                   expected_failures=None):
    '''
    Used to validate the contents of a junit file.
    '''
    if expected_failures is None:
        expected_failures = ["0"]
    test_results = ET.parse(junit_file)
    testsuites = list(test_results.getroot())
    assert len(testsuites) == len(expected_failures)
    for i, testsuite in enumerate(testsuites):
        assert testsuite.attrib['failures'] == str(expected_failures[i])
        testcases = list(testsuite)
        print(testcases)
        assert len(testcases) == expected_test_cases[i]
        testcase_names = ";".join((testcase.attrib["name"] for testcase in testcases))
        for test_result in required_test_results[i]:
            if "name" in test_result:
                assert test_result["name"] in testcase_names
        for test_result in excluded_test_results:
            if "name" in test_result:
                assert test_result["name"] not in testcase_names

def test_test_feedstock_complete(mocker, caplog):
    '''
    This is a complete test of `test_feedstock`.
    '''

    mocker.patch('open_ce.test_feedstock.load_test_file', side_effect=(lambda x, y: mock_load_test_file(os.path.join(test_dir, "open-ce-tests1.yaml"), y)))

    opence._main(["test", test_feedstock.COMMAND, "--conda_env_file", "tests/test-conda-env2.yaml"])
    assert "Running: Create conda environment " + constants.CONDA_ENV_FILENAME_PREFIX in caplog.text
    assert "Running: Test 1" in caplog.text
    assert not "Running: Test 2" in caplog.text
    assert "Running: Remove conda environment " + constants.CONDA_ENV_FILENAME_PREFIX in caplog.text
    validate_junit([[{"name": "Create conda environment " + constants.CONDA_ENV_FILENAME_PREFIX},
                     {"name": "Test 1"},
                     {"name": "Remove conda environment " + constants.CONDA_ENV_FILENAME_PREFIX}]],
                   [[{"name": "Test 2"}]],
                   [3])

def test_test_feedstock_failed_tests(mocker, caplog):
    '''
    Test that failed tests work correctly.
    '''

    mocker.patch('open_ce.test_feedstock.load_test_file', side_effect=(lambda x, y: mock_load_test_file(os.path.join(test_dir, "open-ce-tests2.yaml"), y)))
    mocker.patch('open_ce.conda_env_file_generator.get_variant_string', return_value=None)

    with pytest.raises(OpenCEError) as exc:
        opence._main(["test", test_feedstock.COMMAND, "--conda_env_file", "tests/test-conda-env2.yaml"])
    assert "There were 2 test failures" in str(exc.value)
    assert "Failed test: Test 1" in caplog.text
    assert "Failed test: Test 3" in caplog.text
    assert not "Failed test: Test 2" in caplog.text
    validate_junit([[{"name": "Create conda environment " + constants.CONDA_ENV_FILENAME_PREFIX},
                     {"name": "Test 1"},
                     {"name": "Test 2"},
                     {"name": "Test 3"},
                     {"name": "Remove conda environment " + constants.CONDA_ENV_FILENAME_PREFIX}]],
                   [[]],
                   [5],
                   expected_failures = [2])

def test_test_feedstock_working_dir(mocker, caplog):
    '''
    This tests that the working_dir arg works correctly.
    Also sets a different build_type variant than what is in `test_test_feedstock`.
    '''

    working_dir = "./my_working_dir"
    my_variants = {'build_type' : 'cpu'}
    mocker.patch('open_ce.test_feedstock.load_test_file', side_effect=(lambda x, y: mock_load_test_file(os.path.join(test_dir, "open-ce-tests1.yaml"), my_variants)))

    assert not os.path.exists(working_dir)
    opence._main(["test", test_feedstock.COMMAND, "--conda_env_file", "tests/test-conda-env2.yaml", "--test_working_dir", working_dir])
    assert os.path.exists(working_dir)
    shutil.rmtree(working_dir)
    assert "Running: Create conda environment " + constants.CONDA_ENV_FILENAME_PREFIX in caplog.text
    assert "Running: Test 1" in caplog.text
    assert "Running: Test 2" in caplog.text
    assert "Running: Remove conda environment " + constants.CONDA_ENV_FILENAME_PREFIX in caplog.text

def test_test_feedstock_labels(mocker, caplog):
    '''
    Test that labels work correctly.
    '''

    mocker.patch('open_ce.test_feedstock.load_test_file', side_effect=(lambda x, y: mock_load_test_file(os.path.join(test_dir, "open-ce-tests3.yaml"), y)))

    opence._main(["test", test_feedstock.COMMAND, "--conda_env_file", "tests/test-conda-env2.yaml"])
    assert not "Running: Create conda environment " + constants.CONDA_ENV_FILENAME_PREFIX in caplog.text
    assert not "Running: Test Long" in caplog.text
    assert not "Running: Test Distributed" in caplog.text
    assert not "Running: Test Long and Distributed" in caplog.text
    assert not "Running: Remove conda environment " + constants.CONDA_ENV_FILENAME_PREFIX in caplog.text
    validate_junit([[]],
                   [[]],
                   [0])
    caplog.clear()
    opence._main(["test", test_feedstock.COMMAND, "--conda_env_file", "tests/test-conda-env2.yaml", "--test_labels", "long"])
    assert "Running: Create conda environment " + constants.CONDA_ENV_FILENAME_PREFIX in caplog.text
    assert "Running: Test Long" in caplog.text
    assert not "Running: Test Distributed" in caplog.text
    assert not "Running: Test Long and Distributed" in caplog.text
    assert "Running: Remove conda environment " + constants.CONDA_ENV_FILENAME_PREFIX in caplog.text
    validate_junit([[{"name": "Create conda environment " + constants.CONDA_ENV_FILENAME_PREFIX},
                     {"name": "Test Long"},
                     {"name": "Remove conda environment " + constants.CONDA_ENV_FILENAME_PREFIX}]],
                   [[{"name": "Test Distributed"},
                     {"name": "Test Long and Distributed"}]],
                   [3])
    caplog.clear()
    opence._main(["test", test_feedstock.COMMAND, "--conda_env_file", "tests/test-conda-env2.yaml", "--test_labels", "distributed"])
    assert "Running: Create conda environment " + constants.CONDA_ENV_FILENAME_PREFIX in caplog.text
    assert not "Running: Test Long" in caplog.text
    assert "Running: Test Distributed" in caplog.text
    assert not "Running: Test Long and Distributed" in caplog.text
    assert "Running: Remove conda environment " + constants.CONDA_ENV_FILENAME_PREFIX in caplog.text
    validate_junit([[{"name": "Create conda environment " + constants.CONDA_ENV_FILENAME_PREFIX},
                     {"name": "Test Distributed"},
                     {"name": "Remove conda environment " + constants.CONDA_ENV_FILENAME_PREFIX}]],
                   [[{"name": "Test Long"},
                     {"name": "Test Long and Distributed"}]],
                   [3])
    caplog.clear()
    opence._main(["test", test_feedstock.COMMAND, "--conda_env_file", "tests/test-conda-env2.yaml", "--test_labels", "long,distributed"])
    assert "Running: Create conda environment " + constants.CONDA_ENV_FILENAME_PREFIX in caplog.text
    assert "Running: Test Long" in caplog.text
    assert "Running: Test Distributed" in caplog.text
    assert "Running: Test Long and Distributed" in caplog.text
    assert "Running: Remove conda environment " + constants.CONDA_ENV_FILENAME_PREFIX in caplog.text
    validate_junit([[{"name": "Create conda environment " + constants.CONDA_ENV_FILENAME_PREFIX},
                     {"name": "Test Distributed"},
                     {"name": "Remove conda environment " + constants.CONDA_ENV_FILENAME_PREFIX},
                     {"name": "Test Long"},
                     {"name": "Test Long and Distributed"}]],
                   [[]],
                   [5])

def test_test_feedstock_invalid_test_file(mocker,):
    '''
    Test that labels work correctly.
    '''

    mocker.patch('open_ce.test_feedstock.load_test_file', side_effect=(lambda x, y: mock_load_test_file(os.path.join(test_dir, "open-ce-tests4.yaml"), y)))

    with pytest.raises(OpenCEError) as exc:
        opence._main(["test", test_feedstock.COMMAND, "--conda_env_file", "tests/test-conda-env2.yaml"])
    assert "Unexpected Error: ['Test 1'] is not of expected type <class 'str'>" in str(exc.value)
