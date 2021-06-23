#!/usr/bin/env python
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
import sys

from junit_xml import TestSuite, TestCase

from open_ce import build_feedstock
from open_ce import container_build
from open_ce import utils
from open_ce import inputs
from open_ce.inputs import Argument, ENV_BUILD_ARGS
from open_ce import test_feedstock
from open_ce.errors import OpenCEError, Error, log

COMMAND = "env"

DESCRIPTION = 'Build conda environment as part of Open-CE'

ARGUMENTS = ENV_BUILD_ARGS + \
            [Argument.SKIP_BUILD_PACKAGES,
             Argument.RUN_TESTS,
             Argument.CONTAINER_BUILD,
             Argument.TEST_LABELS,
             Argument.CONTAINER_BUILD_ARGS,
             Argument.CONTAINER_TOOL,
             Argument.CONDA_PKG_FORMAT]

def _run_tests(build_tree, test_labels, conda_env_files, output_folder):
    """
    Run through all of the tests within a build tree for the given conda environment files.

    Args:
        build_tree (BuildTree): The build tree containing the tests
        conda_env_files (dict): A dictionary where the key is a variant string and the value
                                is the name of a conda environment file.
    """
    test_results = {}
    # Run test commands for each conda environment that was generated
    for variant_string, conda_env_file in conda_env_files.items():
        test_feedstocks = build_tree.get_test_feedstocks(variant_string)
        if test_feedstocks:
            log.info("\n*** Running tests within the %s conda environment ***\n", os.path.basename(conda_env_file))
        for feedstock in test_feedstocks:
            log.info("Running tests for %s", feedstock)
            test_result = test_feedstock.test_feedstock(conda_env_file,
                                                        test_labels=test_labels,
                                                        working_directory=feedstock)
            if feedstock not in test_results.keys():
                test_results[feedstock] = test_result
            else:
                test_results[feedstock] += test_result
    label_string = ""
    if test_labels:
        label_string = "with labels: {}".format(str(test_labels))
    test_suites = [TestSuite("Open-CE tests for {} {}".format(feedstock, label_string), test_results[feedstock]) for feedstock in test_results]
    with open(os.path.join(output_folder, "test_results.xml"), 'w') as outfile:
        outfile.write(TestSuite.to_xml_string(test_suites))
    test_failures = [x for key in test_results for x in test_results[key] if x.is_failure()]
    test_feedstock.display_failed_tests(test_failures)
    if test_failures:
        raise OpenCEError(Error.FAILED_TESTS, len(test_failures))

def build_env(args):
    '''Entry Function'''
    utils.check_conda_build_configs_exist(args.conda_build_configs)

    if args.container_build:
        if len(args.cuda_versions.split(',')) > 1:
            raise OpenCEError(Error.TOO_MANY_CUDA)
        container_build.build_with_container_tool(args, sys.argv)
        return

    # Importing BuildTree is intentionally done here because it checks for the
    # existence of conda-build as BuildTree uses conda_build APIs.
    from open_ce.build_tree import construct_build_tree  # pylint: disable=import-outside-toplevel

    build_tree = construct_build_tree(args)
    # Generate conda environment files
    conda_env_files = build_tree.write_conda_env_files(output_folder=os.path.abspath(args.output_folder),
                                                       path=os.path.abspath(args.output_folder))
    log.info("Generated conda environment files from the selected build arguments: %s", conda_env_files.values())
    log.info("One can use these environment files to create a conda" \
          " environment using \"conda env create -f <conda_env_file_name>.\"")

    if not args.skip_build_packages:
        # Build each package in the packages list
        for build_command in build_tree:
            if not build_command.all_outputs_exist(args.output_folder):
                try:
                    log.info("Building %s", build_command.recipe)
                    build_feedstock.build_feedstock_from_command(build_command,
                                                            output_folder=os.path.abspath(args.output_folder),
                                                            pkg_format=args.conda_pkg_format)
                except OpenCEError as exc:
                    raise OpenCEError(Error.BUILD_RECIPE, build_command.repository, exc.msg) from exc
            else:
                log.info("Skipping build of %s because it already exists.",  + build_command.recipe)

    if args.run_tests:
        _run_tests(build_tree, inputs.parse_arg_list(args.test_labels), conda_env_files, os.path.abspath(args.output_folder))

ENTRY_FUNCTION = build_env
