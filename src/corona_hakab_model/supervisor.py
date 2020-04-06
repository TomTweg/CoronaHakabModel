# flake8: noqa flake8 doesn't support named expressions := so for now we have to exclude this file for now:(

from __future__ import annotations

from abc import ABC, abstractmethod
from bisect import bisect
from functools import lru_cache
from typing import Any, Callable, List, NamedTuple, Sequence, Tuple

import manager
import matplotlib_set_backend
import numpy as np

try:
    # plt is optional
    from matplotlib import pyplot as plt
except ImportError:
    pass


class Supervisor:
    """
    records and plots statistics about the simulation.
    """

    # todo I want the supervisor to decide when the simulation ends
    # todo record write/read results as text

    def __init__(self, supervisables: Sequence[Supervisable], manager: "manager.SimulationManager"):
        self.supervisables = supervisables
        self.manager = manager

    def snapshot(self, manager):
        for s in self.supervisables:
            s.snapshot(manager)

    # todo stacked_plot

    def plot(self, max_scale: bool = True, auto_show: bool = True, save: bool = True):
        output_dir = "../output/"
        total_size = len(self.manager.agents)
        title = f"Infections vs. Days, size={total_size:,}"

        fig, ax = plt.subplots()

        # visualization
        # TODO: should be better
        if max_scale:
            ax.set_ylim((0, total_size))

        text_height = ax.get_ylim()[-1] / 2
        # policies
        if self.manager.consts.active_isolation:
            title += (
                f"\napplying lockdown from day {self.manager.consts.stop_work_days} "
                f"to day {self.manager.consts.resume_work_days}"
            )
            ax.axvline(x=self.manager.consts.stop_work_days, color="#0000ff")
            ax.text(
                self.manager.consts.stop_work_days + 2,
                text_height,
                f"day {self.manager.consts.stop_work_days} - pause all work",
                rotation=90,
            )
            ax.axvline(x=self.manager.consts.resume_work_days, color="#0000cc")
            ax.text(
                self.manager.consts.resume_work_days + 2,
                text_height,
                f"day {self.manager.consts.resume_work_days} - resume all work",
                rotation=90,
            )
        if self.manager.consts.home_isolation_sicks:
            title += (
                f"\napplying home isolation for confirmed cases " f"({self.manager.consts.caught_sicks_ratio} of cases)"
            )
        if self.manager.consts.full_isolation_sicks:
            title += (
                f"\napplying full isolation for confirmed cases " f"({self.manager.consts.caught_sicks_ratio} of cases)"
            )

        # plot parameters
        ax.set_title(title)
        ax.set_xlabel("days", color="#1C2833")
        ax.set_ylabel("people", color="#1C2833")

        ax.grid()

        for s in self.supervisables:
            s.plot(ax)
        ax.legend()

        # showing and saving the graph
        if save:
            fig.savefig(
                f"{output_dir}{total_size} agents, applying isolation = {self.manager.consts.active_isolation}, "
                f"max scale = {max_scale}"
            )
        if auto_show:
            plt.show()

    @staticmethod
    def static_plot(
        simulations_info: Sequence[Tuple["manager.SimulationManager", str, Sequence[str]]],
        title="comparing",
        save_name=None,
        max_height=-1,
        auto_show=True,
        save=True,
    ):
        """
        a static plot method, allowing comparison between multiple simulation runs
        :param simulations_info: a sequence of tuples, each representing a simulation. each simulation contains the manager, a pre-fix string and a sequence of syling strings. \
         note that the len of styling strings tuple must be the same as len of the simulation manager supervisables
        :param title: the title of the output graph
        :param save_name: how the simulation will be saved. if not entered, will be same as the title
        :param max_height: max hight to allow a ylim
        :param auto_show:
        :param save:
        :return:
        """

        output_dir = "../output/"
        if save_name is None:
            save_name = title
        fig, ax = plt.subplots()

        ax.set_title(title)
        ax.set_xlabel("days", color="#1C2833")
        ax.set_ylabel("people", color="#1C2833")

        for manager, prefix, styling in simulations_info:
            for supervisable, style in zip(manager.supervisor.supervisables, styling):
                supervisable.plot(ax, prefix, style)
        ax.legend()

        if max_height != -1:
            ax.set_ylim((0, max_height))

        if save:
            fig.savefig(output_dir + save_name + ".png")
        if auto_show:
            plt.show()

    def stack_plot(self, auto_show: bool = True):
        # todo plot and stack_plot share a lot of of components, they need to be unified
        fig, ax = plt.subplots()

        # plot parameters
        ax.set_xlabel("days", color="#1C2833")
        ax.set_ylabel("people", color="#1C2833")

        ax.grid()

        for s in self.supervisables:
            s.stacked_plot(ax)
        ax.legend()

        # showing and saving the graph
        if auto_show:
            plt.show()


class Supervisable(ABC):
    @abstractmethod
    def snapshot(self, manager: "manager.SimulationManager"):
        pass

    @abstractmethod
    def plot(self, ax):
        pass

    @abstractmethod
    def plot(self, ax, prefix="", style=""):
        pass

    @abstractmethod
    def stacked_plot(self, ax):
        pass

    # todo is_finished

    # todo supervisables should be able to keep the manager running if they want

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

    class Delayed(NamedTuple):
        arg: Any
        delay: int

        def __call__(self, m):
            return _DelayedSupervisable(Supervisable.coerce(self.arg, m), self.delay)

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
        self.x = []
        self.y = []

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def get(self, manager: "manager.SimulationManager"):
        pass

    @abstractmethod
    def stacked_plot(self, ax):
        pass

    @abstractmethod
    def plot(self, ax):
        pass

    def snapshot(self, manager: "manager.SimulationManager"):
        self.x.append(manager.current_step)
        self.y.append(self.get(manager))


class FloatSupervisable(ValueSupervisable):
    def plot(self, ax, prefix="", style=""):
        # todo preferred color/style?
        ax.plot(self.x, self.y, style, label=prefix + self.name())

    def stacked_plot(self, ax):
        return ax.stackplot(self.x, self.y, label=self.name())


class LambdaValueSupervisable(FloatSupervisable):
    def __init__(self, name: str, lam: Callable):
        super().__init__()
        self._name = name
        self.lam = lam

    def name(self) -> str:
        return self._name

    def get(self, manager) -> float:
        return self.lam(manager)


class _StateSupervisable(FloatSupervisable):
    def __init__(self, state):
        super().__init__()
        self.state = state

    def get(self, manager: "manager.SimulationManager") -> float:
        return self.state.agent_count

    def name(self) -> str:
        return self.state.name


class _DelayedSupervisable(ValueSupervisable):
    def __init__(self, inner: ValueSupervisable, delay: int):
        super().__init__()
        self.inner = inner
        self.delay = delay

    def get(self, manager: "manager.SimulationManager") -> float:
        desired_date = manager.current_step - self.delay
        desired_index = bisect(self.inner.x, desired_date)
        if desired_index >= len(self.inner.x):
            return np.nan
        return self.inner.y[desired_index]

    def name(self) -> str:
        return self.inner.name() + f" + {self.delay} days"

    def names(self):
        return [n + f" + {self.delay} days" for n in self.inner.names()]

    def plot(self, ax):
        return type(self.inner).plot(self, ax)

    def stacked_plot(self, ax):
        return type(self.inner).stacked_plot(self, ax)


class VectorSupervisable(ValueSupervisable, ABC):
    @abstractmethod
    def names(self):
        pass

    def _to_ys(self):
        n = len(self.y[0])
        return [[v[i] for v in self.y] for i in range(n)]

    def plot(self, ax):
        for n, y in zip(self.names(), self._to_ys()):
            return ax.plot(self.x, y, label=n)

    def stacked_plot(self, ax):
        ax.stackplot(self.x, *self._to_ys(), labels=list(self.names()))


class _StackedFloatSupervisable(VectorSupervisable):
    def __init__(self, inners: List[FloatSupervisable]):
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

    def plot(self, ax):
        return type(self.inners[0]).plot(self, ax)

    def stacked_plot(self, ax):
        return type(self.inners[0]).stacked_plot(self, ax)

    def name(self) -> str:
        if "name" in self.kwargs:
            return self.kwargs["name"]
        return "Total(" + ", ".join(n.name() for n in self.inners)


# todo this is broken. needs adaptation to parasymbolic matrix
class _EffectiveR0Supervisable(FloatSupervisable):
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


class _NewInfectedCount(FloatSupervisable):
    def __init__(self):
        super().__init__()

    def get(self, manager) -> float:
        return manager.new_sick_counter

    def name(self) -> str:
        return "new infected"


class _GrowthFactor(FloatSupervisable):
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
