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

from open_ce.inputs import Argument, ENV_BUILD_ARGS
from open_ce import graph
from open_ce import utils
from open_ce.errors import log

COMMAND = "graph"

DESCRIPTION = 'Plot a dependency graph.'

ARGUMENTS = ENV_BUILD_ARGS + \
            [Argument.WIDTH,
             Argument.HEIGHT]

def export_graph(args):
    '''Entry Function'''
    # Importing BuildTree is intentionally done here because it checks for the
    # existence of conda-build as BuildTree uses conda_build APIs.
    from open_ce.build_tree import construct_build_tree  # pylint: disable=import-outside-toplevel

    build_tree = construct_build_tree(args)
    os.makedirs(args.output_folder, exist_ok=True)
    graph_output = os.path.join(args.output_folder, utils.DEFAULT_GRAPH_FILE)
    graph.export_image(build_tree._tree, graph_output, args.width, args.height) # pylint: disable=protected-access
    log.info("Build graph successfully output to: %s", graph_output)

ENTRY_FUNCTION = export_graph
