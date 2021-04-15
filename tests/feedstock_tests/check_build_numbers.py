#!/usr/bin/env python

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

import sys
import os
import pathlib

sys.path.append(os.path.join(pathlib.Path(__file__).parent.absolute(), '..'))
import open_ce.utils as utils # pylint: disable=wrong-import-position
import open_ce.inputs as inputs # pylint: disable=wrong-import-position

from common import get_configs, make_parser, get_build_numbers

def main(arg_strings=None):
    '''
    Entry function.
    '''
    parser = make_parser()
    args = inputs.parse_args(parser, arg_strings)
    variants = utils.make_variants(args.python_versions, args.build_types, args.mpi_types, args.cuda_versions)

    pr_branch = utils.get_output("git log -1 --format='%H'")
    utils.run_and_log("git remote set-head origin -a")
    default_branch = utils.get_output("git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'")

    variant_build_results = dict()
    for variant in variants:
        utils.run_and_log("git checkout {}".format(default_branch))
        main_build_config_data, main_config = get_configs(variant, args.conda_build_config)
        main_build_numbers = get_build_numbers(main_build_config_data, main_config, variant)

        utils.run_and_log("git checkout {}".format(pr_branch))
        pr_build_config_data, pr_config = get_configs(variant, args.conda_build_config)
        current_pr_build_numbers = get_build_numbers(pr_build_config_data, pr_config, variant)

        print("Build Info for Variant:   {}".format(variant))
        print("Current PR Build Info:    {}".format(current_pr_build_numbers))
        print("Main Branch Build Info:   {}".format(main_build_numbers))

        #No build numbers can go backwards without a version change.
        for package in main_build_numbers:
            if package in current_pr_build_numbers and current_pr_build_numbers[package]["version"] == main_build_numbers[package]["version"]:
                assert int(current_pr_build_numbers[package]["number"]) >= int(main_build_numbers[package]["number"]), "If the version doesn't change, the build number can't be reduced."

        #If packages are added or removed, don't require a version change
        if set(main_build_numbers.keys()) != set(current_pr_build_numbers.keys()):
            return

        #At least one package needs to increase the build number or change the version.
        checks = [current_pr_build_numbers[package]["version"] != main_build_numbers[package]["version"] or
                int(current_pr_build_numbers[package]["number"]) > int(main_build_numbers[package]["number"])
                    for package in main_build_numbers]
        variant_build_results[utils.variant_string(variant["python"], variant["build_type"], variant["mpi_type"], variant["cudatoolkit"])] = any(checks)
    assert any(variant_build_results.values()), "At least one package needs to increase the build number or change the version in at least one variant."

if __name__ == '__main__':
    try:
        main()
        print("BUILD NUMBER SUCCESS")
    except Exception as exc: # pylint: disable=broad-except
        print("BUILD NUMBER ERROR: ", exc)
        sys.exit(1)
