"""Compute resources - BEFORE graph-refs."""

from dataclasses import dataclass

__all__ = ["SecurityGroup", "Instance"]


@dataclass
class SecurityGroup:
    name: str
    network_id: str  # Problem: just a string


@dataclass
class Instance:
    name: str
    subnet_id: str  # Problem: just a string
    security_group_id: str  # Problem: just a string
