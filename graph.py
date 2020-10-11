from collections import namedtuple
import itertools
import matplotlib as mpl
import matplotlib.colors
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import networkx as nx
import networkx.algorithms
import random



class BaseGraph():
    def __init__(self):
        pass

    def create(self):
        raise NotImplementedError('not implemented')



class GridGraph(BaseGraph):
    def __init__(self, grid_size=8, grid_remove=0.25, grid_perturb=0.25):
        self.grid_size = grid_size
        self.grid_remove = grid_remove
        self.grid_perturb = grid_perturb

    def create(self):
        # initialize graph
        G = nx.generators.grid_graph(dim=[self.grid_size, self.grid_size], periodic=False)

        for v in G.nodes:
            G.nodes[v]['pos'] = v
            G.nodes[v]['player_id'] = None
            G.nodes[v]['n_units'] = 0

        # remove a random subset of nodes
        remove_nodes = list(G.nodes)
        random.shuffle(remove_nodes)
        remove_nodes = remove_nodes[0 : int(len(remove_nodes) * self.grid_remove)]

        G.remove_nodes_from(remove_nodes)

        # extract the largest connected component
        components = nx.algorithms.components.connected_components(G)
        components = sorted(components, key=len, reverse=True)

        G = G.subgraph(components[0])

        # randomly perturb the position of each node
        for v in G.nodes:
            x, y = G.nodes[v]['pos']
            x += random.uniform(-self.grid_perturb, self.grid_perturb)
            y += random.uniform(-self.grid_perturb, self.grid_perturb)
            G.nodes[v]['pos'] = x, y

        return G