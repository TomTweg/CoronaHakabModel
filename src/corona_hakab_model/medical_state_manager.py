from collections import defaultdict
from typing import List

import manager
from agent import Agent
from state_machine import PendingTransfers


class MedicalStateManager:
    """
    Manages the medical state
    """

    def __init__(self, sim_manager: "manager.SimulationManager"):
        self.manager = sim_manager
        self.pending_transfers = PendingTransfers()

    def step(self, new_sick: List[Agent]):
        # all the new sick agents are leaving their previous step
        changed_state_leaving = defaultdict(list)
        # agents which are going to enter the new state
        changed_state_introduced = defaultdict(list)
        # list of all the new sick agents

        # all the new sick are going to get to the next state
        if len(new_sick) > 0:
            new_sick_agents = self.manager.agents_df.at(new_sick)
            infected_states = [self.manager.medical_machine.get_state_upon_infection(agent_ind) for agent_ind in new_sick]

            # for agent_ind in new_sick:
            #     changed_state_leaving[self.manager.agents_df.at(agent_ind).medical_state].append(agent_ind)
            #     infected_state = self.manager.medical_machine.get_state_upon_infection(agent_ind)
            #     self.manager.agents_df.change_agents_state(agent_ind, infected_state)
            #     changed_state_introduced[infected_state].append(agent_ind)

            for agent_ind, infected_state, agent in zip(new_sick, infected_states, new_sick_agents.itertuples()):
                changed_state_leaving[agent.medical_state].append(agent_ind)
                changed_state_introduced[infected_state].append(agent_ind)
            self.manager.agents_df.change_agents_state(new_sick, infected_states)


        # saves this number for supervising
        self.manager.new_sick_counter = len(new_sick)  # TODO should be handled in SimulationManager

        moved = self.pending_transfers.advance()
        for (agent_ind, destination, origin, _) in moved:
            self.manager.agents_df.change_agents_state([agent_ind], destination)

            changed_state_introduced[destination].append(agent_ind)
            changed_state_leaving[origin].append(agent_ind)

        for state, agents in changed_state_introduced.items():
            state.add_many(agents)
            self.pending_transfers.extend(state.transfer(agents))

        for state, agents in changed_state_leaving.items():
            state.remove_many(agents)
