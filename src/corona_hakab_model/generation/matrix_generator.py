from itertools import islice
from generation.connection_types import ConnectionTypes, Connect_To_All_types, Random_Clustered_types, \
    Geographic_Clustered_types
from generation.matrix_consts import MatrixConsts
from generation.circles_generator import CirclesGenerator
from parasymbolic_matrix import ParasymbolicMatrix as CoronaMatrix
from typing import List
from generation.circles import SocialCircle
import numpy as np
import math
from generation.node import Node
from random import sample


# todo right now only supports parasymbolic matrix. need to merge with corona matrix class import selector
class MatrixGenerator:
    """
    this module gets the circles and agents created in circles generator and creates a matrix and sub matrices with them.
    """
    __slots__ = (
        "matrix_type",
        "matrix",
        "normalization_factor",
        "total_contagious_probability",
        "matrix_consts",
        "agents",
        "social_circles_by_connection_type",
        "geographic_circles",
        "size",
        "depth",
    )

    def __init__(
            self,
            circles_generator: CirclesGenerator,
            matrix_consts: MatrixConsts = MatrixConsts(),
    ):
        # initiate everything
        self.matrix_consts = matrix_consts
        # todo allow import from a json
        self.import_circles(circles_generator)
        self.size = len(self.agents)
        self.depth = len(ConnectionTypes)
        self.matrix = CoronaMatrix(self.size, self.depth)

        # create all sub matrices
        with self.matrix.lock_rebuild():
            # todo switch the depth logic, to get a connection type instead of int depth
            current_depth = 0

            for con_type in Connect_To_All_types:
                self.create_fully_connected_circles_matrix(con_type, self.social_circles_by_connection_type[con_type],
                                                           current_depth)
                current_depth += 1

            for con_type in Random_Clustered_types:
                self.create_random_clustered_circles_matrix(con_type, self.social_circles_by_connection_type[con_type],
                                                            current_depth)
                current_depth += 1

            for con_type in Geographic_Clustered_types:
                # todo create(). replace with the correct algorithm

                current_depth += 1

        print("done")
        # todo normalize_matrix()

    # todo support import of circles generator info. for now only getting one in init
    def import_circles(self, circles_generator):
        self.agents = circles_generator.agents
        self.social_circles_by_connection_type = circles_generator.social_circles_by_connection_type
        self.geographic_circles = circles_generator.geographic_circles

    def create_fully_connected_circles_matrix(self, con_type: ConnectionTypes, circles: List[SocialCircle], depth):
        connection_strength = self.matrix_consts.connection_type_to_connection_strength[con_type]
        for circle in circles:
            ids = np.array([a.index for a in circle.agents])
            vals = np.full_like(ids, connection_strength, dtype=np.float32)
            for i, row in enumerate(ids):
                temp = vals[i]
                vals[i] = 0
                self.matrix[depth, int(row), ids] = vals
                vals[i] = temp

    def create_random_clustered_circles_matrix(self, con_type: ConnectionTypes, circles: List[SocialCircle], depth):
        # the new connections will be saved here
        connections = [[] for _ in self.agents]
        # gets data from matrix consts
        connection_strength = self.matrix_consts.connection_type_to_connection_strength[con_type]
        daily_connections_float = self.matrix_consts.daily_connections_amount_by_connection_type[con_type]
        weekly_connections_float = self.matrix_consts.weekly_connections_amount_by_connection_type[con_type]
        total_connections_float = daily_connections_float + weekly_connections_float

        for circle in circles:
            agents = circle.agents
            indexes = [agent.index for agent in agents]
            nodes: List[Node] = [Node(index) for index in indexes]

            # the number of nodes. writes it for simplicity
            n = len(indexes)
            connections_amounts = iter(
                self.random_round(((daily_connections_float + weekly_connections_float) / 2), shape=n))
            # saves the already-instered nodes
            inserted_nodes = set()
            np.random.shuffle(nodes)
            con_amount = math.ceil((daily_connections_float + weekly_connections_float) / 2) + 1

            # checks, if the circle is too small, creates this as a family for now
            # todo, add small clustering algorithm
            if con_amount > n or n < self.matrix_consts.clustering_switching_point[0]:
                # todo use small circles algorithm
                continue

            # manually generate the minimum required connections
            for i in range(con_amount):
                other_nodes = nodes[0: con_amount]
                other_nodes.pop(i)
                nodes[i].add_connections(other_nodes)
                inserted_nodes.add(nodes[i])

                # add the newly made connections to the connections list. note that this is one directional,
                # but the other direction will be added when adding the other's connections
                connections[nodes[i].index].extend([node.index for node in other_nodes])

            # add the rest of the nodes, one at a time
            for node in islice(nodes, con_amount, None):
                connections_amount = connections_amounts.__next__()
                # selects the first node to attach to randomly
                rand_node = sample(inserted_nodes, 1)[0]
                inserted_nodes.remove(rand_node)

                # adds a connection between the nodes
                connections[node.index].append(rand_node.index)
                connections[rand_node.index].append(node.index)

                # todo change this to use p, and not only p = 1
                # randomly choose the rest of the connections from rand_node connections.
                nodes_to_return = []
                for _ in range(connections_amount - 1):
                    # randomly choose a node from rand_node connections
                    new_rand = rand_node.pop_random()
                    nodes_to_return.append(new_rand)
                    Node.connect(node, new_rand)

                    # add connection to connections list
                    connections[node.index].append(new_rand.index)
                    connections[new_rand.index].append(node.index)
                # connect current node with rand node. note that this only happens here to not pick yourself later on
                Node.connect(node, rand_node)
                # return the popped nodes back to rand_node connections, and rand node back to already inserted list
                rand_node.add_connections(nodes_to_return)
                inserted_nodes.add(rand_node)
                inserted_nodes.add(node)

        # insert all connections to matrix
        for agent, conns in zip(self.agents, connections):
            conns = np.array(conns)
            conns.sort()
            # rolls for each connection, whether it is daily or weekly
            strengthes = np.random.choice([connection_strength, connection_strength / 7], size=len(conns),
                                          p=[daily_connections_float / total_connections_float, weekly_connections_float / total_connections_float])
            v = np.full_like(conns, strengthes, dtype=np.float32)
            self.matrix[depth, agent.index, conns] = v

    @staticmethod
    def random_round(x: float, shape: int = 1):
        """
        randomly chooses between floor and ceil such that the average will be x
        :param x: a float
        :param shape: amount of wanted rolls
        :return: numpy array of ints, each is either floor or ceil
        """
        floor_prob = x - math.floor(x)
        ceil_prob = math.ceil(x) - x
        return np.random.choice([math.floor(x), math.ceil(x)], size=shape, p=[floor_prob, ceil_prob])
