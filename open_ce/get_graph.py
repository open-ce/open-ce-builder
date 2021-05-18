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

import networkx as nx

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

    #sub_tree_nodes = {node for initial_node in build_tree._initial_nodes for node in nx.descendants(build_tree._tree, initial_node)}
    #sub_tree_nodes = {node for initial_node in build_tree._initial_nodes for node in build_tree._tree.predecessors(initial_node)}
    #sub_tree_nodes = {node for initial_node in build_tree._initial_nodes for node in build_tree._tree.successors(initial_node)}
    #sub_tree_nodes = {node for node in sub_tree_nodes for package in node.packages if 'python' not in package}
    #sub_tree_nodes.update(build_tree._initial_nodes)

    # get all paths from estimator to base to see if there's more than just the direct.
    sub_tree_nodes = set()
    for source_node in {node for node in build_tree._initial_nodes for package in node.packages if "py-lightgbm-base" in package}:
        print("Source output: ", source_node.build_command.output_files)
        for dest_node in {node for node in build_tree._initial_nodes for package in node.packages if "openmpi" in package}:
            print("Destination output: ", dest_node.build_command.output_files)
            paths = nx.all_simple_paths(build_tree._tree, source_node, dest_node)
            for path in paths:
                print(path)
            sub_tree_nodes.update({node for path in paths for node in path})
        print()
        print("-----------")
        print()


    sub_tree = build_tree._tree.subgraph(sub_tree_nodes)

    graph.export_image(build_tree._tree, os.path.join(args.output_folder, "graph.png"), args.width, args.height) # pylint: disable=protected-access

ENTRY_FUNCTION = export_graph
