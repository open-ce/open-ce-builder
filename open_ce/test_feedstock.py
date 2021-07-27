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

import datetime
import os
import tempfile
from enum import Enum, unique, auto
import time
from junit_xml import TestSuite, TestCase, to_xml_report_string

from open_ce import utils
from open_ce import conda_env_file_generator
from open_ce import inputs
from open_ce.inputs import Argument
from open_ce.errors import OpenCEError, Error, log

COMMAND = 'feedstock'
DESCRIPTION = 'Test a feedstock as part of Open-CE'
ARGUMENTS = [Argument.CONDA_ENV_FILE, Argument.TEST_WORKING_DIRECTORY, Argument.TEST_LABELS,
             Argument.WORKING_DIRECTORY]

@unique
class Key(Enum):
    '''Enum for Test File Keys'''
    tests = auto()
    name = auto()
    command = auto()

_TEST_SCHEMA ={
    Key.name.name: utils.make_schema_type(str, True),
    Key.command.name: utils.make_schema_type(str, True)
}

_TEST_FILE_SCHEMA = {
    Key.tests.name: utils.make_schema_type([_TEST_SCHEMA])
}

class TestCommand():
    """
    Contains a test to run within a given conda environment.

    Args:
        name (str): The name describing the test.
        conda_env (str): The name of the conda environment that the test will be run in.
        bash_command (str): The bash command to run.
        create_env (bool): Whether this is the command to create a new conda environment.
        clean_env (bool): Whether this is the command to remove a conda environment.
        working_dir (str): Working directory to be used when executing the bash command.
    """
    #pylint: disable=too-many-arguments,too-many-instance-attributes
    def __init__(self, name, conda_env=None, bash_command="",
                 create_env=False, clean_env=False, working_dir=os.getcwd(),
                 test_file=None):
        self.bash_command = bash_command
        self.conda_env = conda_env
        self.name = name
        self.create_env = create_env
        self.clean_env = clean_env
        self.working_dir = working_dir
        self.feedstock_dir = os.getcwd()
        self.test_file = test_file

    def get_test_command(self, conda_env_file=None):
        """"
        Returns a string of the test command.

        Args:
            conda_env_file (str): The name of the original conda environment file.
                                  This is only needed when create_env is True.
        """
        output = ""
        output += "CONDA_BIN=$(dirname $(which conda))\n"
        output += "source ${CONDA_BIN}/../etc/profile.d/conda.sh\n"

        if self.create_env:
            channels = conda_env_file_generator.get_channels(conda_env_file)
            output += "conda env create -f " + conda_env_file + " -n " + self.conda_env + "\n"
            if channels:
                # Add the first channel from the environment file to the newly created conda environment.
                # This will allow tests to install other packages from the local conda channel.
                output += "conda activate " + self.conda_env + "\n"
                output += "conda config --env --add channels " + channels[0] + "\n"
            return output

        if self.clean_env:
            output += "conda env remove -y -n " + self.conda_env + "\n"
            return output

        output += "set -e\n"
        output += "conda activate " + self.conda_env + "\n"
        output += "export FEEDSTOCK_DIR=" + self.feedstock_dir + "\n"
        output += "set -x\n"
        output += self.bash_command + "\n"

        return output

    def run(self, conda_env_file):
        """
        Runs the test.

        Creates a temporary bash file, and writes the contents to `get_test_command` into it.
        Runs the generated bash file.
        Removes the temporary bash file.

        Args:
            conda_env_file (str): The name of the original conda environment file.
        """
        log.info("Running: %s", self.name)
        start_time = time.time()
        # Create file containing bash commands
        os.makedirs(self.working_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w+t', dir=self.working_dir, delete=False) as temp:
            temp.write(self.get_test_command(conda_env_file))
            temp_file_name = temp.name

        # Execute file
        retval,stdout,stderr = utils.run_command_capture("bash {}".format(temp_file_name),
                                                         cwd=self.working_dir)

        # Remove file containing bash commands
        os.remove(temp_file_name)

        result = TestResult(conda_env_file, retval,
                            name=self.name,
                            category=os.path.basename(self.feedstock_dir) + ":" + os.path.basename(conda_env_file),
                            file=self.test_file,
                            stdout=stdout if not retval else None,
                            stderr=stderr if not retval else None,
                            timestamp=start_time,
                            elapsed_sec = time.time() - start_time)

        if not retval:
            log.error(result.display_failed())

        return result

class TestResult(TestCase):
    """
    Contains the results of running a test.

    Args:
        name (str): The name of the test that was run.
        returncode (int): The return code of the test that was run.
        output (str): The resuling output from running the test.
    """
    def __init__(self, conda_env_file, return_code, *args, **kwargs):
        TestCase.__init__(self, *args, **kwargs)
        self.conda_env_file = conda_env_file
        if not self.classname:
            self.classname = self.category
        if not return_code:
            self.add_failure_info(message="Failed test: " + self.name,
                                  output="See stderr and stdout for output.")

    def display_failed(self):
        """
        Display the output from a failed test.
        """
        retval = ""
        if self.is_failure() or self.is_error():
            retval += "-" * 30
            retval += "\n"
            for failure in self.failures:
                retval += failure["message"] + "\n"
                retval += failure["output"] + "\n"
            retval += "-" * 30
            retval += "\n"
        return retval

def load_test_file(test_file, variants):
    """
    Load a given test file.

    Args:
        test_file (str): Path to the test file to load.
    """
    #pylint: disable=import-outside-toplevel
    from open_ce import conda_utils

    if not os.path.exists(test_file):
        return None

    test_file_data = conda_utils.render_yaml(test_file, variants, permit_undefined_jinja=True, schema=_TEST_FILE_SCHEMA)

    return test_file_data

def gen_test_commands(test_file=utils.DEFAULT_TEST_CONFIG_FILE, variants=None, working_dir=os.getcwd()):
    """
    Generate a list of test commands from the provided test file.

    Args:
        test_file (str): Path to the test file.
    """
    test_data = load_test_file(test_file, variants)
    if not test_data or not test_data['tests']:
        return []

    time_stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    conda_env = utils.CONDA_ENV_FILENAME_PREFIX + time_stamp

    test_commands = []

    # Create conda environment for testing
    test_commands.append(TestCommand(name="Create conda environment " + conda_env,
                                     conda_env=conda_env,
                                     create_env=True,
                                     working_dir=working_dir,
                                     test_file="Prefix-{}".format(test_file)))

    for test in test_data['tests']:
        test_commands.append(TestCommand(name=test.get('name'),
                                         conda_env=conda_env,
                                         bash_command=test.get('command'),
                                         working_dir=working_dir,
                                         test_file=test_file))

    test_commands.append(TestCommand(name="Remove conda environment " + conda_env,
                                     conda_env=conda_env,
                                     clean_env=True,
                                     working_dir=working_dir,
                                     test_file="Postfix-{}".format(test_file)))

    return test_commands

def run_test_commands(conda_env_file, test_commands):
    """
    Run a list of tests within a conda environment.

    Args:
        conda_env_file (str): The name of the conda environment file used to create the conda environment.
        test_commands (:obj:`list` of :obj:`TestCommand): List of test commands to run.
    """
    return [x.run(conda_env_file) for x in test_commands]

def test_feedstock(conda_env_file, test_labels=None,
                   test_working_dir=utils.DEFAULT_TEST_WORKING_DIRECTORY, working_directory=None):
    """
    Test a particular feedstock, provided by the working_directory argument.
    """
    saved_working_directory = None
    if working_directory:
        saved_working_directory = os.getcwd()
        os.chdir(os.path.abspath(working_directory))

    conda_env_file = os.path.abspath(conda_env_file)
    var_string = conda_env_file_generator.get_variant_string(conda_env_file)
    if var_string:
        variant_dict = utils.variant_string_to_dict(var_string)
    else:
        variant_dict = dict()
    for test_label in inputs.parse_arg_list(test_labels):
        variant_dict[test_label] = True
    test_commands = gen_test_commands(working_dir=test_working_dir, variants=variant_dict)
    test_results = run_test_commands(conda_env_file, test_commands)

    if saved_working_directory:
        os.chdir(saved_working_directory)

    return test_results

def process_test_results(test_results, output_folder="./", test_labels=None):
    """
    This function writes test results to a file, displays failed tests to stdout,
    and throws an exception if there are test failures.
    """
    label_string = ""
    if test_labels:
        label_string = "with labels: {}".format(str(test_labels))
    test_suites = [TestSuite("Open-CE tests for {} {}".format(feedstock, label_string), test_results[feedstock])
                        for feedstock in test_results]
    with open(os.path.join(output_folder, utils.DEFAULT_TEST_RESULT_FILE), 'w') as outfile:
        outfile.write(to_xml_report_string(test_suites))
    failed_tests = [x for key in test_results for x in test_results[key] if x.is_failure()]
    if failed_tests:
        raise OpenCEError(Error.FAILED_TESTS, len(failed_tests), str([failed_test.name for failed_test in failed_tests]))
    log.info("All tests passed!")

def test_feedstock_entry(args):
    '''Entry Function'''
    if not args.conda_env_files:
        raise OpenCEError(Error.CONDA_ENV_FILE_REQUIRED)

    if args.working_directory:
        feedstock = os.path.basename(os.path.abspath(args.working_directory))
    else:
        feedstock = os.path.basename(os.getcwd())
    test_results = {feedstock: []}
    for conda_env_file in inputs.parse_arg_list(args.conda_env_files):
        test_results[feedstock] += test_feedstock(conda_env_file,
                                       args.test_labels,
                                       args.test_working_dir,
                                       args.working_directory)
    process_test_results(test_results, args.test_working_dir, args.test_labels)

ENTRY_FUNCTION = test_feedstock_entry
