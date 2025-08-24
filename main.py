from __future__ import annotations
from collections import defaultdict, UserDict
import enum
from pathlib import Path
from typing import Mapping, Sequence, Mapping, Protocol, Type, Self, final, Iterator, Tuple, Final
import tomllib

class Subconfig(UserDict[str, str]):
    def __sub__(self, other: Subconfig):
        return Subconfig({k: v for k, v in self.items() if k not in other or v != other[k]})

    def __add__(self, other: Subconfig):
        return Subconfig({**self, **other})

type Config = Mapping[str, Subconfig]

class Action(Protocol):
    pass

class Environment[A: Action](Protocol):
    def probe(self, namespace: str) -> Subconfig: ...
    def apply(self, actions: Sequence[A]) -> None: ...

class Component[E: Environment](Protocol):
    namespace: str
    deps: list[Type[Component]] = []

    def __init__(self, Config): ...
    def probe(self, env: E) -> Sequence[Action]: ...
    def subconfig(self) -> Subconfig: ...
    def dependencies(self) -> Sequence[Component[E]]: ...

class Application[E: Environment](Protocol):
    deps: list[Type[Component]] = []
    _components: Sequence[Component]
    _config_path: Path
    _config: Config

    def __init__(self, config_path: str):
        self._config_path = Path(config_path)
        with self._config_path.open("rb") as f:
            self._config = tomllib.load(f)

    def config(self) -> Config:
        return self._config

    def components(self) -> Sequence[Component[E]]:
        if not hasattr(self, "_components"):
            self._components = [C(self.config()) for C in self.deps]
        return self._components

    def probeall(self, env: E) -> Sequence[Action]:
        actions = []
        for c in self.components():
            actions += [a for d in c.dependencies() for a in d.probe(env)]
            actions += [a for a in c.probe(env)]
        print(f"Probe all finished: {actions}")
        return actions

    def run_in_series(self, env: E) -> None:
        for c in self.components():
            for dep in c.dependencies():
                actions = dep.probe(env)
                print(f"Running dep {dep} for {c}: {actions}")
                env.apply(actions)
            actions = c.probe(env)
            print(f"Running {c}: {actions}")
            env.apply(actions)

    def run_all(self, env: E) -> None:
        actions = self.probeall(env)
        print("Running all ...")
        env.apply(actions)

