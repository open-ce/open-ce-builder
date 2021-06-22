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

from open_ce import utils
from open_ce.inputs import ENV_BUILD_ARGS
from open_ce.errors import OpenCEError, Error, log

COMMAND = 'config'

DESCRIPTION = 'Perform validation on a conda_build_config.yaml file.'

ARGUMENTS = ENV_BUILD_ARGS

def validate_config(args):
    '''Entry Function
    Validates a lits of Open-CE env files against a conda build config
    for a given set of variants.
    '''
    # Importing BuildTree is intentionally done here because it checks for the
    # existence of conda-build as BuildTree uses conda_build APIs.
    from open_ce.build_tree import construct_build_tree  # pylint: disable=import-outside-toplevel

    for env_file in list(args.env_config_file): #make a copy of the env_file list
        log.info('Validating %s for %s', args.conda_build_configs, env_file)
        try:
            args.env_config_file = [env_file]
            _ = construct_build_tree(args)
        except OpenCEError as err:
            raise OpenCEError(Error.VALIDATE_CONFIG, args.conda_build_configs, env_file, err.msg) from err
        log.info('Successfully validated %s for %s', args.conda_build_configs, env_file)

def validate_build_tree(tree, external_deps, start_nodes=None):
    '''
    Check a build tree for dependency compatability.
    '''
    # Importing BuildTree is intentionally done here because it checks for the
    # existence of conda-build as BuildTree uses conda_build APIs.
    from open_ce import build_tree  # pylint: disable=import-outside-toplevel

    packages = [package for recipe in build_tree.traverse_build_commands(tree, start_nodes)
                            for package in recipe.packages]
    channels = {channel for recipe in build_tree.traverse_build_commands(tree, start_nodes) for channel in recipe.channels}
    env_channels = {channel for node in tree.nodes() for channel in node.channels}
    deps = build_tree.get_installable_packages(tree, external_deps, start_nodes, True)

    pkg_args = " ".join(["\"{}\"".format(utils.generalize_version(dep)) for dep in deps
                                                                    if not utils.remove_version(dep) in packages])
    channel_args = " ".join({"-c \"{}\"".format(channel) for channel in channels.union(env_channels)})

    cli = "conda create --dry-run -n test_conda_dependencies {} {}".format(channel_args, pkg_args)
    ret_code, std_out, std_err = utils.run_command_capture(cli)
    if not ret_code:
        raise OpenCEError(Error.VALIDATE_BUILD_TREE, cli, std_out, std_err)

ENTRY_FUNCTION = validate_config
