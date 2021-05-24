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

import networkx as nx
import matplotlib.pyplot as plt

class OpenCEGraph(nx.DiGraph):
    """
    Wrapper class for the NetworkX DiGraph class.
    Improves functionality for objects that can be equal but different.
    """
    def add_node(self, node_for_adding, **attr):
        """
        Add a single node `node_for_adding` and update node attributes.
        """
        existing_node = next((x for x in self.nodes() if x == node_for_adding), None)
        if existing_node:
            super().add_node(existing_node, **attr)
        else:
            super().add_node(node_for_adding, **attr)

    def add_nodes_from(self, nodes_for_adding, **attr):
        """
        Add multiple nodes.
        """
        for n in nodes_for_adding:
            if isinstance(n, tuple):
                n, ndict = n
                newdict = attr.copy()
                newdict.update(ndict)
            else:
                newdict = attr
            self.add_node(n, **newdict)

    def add_edge(self, u_of_edge, v_of_edge, **attr):
        """
        Add an edge between u and v.
        """
        existing_u = next((x for x in self.nodes() if x == u_of_edge), None)
        if existing_u is None:
            super().add_node(u_of_edge)
            existing_u = u_of_edge

        existing_v = next((x for x in self.nodes() if x == v_of_edge), None)
        if existing_v is None:
            super().add_node(v_of_edge)
            existing_v = v_of_edge

        super().add_edge(existing_u, existing_v, **attr)

    def add_edges_from(self, ebunch_to_add, **attr):
        """
        Add all the edges in ebunch_to_add.
        """
        for e in ebunch_to_add:
            ne = len(e)
            if ne == 3:
                u, v, dd = e
            elif ne == 2:
                u, v = e
                dd = {}
            else:
                raise nx.NetworkXError(f"Edge tuple {e} must be a 2-tuple or 3-tuple.")
            newdict = attr.copy()
            newdict.update(dd)
            self.add_edge(u, v, **newdict)

def export_image(graph, output_file, x=50, y=50):
    '''
    Export a plot of a graph using matplotlib.
    '''
    f = plt.figure()
    f.set_figwidth(x)
    f.set_figheight(y)
    nx.draw_circular(graph, with_labels = True)
    plt.savefig(output_file)
