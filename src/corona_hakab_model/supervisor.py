# flake8: noqa flake8 doesn't support named expressions := so for now we have to exclude this file for now:(

from __future__ import annotations

import os
from datetime import datetime
from abc import ABC, abstractmethod
from bisect import bisect
from functools import lru_cache
from typing import Any, Callable, List, NamedTuple, Sequence

import manager
import numpy as np
import csv

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from state_machine import State


class SimulationProgression:
    """
    records statistics about the simulation.
    """

    # todo I want the supervisor to decide when the simulation ends
    # todo record write/read results as text

    def __init__(self, supervisables: Sequence[Supervisable], manager: "manager.SimulationManager"):
        self.supervisables = supervisables
        self.manager = manager

    def snapshot(self, manager):
        for s in self.supervisables:
            s.snapshot(manager)

    def dump(self):
        output_folder = os.path.join(os.path.split(os.path.dirname(os.path.realpath(__file__)))[0], "output")

        with open(os.path.join(output_folder, datetime.now().strftime("%Y%m%d-%H%M%S") + ".csv"), 'w',
                  newline="") as output_file:
            published_data = [v.publish() for v in self.supervisables]
            csv_writer = csv.writer(output_file)
            # write data rows
            for i in range(self.manager.consts.total_steps + 1):
                row = [i]
                if i == 0:  # header row
                    row = ["days"]
                for data in published_data:
                    # first column is always the #day
                    row = row + data[i][1:]
                csv_writer.writerow(row)
    # todo stacked_plot


class Supervisable(ABC):
    @abstractmethod
    def snapshot(self, manager: "manager.SimulationManager"):
        pass

    @abstractmethod
    def publish(self):
        pass

    # todo is_finished
    # todo supervisables should be able to keep the manager running if they want

    @abstractmethod
    def name(self) -> str:
        pass

    @classmethod
    @lru_cache
    def coerce(cls, arg, manager: "manager.SimulationManager") -> Supervisable:
        if isinstance(arg, str):
            return _StateSupervisable(manager.medical_machine[arg])
        if isinstance(arg, cls):
            return arg
        if isinstance(arg, Callable):
            return arg(manager)
        raise TypeError

    class State:

        class Current:
            def __init__(self, name) -> None:
                self.name = name

            def __call__(self, m):
                return _StateSupervisable(m.medical_machine[self.name])

        class TotalSoFar:
            def __init__(self, name) -> None:
                self.name = name

            def __call__(self, m):
                return _StateTotalSoFarSupervisable(m.medical_machine[self.name])

        class AddedPerDay:
            def __init__(self, name) -> None:
                self.name = name

            def __call__(self, m):
                diff_sup = _DiffSupervisable(_StateTotalSoFarSupervisable(m.medical_machine[self.name]))
                return _NameOverrideSupervisable(diff_sup, "New " + self.name)

    class Delayed(NamedTuple):
        arg: Any
        delay: int

        def __call__(self, m):
            return _DelayedSupervisable(Supervisable.coerce(self.arg, m), self.delay)

    class Diff(NamedTuple):
        arg: Any

        def __call__(self, m):
            return _DiffSupervisable(Supervisable.coerce(self.arg, m))

    class Stack:
        def __init__(self, *args):
            self.args = args

        def __call__(self, m):
            return _StackedFloatSupervisable([Supervisable.coerce(a, m) for a in self.args])

    class Sum:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def __call__(self, m):
            return _SumSupervisable([Supervisable.coerce(a, m) for a in self.args], **self.kwargs)

    class R0:
        def __init__(self):
            pass

        def __call__(self, m):
            return _EffectiveR0Supervisable()

    class NewCasesCounter:
        def __init__(self):
            pass

        def __call__(self, manager):
            return _NewInfectedCount()

    class GrowthFactor:
        def __init__(self, sum_supervisor: "Sum", new_infected_supervisor: "NewCasesCounter"):
            self.new_infected_supervisor = new_infected_supervisor
            self.sum_supervisor = sum_supervisor

        def __call__(self, m):
            return _GrowthFactor(
                Supervisable.coerce(self.new_infected_supervisor, m), Supervisable.coerce(self.sum_supervisor, m)
            )


SupervisableMaker = Callable[[Any], Supervisable]


class ValueSupervisable(Supervisable):
    def __init__(self):
        self.snapshots = {}

    @abstractmethod
    def get(self, manager: "manager.SimulationManager"):
        pass

    def snapshot(self, manager: "manager.SimulationManager"):
        self.snapshots[manager.current_step] = self.get(manager)

    def publish(self):
        return [["", self.name()]] + ([list(z[0]) for z in zip(self.snapshots.items())])


class LambdaValueSupervisable(ValueSupervisable):
    def __init__(self, name: str, lam: Callable):
        super().__init__()
        self._name = name
        self.lam = lam

    def name(self) -> str:
        return self._name

    def get(self, manager) -> float:
        return self.lam(manager)


class _StateSupervisable(ValueSupervisable):
    def __init__(self, state):
        super().__init__()
        self.state = state

    def get(self, manager: "manager.SimulationManager") -> float:
        return self.state.agent_count

    def name(self) -> str:
        return self.state.name


class _StateTotalSoFarSupervisable(ValueSupervisable):
    def __init__(self, state: State):
        super().__init__()
        self.state = state
        self.__name = state.name + " So Far"

    def get(self, manager: "manager.SimulationManager") -> float:
        return len(self.state.ever_visited)

    def name(self) -> str:
        return self.__name


class _DelayedSupervisable(ValueSupervisable):
    def __init__(self, inner: ValueSupervisable, delay: int):
        super().__init__()
        self.inner = inner
        self.delay = delay

    def get(self, manager: "manager.SimulationManager") -> float:
        desired_date = manager.current_step - self.delay
        time_values = np.sort(self.inner.snapshots.keys())  # TODO: Assume sorted somehow?
        desired_index = bisect(time_values, desired_date)
        if desired_index >= len(time_values):
            return np.nan
        return self.inner.snapshots[desired_index]

    def name(self) -> str:
        return self.inner.name() + f" + {self.delay} days"

    def names(self):
        return [n + f" + {self.delay} days" for n in self.inner.names()]

    def snapshot(self, manager: "manager.SimulationManager"):
        self.inner.snapshot(manager)
        super().snapshot(manager)


class _NameOverrideSupervisable(ValueSupervisable):
    def __init__(self, inner: ValueSupervisable, name: str):
        super().__init__()
        self.__name = name
        self.inner = inner

    def get(self, manager: "manager.SimulationManager"):
        return self.inner.get(manager)

    def snapshot(self, manager: "manager.SimulationManager"):
        self.inner.snapshot(manager)
        super().snapshot(manager)

    def publish(self):
        return super().publish()

    def name(self) -> str:
        return self.__name


class _DiffSupervisable(ValueSupervisable):
    def __init__(self, inner: ValueSupervisable):
        super().__init__()
        self.inner = inner

    def get(self, manager: "manager.SimulationManager") -> float:
        if (manager.current_step - 1) not in self.inner.snapshots:
            return 0
        return self.inner.snapshots[manager.current_step] - self.inner.snapshots[manager.current_step - 1]

    def snapshot(self, manager: "manager.SimulationManager"):
        self.inner.snapshot(manager)
        super().snapshot(manager)

    def name(self) -> str:
        return self.inner.name() + " diff"


class VectorSupervisable(ValueSupervisable, ABC):
    @abstractmethod
    def names(self):
        pass

    def _to_ys(self):
        raise NotImplementedError('Need to convert (.x and .y) notation to the new (.snapshots) notation')
        n = len(self.y[0])
        return [[v[i] for v in self.y] for i in range(n)]

    def publish(self):
        return [["", self.names()]] + ([[z[0]] + z[1] for z in zip(self.snapshots.items())])


class _StackedFloatSupervisable(VectorSupervisable):
    def __init__(self, inners: List[ValueSupervisable]):
        super().__init__()
        self.inners = inners

    def get(self, manager: "manager.SimulationManager"):
        return [i.get(manager) for i in self.inners]

    def name(self) -> str:
        return "Stacked (" + ", ".join(n.name() for n in self.inners) + ")"

    def names(self):
        return [i.name() for i in self.inners]


class _SumSupervisable(ValueSupervisable):
    def __init__(self, inners: List[ValueSupervisable], **kwargs):
        super().__init__()
        self.inners = inners
        self.kwargs = kwargs

    def get(self, manager: "manager.SimulationManager") -> float:
        return sum(s.get(manager) for s in self.inners)

    def names(self):
        return ["Total(" + ", ".join(names) + ")" for names in zip(*(i.names() for i in self.inners))]

    def name(self) -> str:
        if "name" in self.kwargs:
            return self.kwargs["name"]
        return "Total(" + ", ".join(n.name() for n in self.inners)


# todo this is broken. needs adaptation to parasymbolic matrix
class _EffectiveR0Supervisable(ValueSupervisable):
    def __init__(self):
        super().__init__()

    def get(self, manager) -> float:
        # note that this calculation is VARY heavy
        suseptable_indexes = np.flatnonzero(manager.susceptible_vector)
        # todo someone who knows how this works fix it
        return (
                np.sum(1 - np.exp(manager.matrix[suseptable_indexes].data))
                * manager.update_matrix_manager.total_contagious_probability
                / len(manager.agents)
        )

    def name(self) -> str:
        return "effective R"


class _NewInfectedCount(ValueSupervisable):
    def __init__(self):
        super().__init__()

    def get(self, manager) -> float:
        return manager.new_sick_counter

    def name(self) -> str:
        return "new infected"


class _GrowthFactor(ValueSupervisable):
    def __init__(self, new_infected_supervisor, sum_supervisor):
        super().__init__()
        self.new_infected_supervisor = new_infected_supervisor
        self.sum_supervisor = sum_supervisor

    def get(self, manager) -> float:
        new_infected = self.new_infected_supervisor.get(manager)
        sum = self.sum_supervisor.get(manager)
        if sum == 0:
            return np.nan
        return new_infected / sum

    def name(self) -> str:
        return "growth factor"
