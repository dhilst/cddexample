from __future__ import annotations
from typing import final, Sequence, Type, Mapping
import tomllib
from pathlib import Path
from collections import defaultdict
import pprint
import json

from main import Application, Config, Environment, Component, Subconfig

@final
class DictEnv(Environment[str]):
    def __init__(self):
        self._current_state = defaultdict(dict)

    def state(self, key: str) -> Subconfig:
        return Subconfig(self._current_state[key])

    def probe(self, namespace: str) -> Subconfig:
        return self.state(namespace)

    def apply(self, actions: Sequence[str]) -> None:
        for action in actions:
            namespace, key, value = action.split(":")
            self.applyone(namespace, key, value)

    def applyone(self, namespace: str, key: str, value: str):
        self._current_state[namespace][key] = value

    def __repr__(self):
        return pprint.pformat(self._current_state)

    def to_dict(self) -> Mapping[str, Mapping[str, str]]:
        return self._current_state

class BaseComponent(Component[DictEnv]):
    def __init__(self, config: Config):
        self.config = config
        self._dependencies = [Dep(config) for Dep in self.deps]

    def probe(self, env: DictEnv) -> Sequence[str]:
        substate = self.subconfig()
        envstate = env.probe(self.namespace)
        deltastate = substate - envstate
        return [f"{self.namespace}:{key}:{value}"
            for key, value in deltastate.items()]

    def subconfig(self) -> Subconfig:
        return Subconfig(self.config.get(self.namespace, {}))

    def dependencies(self) -> Sequence[Component[DictEnv]]:
        return self._dependencies


@final
class Network(BaseComponent):
    namespace = "network"
    deps = []


@final
class SSHD(BaseComponent):
    namespace = "sshd"
    deps = [Network]

@final
class MyApp(Application[DictEnv]):
    deps = [SSHD]

def main():
    app = MyApp("main.toml")

    env = DictEnv()
    app.run_all(env)
    print(json.dumps(env.to_dict(), indent=2))

    env2 = DictEnv()
    app.run_in_series(env2)
    print(json.dumps(env2.to_dict(), indent=2))

if __name__ == "__main__":
    main()
    

