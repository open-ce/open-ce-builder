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

import os

from open_ce import inputs
from open_ce.inputs import Argument
from open_ce.errors import OpenCEError, Error

COMMAND = 'feedstock'
DESCRIPTION = 'Test a feedstock as part of Open-CE'
ARGUMENTS = [Argument.CONDA_ENV_FILE, Argument.TEST_WORKING_DIRECTORY, Argument.TEST_LABELS,
             Argument.WORKING_DIRECTORY]

def test_feedstock_entry(args):
    '''Entry Function'''
    # Importing test_utils is intentionally done here because it checks for the
    # existence of junit_xml.
    from open_ce.test_utils import test_feedstock, process_test_results  # pylint: disable=import-outside-toplevel

    if not args.conda_env_files:
        raise OpenCEError(Error.CONDA_ENV_FILE_REQUIRED)

    feedstock = os.path.basename(os.path.abspath(args.working_directory))
    test_results = {feedstock: []}
    for conda_env_file in inputs.parse_arg_list(args.conda_env_files):
        test_results[feedstock] += test_feedstock(conda_env_file,
                                       args.test_labels,
                                       args.test_working_dir,
                                       args.working_directory)
    process_test_results(test_results, args.test_working_dir, args.test_labels)

ENTRY_FUNCTION = test_feedstock_entry
