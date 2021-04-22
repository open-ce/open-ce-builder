#!/usr/bin/env python

# *****************************************************************
# (C) Copyright IBM Corp. 2021. All Rights Reserved.
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

import sys
import os
import pathlib

sys.path.append(os.path.join(pathlib.Path(__file__).parent.absolute(), '..'))
import open_ce.utils as utils # pylint: disable=wrong-import-position
import open_ce.inputs as inputs # pylint: disable=wrong-import-position
from common import get_configs, make_parser, check_recipes

def main(arg_strings=None):
    '''
    Entry function.
    '''
    parser = make_parser()
    args = inputs.parse_args(parser, arg_strings)
    variants = utils.make_variants(args.python_versions, args.build_types, args.mpi_types, args.cuda_versions)

    check_result = True
    for variant in variants:
        main_build_config_data, main_config = get_configs(variant, args.conda_build_config)
        if not check_recipes(main_build_config_data, main_config, variant):
            check_result = False
            print("Recipe validation failed for variant '{}'.".format(variant))

    assert check_result, "All recipes must be valid."

if __name__ == '__main__':
    try:
        main()
        print("RECIPE VALIDATION SUCCESS")
    except Exception as exc: # pylint: disable=broad-except
        print("RECIPE VALIDATION ERROR: ", exc)
        sys.exit(1)
