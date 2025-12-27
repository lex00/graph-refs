"""Compute resources - AFTER with graph-refs."""

from dataclasses import dataclass
from graph_refs import Ref

from .network import Network, Subnet

__all__ = ["SecurityGroup", "Instance"]


@dataclass
class SecurityGroup:
    name: str
    network: Ref[Network]  # Typed reference


@dataclass
class Instance:
    name: str
    subnet: Ref[Subnet]  # Typed reference
    security_group: Ref[SecurityGroup]  # Typed reference
