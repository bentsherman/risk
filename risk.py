import argparse
from collections import namedtuple
import itertools
import matplotlib as mpl
import matplotlib.animation
import matplotlib.colors
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import networkx as nx
import networkx.algorithms
import random
import time



CARD_TYPE_INFANTRY = 1
CARD_TYPE_CAVALRY = 2
CARD_TYPE_ARTILLERY = 3



Card = namedtuple('Card', ['node', 'type'])



class Agent():
    def __init__(self, game, id, n_units):
        self.game = game
        self.id = id
        self.n_units = n_units
        self.cards = []

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



class GameState():
    def __init__(self, grid_size=8, grid_remove=0.25, grid_perturb=0.25, n_players=2, n_starting_units=50):
        # validate arguments
        n_nodes = grid_size ** 2

        if n_nodes < n_players:
            raise ValueError('Not enough grid points for all players')

        if n_players * n_starting_units < n_nodes:
            raise ValueError('Players do not have enough starting units to occupy the entire grid')

        # initialize figure
        self._fig = plt.figure(figsize=(12, 12))
        self._frames = 0

        # initialize graph
        G = nx.generators.grid_graph(dim=[grid_size, grid_size], periodic=False)

        for v in G.nodes:
            G.nodes[v]['pos'] = v
            G.nodes[v]['player_id'] = None
            G.nodes[v]['n_units'] = 0

        # remove a random subset of nodes
        remove_nodes = list(G.nodes)
        random.shuffle(remove_nodes)
        remove_nodes = remove_nodes[0 : int(len(remove_nodes) * grid_remove)]

        G.remove_nodes_from(remove_nodes)

        # extract the largest connected component
        components = nx.algorithms.components.connected_components(G)
        components = sorted(components, key=len, reverse=True)

        G = G.subgraph(components[0])

        # randomly perturb the position of each node
        for v in G.nodes:
            x, y = G.nodes[v]['pos']
            x += random.uniform(-grid_perturb, grid_perturb)
            y += random.uniform(-grid_perturb, grid_perturb)
            G.nodes[v]['pos'] = x, y

        # initialize cards
        card_types = [CARD_TYPE_INFANTRY, CARD_TYPE_CAVALRY, CARD_TYPE_ARTILLERY]
        cards = [Card(v, t) for v, t in zip(G.nodes, itertools.cycle(card_types))]
        random.shuffle(cards)

        # initialize players
        players = [Agent(self, i + 1, n_starting_units) for i in range(n_players)]

        # assign nodes randomly to players
        unclaimed_nodes = list(G.nodes)
        random.shuffle(unclaimed_nodes)

        for i, v in enumerate(unclaimed_nodes):
            player = players[i % n_players]
            G.nodes[v]['player_id'] = player.id
            G.nodes[v]['n_units'] += 1
            player.n_units -= 1

        # reinforce each player's territories randomly
        for player in players:
            # get list of nodes occupied by player
            player_nodes = [v for v in G.nodes if G.nodes[v]['player_id'] == player.id]

            while player.n_units > 0:
                v = random.choice(player_nodes)
                G.nodes[v]['n_units'] += 1
                player.n_units -= 1

        # save attributes
        self._graph = G
        self._current_card_bonus = 5
        self._cards = cards
        self._discards = []
        self._players = players

    def render(self, args):
        # unpack arguments
        node_updates, text = args

        # print frame number
        print('rendering frame %d' % (self._frames))
        self._frames += 1

        # determine graph attributes
        G = self._graph
        pos = {v: G.nodes[v]['pos'] for v in G.nodes}
        sizes = [(300 + 300 * G.nodes[v]['n_units']) for v in G.nodes]
        colors = [G.nodes[v]['player_id'] / len(self._players) for v in G.nodes]
        labels = {v: G.nodes[v]['n_units'] for v in G.nodes}

        # highlight updated nodes
        edgecolors = [('r' if v in node_updates else 'w') for v in G.nodes]

        # clear figure
        plt.clf()

        # create colormap for graph, legend
        norm = mpl.colors.Normalize(vmin=1, vmax=len(self._players))
        cmap = plt.get_cmap('Accent')
        smap = cm.ScalarMappable(norm=norm, cmap=cmap)

        # draw graph
        nx.draw_networkx(
            G,
            pos=pos,
            with_labels=False,
            node_size=sizes,
            node_color=colors,
            labels=labels,
            cmap=cmap,
            linewidths=2.0,
            edgecolors=edgecolors)

        # plot dummy points for legend
        xmin, xmax = plt.xlim()
        ymin, ymax = plt.ylim()

        for player in self._players:
            color = smap.to_rgba(player.id)
            label = 'Player %d' % (player.id)
            plt.plot([-10], [-10], 'o', color=color, label=label, markersize=10)

        plt.xlim(xmin, xmax)
        plt.ylim(ymin, ymax)

        # draw legend
        plt.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))

        # draw text annotation if specified
        if text != None:
            plt.text(xmin, ymax * 1.05, text, fontsize='x-large')

    def get_card_trio(self, player):
        # generate all subsets of size three in player hand
        card_trio = None

        for trio in itertools.combinations(player.cards, 3):
            if sum(c.type for c in trio) % 3 == 0:
                card_trio = trio
                break

        # remove card trio from player hand if found
        if card_trio != None:
            for c in card_trio:
                player.cards.remove(c)

        return card_trio

    def get_enemy_neighbors(self, v):
        G = self._graph
        return [w for w in G.neighbors(v) if G.nodes[v]['player_id'] != G.nodes[w]['player_id']]

    def roll_dice(self, n_dice):
        return sorted([random.randint(1, 6) for i in range(n_dice)], reverse=True)

    def do_attack(self, attacker, v_attack, v_defend):
        G = self._graph

        # raise error if attacking node doesn't have enough units
        if G.nodes[v_attack]['n_units'] == 1:
            raise ValueError('Attacking node doesn\'t have enough units!')

        # determine the number of units available to attack and defend
        n_units_attack = G.nodes[v_attack]['n_units'] - 1
        n_units_defend = G.nodes[v_defend]['n_units']

        # temporarily remove units from nodes
        G.nodes[v_attack]['n_units'] -= n_units_attack
        G.nodes[v_defend]['n_units'] -= n_units_defend

        # do battle until one side wins or attacker retreats
        while n_units_attack > 0 and n_units_defend > 0 and attacker.continue_attack(n_units_attack, n_units_defend):
            # roll attack dice and defend dice
            dice_attack = self.roll_dice(min(n_units_attack, 3))
            dice_defend = self.roll_dice(min(n_units_defend, 2))

            # check each die result and remove units accordingly
            for r_atk, r_def in zip(dice_attack, dice_defend):
                if r_atk > r_def:
                    n_units_attack -= 1
                else:
                    n_units_defend -= 1

        # if attacker won, move attacking units into defending node
        if n_units_defend == 0:
            G.nodes[v_defend]['player_id'] = G.nodes[v_attack]['player_id']
            G.nodes[v_defend]['n_units'] = n_units_attack
            return True

        # if defender won, return defending units to their node
        if n_units_attack == 0:
            G.nodes[v_defend]['n_units'] += n_units_defend
            return False

    def do_turn(self, i):
        G = self._graph

        # get current player
        player = self._players[i]

        # skip turn if player was already eliminated
        player_nodes = [v for v in G.nodes if G.nodes[v]['player_id'] == player.id]

        if len(player_nodes) == 0:
            return

        # compute reinforcements from occupied nodes
        n_reinforcements = max(3, len(player_nodes) // 3)

        # trade cards for reinforcements if possible
        card_trio = self.get_card_trio(player)

        if card_trio != None:
            self._discards += card_trio
            n_reinforcements += self._current_card_bonus
            self._current_card_bonus += 5

        # place reinforcements
        node_updates = player.reinforce(n_reinforcements)

        # render updated graph
        yield (node_updates, 'Player %d placed %d reinforcements' % (player.id, n_reinforcements))

        # perform attacks
        attack_success = False

        for v, w in player.select_attack_target():
            # render updated graph
            yield ([v, w], 'Player %d attacking from %s with %d units, Player %d defending from %s with %d units' % (
                G.nodes[v]['player_id'], v, G.nodes[v]['n_units'],
                G.nodes[w]['player_id'], w, G.nodes[w]['n_units']
            ))

            # perform attack
            success = self.do_attack(player, v, w)

            # render updated graph
            if success:
                attack_success = True
                text = 'Attacking player won!'
            else:
                text = 'Defending player won!'

            yield ([v, w], text)

        # move units
        player.move()

        # draw card if player captured a node
        if attack_success:
            player.cards.append(self._cards.pop())

        # reset discards if card deck is empty
        if len(self._cards) == 0:
            self._cards = self._discards
            self._discards = []

            random.shuffle(self._cards)

    def do_round(self):
        # perform each player's turn
        for i in range(len(self._players)):
            yield from self.do_turn(i)

    def check_winner(self):
        # check if all nodes are occupied by a single player
        player_ids = [self._graph.nodes[v]['player_id'] for v in self._graph.nodes]
        player_ids = list(set(player_ids))

        if len(player_ids) == 1:
            return player_ids[0]
        else:
            return None

    def animate(self):
        # draw initial state
        yield ([], None)

        # play for several rounds
        while True:
            # play a round
            yield from self.do_round()

            # check if someone has won
            player_id = self.check_winner()

            if player_id != None:
                yield ([], 'Player %d won!' % (player_id))
                break




def main():
    # parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--grid-size', help='size of each grid dimension', type=int, default=8)
    parser.add_argument('--n-players', help='number of players', type=int, default=2)
    parser.add_argument('--n-frames', help='number of frames to render', type=int, default=100)
    parser.add_argument('--frame-interval', help='length of each frame in ms', type=int, default=500)

    args = parser.parse_args()

    # initialize game state
    game = GameState(grid_size=args.grid_size, n_players=args.n_players)

    # initialize animation
    t0 = time.perf_counter()

    anim = mpl.animation.FuncAnimation(game._fig, game.render, frames=game.animate, save_count=args.n_frames, interval=args.frame_interval)
    anim.save('risk.mp4')

    t1 = time.perf_counter()

    # print performance metrics
    t = t1 - t0
    q = args.n_frames / t
    print('processing time: %.3f s, %.3f frames / s' % (t, q))



if __name__ == '__main__':
    main()