"""
graph-refs: Typed graph references for Python dataclasses.

This module provides type markers for expressing references between dataclass
instances in graph-structured domains. It enables type checkers to verify
that relationships are correctly typed, while providing runtime introspection
for frameworks that need to analyze reference graphs.

Overview:
    The library provides five type markers for different reference patterns:

    - `Ref[T]`: Reference to an instance of type T
    - `Attr[T, "name"]`: Reference to a specific attribute of type T
    - `RefList[T]`: List of references to type T
    - `RefDict[K, V]`: Dictionary with reference values of type V
    - `ContextRef["name"]`: Reference to a context value

    And two introspection functions:

    - `get_refs(cls)`: Extract reference information from a class
    - `get_dependencies(cls)`: Compute the dependency graph

Installation:
    Install from PyPI::

        pip install graph-refs

Quick Start:
    Basic usage with dataclasses::

        from dataclasses import dataclass
        from graph_refs import Ref, Attr, get_refs, get_dependencies

        @dataclass
        class Network:
            cidr: str

        @dataclass
        class Subnet:
            network: Ref[Network]  # Reference to a Network
            cidr: str

        @dataclass
        class Instance:
            subnet: Ref[Subnet]
            role_arn: Attr[Role, "Arn"]  # Reference to Role's Arn attribute
            name: str

        # Extract reference information
        refs = get_refs(Subnet)
        print(refs["network"].target)  # <class 'Network'>

        # Compute dependencies
        deps = get_dependencies(Instance, transitive=True)
        print(deps)  # {<class 'Subnet'>, <class 'Network'>}

Use Cases:
    **Infrastructure-as-Code**::

        @infrastructure
        class Database:
            resource: RDSInstance
            vpc: Ref[MyVPC]
            security_groups: RefList[SecurityGroup]

    **Configuration Management**::

        @config
        class ServiceConfig:
            database: Ref[DatabaseConfig]
            cache: Ref[CacheConfig]

    **Entity Relationships**::

        @entity
        class Order:
            customer: Ref[Customer]
            items: RefList[Product]

    **Workflow Systems**::

        @task
        class ProcessData:
            depends_on: RefList[Task]
            output: Attr[Storage, "Path"]

Type Checker Support:
    All types work with mypy, pyright, and other type checkers::

        @dataclass
        class Subnet:
            network: Ref[Network]

        # Type checker catches this error:
        subnet = Subnet(network=MyBucket)  # Error: expected Network, got Bucket

Exports:
    Types:
        - `Ref`: Reference to a class
        - `Attr`: Reference to an attribute
        - `RefList`: List of references
        - `RefDict`: Dictionary with reference values
        - `ContextRef`: Reference to a context value

    Introspection:
        - `RefInfo`: Metadata about a reference field
        - `get_refs`: Extract references from a class
        - `get_dependencies`: Compute dependency graph

See Also:
    - `PHILOSOPHY.md`: Design principles behind this library
    - `docs/PEP_TYPING.md`: PEP proposal for stdlib inclusion
"""

from graph_refs._introspection import (
    RefInfo,
    get_dependencies,
    get_refs,
)
from graph_refs._types import (
    Attr,
    ContextRef,
    Ref,
    RefDict,
    RefList,
)

__all__ = [
    # Types
    "Ref",
    "Attr",
    "RefList",
    "RefDict",
    "ContextRef",
    # Introspection
    "RefInfo",
    "get_refs",
    "get_dependencies",
]

__version__ = "0.1.0"
