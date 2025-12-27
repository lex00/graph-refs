"""Network resources - AFTER with graph-refs."""

from dataclasses import dataclass
from graph_refs import Ref

__all__ = ["Network", "Subnet"]


@dataclass
class Network:
    name: str
    cidr: str


@dataclass
class Subnet:
    name: str
    cidr: str
    network: Ref[Network]  # Typed reference - must be a Network
