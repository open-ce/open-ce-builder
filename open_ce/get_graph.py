#!/usr/bin/env python
"""
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
"""

import os

from open_ce import utils
from open_ce import inputs
from open_ce.inputs import Argument
from open_ce import graph

COMMAND = "graph"

DESCRIPTION = 'Plot a dependency graph.'

ARGUMENTS = [Argument.CONDA_BUILD_CONFIG,
             Argument.OUTPUT_FOLDER,
             Argument.CHANNELS,
             Argument.ENV_FILE,
             Argument.PACKAGES,
             Argument.REPOSITORY_FOLDER,
             Argument.PYTHON_VERSIONS,
             Argument.BUILD_TYPES,
             Argument.MPI_TYPES,
             Argument.CUDA_VERSIONS,
             Argument.GIT_LOCATION,
             Argument.GIT_TAG_FOR_ENV,
             Argument.GIT_UP_TO_DATE,
             Argument.WIDTH,
             Argument.HEIGHT]

def export_graph(args):
    '''Entry Function'''

    utils.check_conda_build_configs_exist(args.conda_build_configs)

    # Checking conda-build existence if --container_build is not specified
    utils.check_if_package_exists('conda-build')

    # Here, importing BuildTree is intentionally done after checking
    # existence of conda-build as BuildTree uses conda_build APIs.
    from open_ce.build_tree import BuildTree  # pylint: disable=import-outside-toplevel

    # If repository_folder doesn't exist, create it
    if args.repository_folder and not os.path.exists(args.repository_folder):
        os.mkdir(args.repository_folder)

    # Create the build tree
    build_tree = BuildTree(env_config_files=args.env_config_file,
                               python_versions=inputs.parse_arg_list(args.python_versions),
                               build_types=inputs.parse_arg_list(args.build_types),
                               mpi_types=inputs.parse_arg_list(args.mpi_types),
                               cuda_versions=inputs.parse_arg_list(args.cuda_versions),
                               repository_folder=args.repository_folder,
                               channels=args.channels_list,
                               git_location=args.git_location,
                               git_tag_for_env=args.git_tag_for_env,
                               git_up_to_date=args.git_up_to_date,
                               conda_build_config=args.conda_build_configs,
                               packages=inputs.parse_arg_list(args.packages))

    graph.export_image(build_tree._tree, os.path.join(args.output_folder, "graph.png"), args.width, args.height) # pylint: disable=protected-access

ENTRY_FUNCTION = export_graph
