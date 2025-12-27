"""Network resources - BEFORE graph-refs."""

from dataclasses import dataclass

__all__ = ["Network", "Subnet"]


@dataclass
class Network:
    name: str
    cidr: str


@dataclass
class Subnet:
    name: str
    cidr: str
    network_id: str  # Problem: just a string, no type safety
