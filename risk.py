import argparse
import matplotlib as mpl
import matplotlib.animation
import matplotlib.colors
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import networkx as nx
import random



class GameState():
    def __init__(self, grid_dim=[8, 8], n_players=2):
        # initialize figure
        self._fig = plt.figure(figsize=(12, 12))
        self._frames = 0

        # initialize graph
        self._graph = nx.generators.grid_graph(dim=grid_dim, periodic=False)

        for v in self._graph.nodes:
            self._graph.nodes[v]['player_id'] = None
            self._graph.nodes[v]['n_units'] = 0

        # initialize players
        STARTING_UNITS = {
            2: 50,
            3: 35,
            4: 30,
            5: 25,
            6: 20
        }

        self._players = [{'id': i + 1, 'n_units': STARTING_UNITS[n_players]} for i in range(n_players)]

        # assign nodes randomly to players
        unclaimed_nodes = list(self._graph.nodes)
        random.shuffle(unclaimed_nodes)

        for i, v in enumerate(unclaimed_nodes):
            player = self._players[i % n_players]
            self._graph.nodes[v]['player_id'] = player['id']
            self._graph.nodes[v]['n_units'] += 1
            player['n_units'] -= 1

        # reinforce each player's territories randomly
        for player in self._players:
            # get list of nodes occupied by player
            player_nodes = [v for v in self._graph.nodes if self._graph.nodes[v]['player_id'] == player['id']]

            while player['n_units'] > 0:
                v = random.choice(player_nodes)
                self._graph.nodes[v]['n_units'] += 1
                player['n_units'] -= 1

    def render(self, args):
        # unpack arguments
        node_updates, text = args

        # print frame number
        print('rendering frame %d' % (self._frames))
        self._frames += 1

        # determine colors
        pos = {node: node for node in self._graph.nodes}
        sizes = [500 * self._graph.nodes[v]['n_units'] for v in self._graph.nodes]
        colors = [self._graph.nodes[v]['player_id'] / len(self._players) for v in self._graph.nodes]
        labels = {v: self._graph.nodes[v]['n_units'] for v in self._graph.nodes}

        # highlight updated nodes
        edgecolors = [('r' if v in node_updates else 'w') for v in self._graph.nodes]

        # clear figure
        plt.clf()

        # plot dummy points for legend
        norm = mpl.colors.Normalize(vmin=1, vmax=len(self._players))
        cmap = plt.get_cmap('Accent')
        smap = cm.ScalarMappable(norm=norm, cmap=cmap)

        # draw graph
        nx.draw_networkx(self._graph, pos=pos, with_labels=False, node_size=sizes, node_color=colors, labels=labels, cmap=cmap, edgecolors=edgecolors)

        xmin, xmax = plt.xlim()
        ymin, ymax = plt.ylim()

        for player in self._players:
            color = smap.to_rgba(player['id'])
            label = 'Player %d' % (player['id'])
            plt.plot([-10], [-10], 'o', color=color, label=label, markersize=10)

        plt.xlim(xmin, xmax)
        plt.ylim(ymin, ymax)

        # draw legend
        plt.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))

        # draw text annotation if specified
        if text != None:
            plt.text(xmin, ymax * 1.05, text)

    def roll_dice(self, n_dice):
        return sorted([random.randint(1, 6) for i in range(n_dice)], reverse=True)

    def do_attack(self, v_attack, v_defend):
        # raise error if attacking node doesn't have enough units
        if self._graph.nodes[v_attack]['n_units'] == 1:
            raise ValueError('attacking node doesn\'t have enough units!')

        # determine the number of units available to attack and defend
        n_units_attack = self._graph.nodes[v_attack]['n_units'] - 1
        n_units_defend = self._graph.nodes[v_defend]['n_units']

        # temporarily remove units from nodes
        self._graph.nodes[v_attack]['n_units'] -= n_units_attack
        self._graph.nodes[v_defend]['n_units'] -= n_units_defend

        # do battle until one side wins
        while n_units_attack > 0 and n_units_defend > 0:
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
            self._graph.nodes[v_defend]['player_id'] = self._graph.nodes[v_attack]['player_id']
            self._graph.nodes[v_defend]['n_units'] = n_units_attack
            return True

        # if defender won, return defending units to their node
        if n_units_attack == 0:
            self._graph.nodes[v_defend]['n_units'] += n_units_defend
            return False

    def do_turn(self, i):
        # get current player
        player = self._players[i]

        # compute reinforcements
        player_nodes = [v for v in self._graph.nodes if self._graph.nodes[v]['player_id'] == player['id']]
        n_reinforcements = max(3, len(player_nodes) // 3)
        player['n_units'] += n_reinforcements

        # skip turn if player was already eliminated
        if len(player_nodes) == 0:
            return

        # place reinforcements
        node_updates = []

        while player['n_units'] > 0:
            v = random.choice(player_nodes)
            self._graph.nodes[v]['n_units'] += 1
            player['n_units'] -= 1
            node_updates.append(v)

        # render updated graph
        yield (node_updates, 'Player %d placed %d reinforcements' % (player['id'], n_reinforcements))

        # perform attacks
        valid_nodes = [v for v in player_nodes if self._graph.nodes[v]['n_units'] > 1]

        for v in valid_nodes:
            # determine whether this node has enemy neighbors
            enemy_neighbors = [w for w in list(self._graph.neighbors(v)) if self._graph.nodes[w]['player_id'] != player['id']]

            if len(enemy_neighbors) == 0:
                continue

            # decide whether to attack from this node
            if random.uniform(0, 1) < 0.5:
                continue

            # select a random neighbor to attack
            w = random.choice(enemy_neighbors)

            # render updated graph
            yield ([v, w], 'Player %d attacking from %s with %d units, Player %d defending from %s with %d units' % (
                self._graph.nodes[v]['player_id'], v, self._graph.nodes[v]['n_units'],
                self._graph.nodes[w]['player_id'], w, self._graph.nodes[w]['n_units']
            ))

            # perform attack
            success = self.do_attack(v, w)

            # render updated graph
            if success:
                text = 'Attacking player won!'
            else:
                text = 'Defending player won!'

            yield ([v, w], text)

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
    parser.add_argument('--n-players', help='number of players', default=2)
    parser.add_argument('--n-rounds', help='number of rounds', default=10)

    args = parser.parse_args()

    # initialize game state
    game = GameState(n_players=args.n_players)

    # initialize animation
    anim = mpl.animation.FuncAnimation(game._fig, game.render, frames=game.animate, interval=1000)
    anim.save('risk.mp4')



if __name__ == '__main__':
    main()