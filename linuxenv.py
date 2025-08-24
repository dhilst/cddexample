from __future__ import annotations
from typing import Any, final, Sequence, Type, Mapping
import json
from subprocess import check_output

def sh(*args, **kwargs) -> Sequence[str]:
    return check_output(*args, **kwargs, shell=True, universal_newlines=True).splitlines()

from main import Application, Config, Environment, Component, Subconfig, Action

class Command(str, Action):
    pass
    

@final
class LinuxEnv(Environment[Command]):
    def probe(self, namespace: str) -> Subconfig:
        if namespace == "packages":
            return Subconfig({"packages": set(sh("rpm -qa"))}) # type: ignore

        raise RuntimeError(f"Invalid namespace: {namespace}")

    def apply(self, actions: Sequence[str]) -> None:
        for action in actions:
            print(f"Running {action}");
            sh(action)

class LinuxComponent(Component[LinuxEnv]):
    def __init__(self, config: Config):
        self.config = config

    def subconfig(self) -> Subconfig:
        return self.config[self.namespace]

    def dependencies(self) -> Sequence[Component[LinuxEnv]]:
        if not hasattr(self, "_dependencies"):
            self._dependencies = [D(self.config) for D in self.deps]
        return self._dependencies



@final
class Network(LinuxComponent):
    namespace = "network"

    def probe(self, env: LinuxEnv) -> Sequence[Command]:
        subconfig = self.subconfig()
        currentstate = env.probe(self.namespace)
        deltastate = subconfig - currentstate
        commands = []
        for key, value in deltastate.items():
            commands.append(self.to_command(key, value))

        return commands

    def to_command(self, key: str, value: Any) -> Command:
        if key == "hostname":
            return Command(f"hostnamectl {value}")
        raise ValueError(f"Invalid key {key}")



@final
class Aider(LinuxComponent):
    namespace = "aider"

    def probe(self, env: LinuxEnv):
        subconfig = self.subconfig()
        installed_pkgs: set[str] = env.probe("packages")["packages"] # type: ignore
        to_install_pkgs = set(subconfig.get("packages", [])) - installed_pkgs
        return [Command(f"dnf install -y {pkg}") for pkg in to_install_pkgs]


@final
class MyApp(Application[LinuxEnv]):
    deps = [Network, Aider]

def main():
    app = MyApp("linux.toml")

    env = LinuxEnv()
    app.run_all(env)
