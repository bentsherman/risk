import random



class BaseAgent():
    def __init__(self, game, id, n_units):
        self.game = game
        self.id = id
        self.n_units = n_units
        self.cards = []

    def reinforce(self, n_reinforcements):
        raise NotImplementedError('not implemented')

    def select_attack_target(self):
        raise NotImplementedError('not implemented')

    def continue_attack(self, n_units_attack, n_units_defend):
        raise NotImplementedError('not implemented')

    def move(self):
        raise NotImplementedError('not implemented')



class DefaultAgent(BaseAgent):
    def reinforce(self, n_reinforcements):
        G = self.game._graph

        # get list of all nodes occupied by player
        player_nodes = [v for v in G.nodes if G.nodes[v]['player_id'] == self.id]

        # determine threat level of each node
        weights = [self.game.get_enemy_neighbors(v) for v in player_nodes]
        weights = [sum(G.nodes[v]['n_units'] for v in nodes) for nodes in weights]

        # place reinforcements, weighted by threat level
        placements = random.choices(player_nodes, weights=weights, k=n_reinforcements)
        node_updates = set(placements)

        for v in placements:
            G.nodes[v]['n_units'] += 1

        return node_updates

    def select_attack_target(self):
        G = self.game._graph

        # get list of all nodes occupied by player
        player_nodes = [v for v in G.nodes if G.nodes[v]['player_id'] == self.id]

        # perform an attack from each occupied node with some probability
        attack_prob = 0.5
        valid_nodes = [v for v in player_nodes if G.nodes[v]['n_units'] > 1]

        for v in valid_nodes:
            # determine whether this node has enemy neighbors
            enemy_neighbors = self.game.get_enemy_neighbors(v)

            if len(enemy_neighbors) == 0:
                continue

            # decide whether to attack from this node
            if random.uniform(0, 1) < attack_prob:
                continue

            # select a random neighbor to attack
            w = random.choice(enemy_neighbors)

            # generate source-target pair for attack
            yield v, w

    def continue_attack(self, n_units_attack, n_units_defend):
        return True

    def move(self):
        pass