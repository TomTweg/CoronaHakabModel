from __future__ import annotations

from collections import namedtuple
from typing import TYPE_CHECKING, Callable, List

import numpy as np
from agent import Agent
from util import Queue

if TYPE_CHECKING:
    from manager import SimulationManager


PendingTestResult = namedtuple("PendingTestResult", ["agent", "test_result", "original_duration"])


class PendingTestResults(Queue[PendingTestResult]):
    def __init__(self):
        super().__init__()


class DetectionTest:
    def __init__(self, detection_prob, false_alarm_prob, time_until_result):
        self.detection_prob = detection_prob
        self.false_alarm_prob = false_alarm_prob
        self.time_until_result = time_until_result

    def test(self, agent: Agent):
        if agent.medical_state.detectable:
            test_result = np.random.rand() < self.detection_prob
        else:
            test_result = np.random.rand() < self.false_alarm_prob

        pending_result = PendingTestResult(agent, test_result, self.time_until_result)
        return pending_result


class HealthcareManager:
    def __init__(self, sim_manager: SimulationManager):
        self.manager = sim_manager

    def _get_testable(self):
        tested_pos_too_recently = (
            self.manager.tested_vector
            & self.manager.tested_positive_vector
            & (
                self.manager.current_step - self.manager.date_of_last_test
                < self.manager.consts.testing_gap_after_positive_test
            )
        )

        tested_neg_too_recently = (
            self.manager.tested_vector
            & np.logical_not(self.manager.tested_positive_vector)
            & (
                self.manager.current_step - self.manager.date_of_last_test
                < self.manager.consts.testing_gap_after_negative_test
            )
        )

        return np.logical_not(tested_pos_too_recently | tested_neg_too_recently) & self.manager.living_agents_vector

    def testing_step(self, test: DetectionTest, num_of_tests, priorities: List[Callable[[Agent], bool]]):
        # Who can to be tested
        want_to_be_tested = np.random.random(len(self.manager.agents)) < self.manager.test_willingness_vector
        can_be_tested = self._get_testable()
        test_candidates = want_to_be_tested & can_be_tested

        test_candidates_inds = set(np.flatnonzero(test_candidates))
        tested: List[PendingTestResult] = []

        if len(test_candidates_inds) < num_of_tests:
            # There are more tests than candidates. Don't check the priorities
            for ind in test_candidates_inds:
                tested.append(test.test(self.manager.agents[ind]))
                num_of_tests -= 1
        else:
            for priority_lambda in list(priorities):
                # First test the prioritized candidates
                for ind in np.random.permutation(list(test_candidates_inds)):
                    # permute the indices so we won't always test the lower indices
                    if priority_lambda(self.manager.agents[ind]):
                        tested.append(test.test(self.manager.agents[ind]))
                        test_candidates_inds.remove(ind)  # Remove so it won't be tested again
                        num_of_tests -= 1

                        if num_of_tests == 0:
                            return tested

            # Test the low prioritized now
            num_of_low_priority_to_test = min(num_of_tests, len(test_candidates_inds))
            low_priority_tested = [
                test.test(self.manager.agents[ind])
                for ind in np.random.permutation(list(test_candidates_inds))[:num_of_low_priority_to_test]
            ]
            tested += low_priority_tested
            num_of_tests -= len(low_priority_tested)

        # There are some tests left. Choose randomly from outside the pool
        test_leftovers_candidates_inds = np.flatnonzero(can_be_tested & np.logical_not(want_to_be_tested))
        will_be_tested_inds = np.random.choice(
            test_leftovers_candidates_inds, min(num_of_tests, len(test_leftovers_candidates_inds)), replace=False
        )

        for ind in will_be_tested_inds:
            tested.append(test.test(self.manager.agents[ind]))
            num_of_tests -= 1

        return tested
