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

from open_ce.inputs import Argument
from open_ce import graph
from open_ce import build_env

COMMAND = "graph"

DESCRIPTION = 'Plot a dependency graph.'

ARGUMENTS = build_env.ARGUMENTS + \
            [Argument.WIDTH,
             Argument.HEIGHT]

def export_graph(args):
    '''Entry Function'''
    build_tree = build_env.construct_build_tree(args)

    graph.export_image(build_tree._tree, os.path.join(args.output_folder, "graph.png"), args.width, args.height) # pylint: disable=protected-access

ENTRY_FUNCTION = export_graph
