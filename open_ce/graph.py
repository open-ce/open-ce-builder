import networkx as nx

class OpenCEGraph(nx.DiGraph):
    def __init__(self, incoming_graph_data=None, **attr):
        super().__init__(incoming_graph_data, **attr)

    def add_node(self, node_for_adding, **attr):
        if node_for_adding in self.nodes():
            existing_node = [x for x in self.nodes() if x == node_for_adding][0]
            super().add_node(existing_node, **attr)
        else:
            super().add_node(node_for_adding, **attr)

    def add_nodes_from(self, nodes_for_adding, **attr):
        for n in nodes_for_adding:
            try:
                newnode = n not in self._node
                newdict = attr
            except TypeError:
                n, ndict = n
                newnode = n not in self._node
                newdict = attr.copy()
                newdict.update(ndict)
            self.add_node(n, **newdict)

    def add_edge(self, u_of_edge, v_of_edge, **attr):
        self.add_nodes_from([u_of_edge, v_of_edge])
        existing_u = [x for x in self.nodes() if x == u_of_edge][0]
        existing_v = [x for x in self.nodes() if x == v_of_edge][0]
        super().add_edge(existing_u, existing_v, **attr)

    def add_edges_from(self, ebunch_to_add, **attr):
        for e in ebunch_to_add:
            ne = len(e)
            if ne == 3:
                u, v, dd = e
            elif ne == 2:
                u, v = e
                dd = {}
            else:
                raise nx.NetworkXError(f"Edge tuple {e} must be a 2-tuple or 3-tuple.")
            self.add_edge(u, v, **attr)
