from typing import List

from agent import Agent
from scipy.stats import rv_discrete


class CircularConnectionsMatrix:

    __slots__ = "name", "agents", "circle_size_probability", "connection_strength"

    # todo switch type to a named-tuple
    def __init__(
        self, name: str, agents: List[Agent], circle_size_probability: rv_discrete, connection_strength: float
    ):
        self.name = name
        self.agents = agents
        self.circle_size_probability = circle_size_probability
        self.connection_strength = connection_strength


class NonCircularConnectionMatrix:

    __slots__ = "name", "agents", "scale_factor", "connection_strength"

    def __init__(self, name: str, agents: List[Agent], scale_factor: float, connection_strength: float):
        self.name = name
        self.agents = agents
        self.scale_factor = scale_factor
        self.connection_strength = connection_strength
