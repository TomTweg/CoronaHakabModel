from collections import defaultdict
from typing import List

from agent import Agent
from medical_state_machine import MedicalStateMachine
from state_machine import PendingTransfers


class MedicalStateManager:
    """
    Manages the medical state
    """

    def __init__(self, medical_state_machine: MedicalStateMachine):
        self.medical_state_machine = medical_state_machine
        self.pending_transfers = PendingTransfers()

    def step(self, new_sick: List[Agent]):
        # all the new sick agents are leaving their previous step
        changed_state_leaving = defaultdict(list)
        # agents which are going to enter the new state
        changed_state_introduced = defaultdict(list)
        # list of all the new sick agents

        # all the new sick are going to get to the next state
        for agent in new_sick:
            changed_state_leaving[agent.medical_state].append(agent)
            agent.set_medical_state_no_inform(self.medical_state_machine.get_state_upon_infection(agent))
            changed_state_introduced[agent.medical_state].append(agent)

        # saves this number for supervising
        new_sick_counter = len(new_sick)  # TODO should be handled in SimulationManager

        moved = self.pending_transfers.advance()
        for (agent, destination, origin, _) in moved:
            agent.set_medical_state_no_inform(destination)

            changed_state_introduced[destination].append(agent)
            changed_state_leaving[origin].append(agent)

        for state, agents in changed_state_introduced.items():
            state.add_many(agents)
            self.pending_transfers.extend(state.transfer(agents))

        for state, agents in changed_state_leaving.items():
            state.remove_many(agents)

        return dict(new_sick=new_sick_counter)