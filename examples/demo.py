#!/usr/bin/env python3
"""Demo: What graph-refs Can Do Today

This example demonstrates the CURRENT capabilities of graph-refs,
with comments explaining what additional tooling could enable.

Run with: python examples/demo.py
"""

from dataclasses import dataclass, field
from typing import Any

from graph_refs import Ref, Attr, RefList, get_refs, get_dependencies, RefInfo


# =============================================================================
# PART 1: A Simple Infrastructure Decorator
# =============================================================================
#
# This decorator demonstrates how a framework would USE graph-refs.
# graph-refs provides the type markers and introspection.
# The framework provides the decorator, registry, and serialization.

_registry: dict[str, type] = {}


def infra(cls: type) -> type:
    """A minimal infrastructure decorator that registers classes.

    A real framework would add:
    - Serialization to CloudFormation/Terraform/etc.
    - Validation of required fields
    - Reference resolution at serialization time

    graph-refs enables the framework to DISCOVER references automatically
    using get_refs() instead of manually tracking them.
    """
    # Register the class
    _registry[cls.__name__] = cls

    # Analyze references using graph-refs introspection
    refs = get_refs(cls)

    # Store reference metadata on the class for later use
    cls._refs = refs  # type: ignore
    cls._dependencies = get_dependencies(cls)  # type: ignore

    return cls


# =============================================================================
# PART 2: Define Resources with Typed References
# =============================================================================
#
# These type annotations work TODAY with graph-refs.
# Type checkers (mypy, pyright) see Ref[Network] as a valid generic type.
# The get_refs() function can extract reference information at runtime.


@infra
@dataclass
class Network:
    """A virtual network resource."""
    name: str
    cidr: str = "10.0.0.0/16"


@infra
@dataclass
class Subnet:
    """A subnet within a network.

    The `network` field uses Ref[Network] to indicate this subnet
    references a Network resource. This is:

    WORKING TODAY:
    - Type checkers understand Ref[Network] as a generic type
    - get_refs(Subnet) discovers this reference automatically
    - get_dependencies(Subnet) returns {Network}

    WOULD REQUIRE ADDITIONAL TOOLING:
    - Type checker enforcing that only Network classes are assigned
    - IDE autocomplete showing only Network resources
    - Automatic serialization to {"Ref": "NetworkName"}
    """
    name: str
    cidr: str
    network: Ref[Network]  # <-- Typed reference annotation


@infra
@dataclass
class SecurityGroup:
    """A security group attached to a network."""
    name: str
    network: Ref[Network]
    ingress_ports: list[int] = field(default_factory=list)


@infra
@dataclass
class Instance:
    """A compute instance with multiple dependencies.

    Demonstrates:
    - Multiple Ref[T] fields pointing to different resource types
    - get_dependencies() can compute transitive dependencies
    """
    name: str
    subnet: Ref[Subnet]
    security_group: Ref[SecurityGroup]
    instance_type: str = "t3.micro"


# =============================================================================
# PART 3: Introspection in Action (WORKS TODAY)
# =============================================================================

def demo_introspection() -> None:
    """Demonstrate what graph-refs introspection can do TODAY."""

    print("=" * 70)
    print("WORKING TODAY: Reference Introspection with graph-refs")
    print("=" * 70)

    # 1. Discover references from type annotations
    print("\n1. get_refs() extracts reference fields from annotations:\n")

    for cls in [Network, Subnet, SecurityGroup, Instance]:
        refs = get_refs(cls)
        print(f"   {cls.__name__}:")
        if refs:
            for name, info in refs.items():
                print(f"      .{name}: Ref[{info.target.__name__}]")
        else:
            print("      (no references)")

    # 2. Compute dependency graphs
    print("\n2. get_dependencies() computes the dependency graph:\n")

    for cls in [Network, Subnet, SecurityGroup, Instance]:
        deps = get_dependencies(cls, transitive=False)
        trans_deps = get_dependencies(cls, transitive=True)

        direct = [d.__name__ for d in deps] or ["none"]
        transitive = [d.__name__ for d in trans_deps] or ["none"]

        print(f"   {cls.__name__}:")
        print(f"      direct:     {direct}")
        print(f"      transitive: {transitive}")

    # 3. The decorator stored this info on the class
    print("\n3. The @infra decorator used graph-refs to store metadata:\n")

    print(f"   Instance._refs = {{")
    for name, info in Instance._refs.items():  # type: ignore
        print(f"      '{name}': RefInfo(target={info.target.__name__}, ...)")
    print(f"   }}")
    print(f"   Instance._dependencies = {{{', '.join(d.__name__ for d in Instance._dependencies)}}}")  # type: ignore


# =============================================================================
# PART 4: What a Framework Would Add (NOT in graph-refs)
# =============================================================================

def demo_framework_usage() -> None:
    """Show how a framework would BUILD ON graph-refs.

    graph-refs provides: type markers + introspection
    Frameworks provide: decorators + serialization + validation
    """

    print("\n" + "=" * 70)
    print("FRAMEWORK TERRITORY: What gets built on top of graph-refs")
    print("=" * 70)

    print("""
    A framework like an infrastructure DSL would add:

    1. SERIALIZATION - Convert resources to target format:

       Instance -> {
           "Type": "AWS::EC2::Instance",
           "Properties": {
               "SubnetId": {"Ref": "ProdSubnet"},
               "SecurityGroupIds": [{"Ref": "WebSG"}]
           }
       }

    2. VALIDATION - Check references point to valid resources

    3. ORDERING - Use get_dependencies() for creation order

    4. THE NO-PARENS PATTERN - With a custom decorator:

       @infra
       class MyInstance:
           subnet = ProdSubnet        # Class reference, not Ref[T] annotation
           security_group = WebSG     # Decorator detects and processes these

       This pattern is POSSIBLE today with metaclasses/decorators,
       but type checkers won't understand it without:
       - stdlib Ref[T] type, or
       - @dataclass_transform extensions (proposed in docs/RATIONALE.md)
    """)


# =============================================================================
# PART 5: Topological Sort Example (WORKS TODAY)
# =============================================================================

def demo_topological_sort() -> None:
    """Demonstrate computing creation order from dependencies."""

    print("\n" + "=" * 70)
    print("WORKING TODAY: Topological Sort for Creation Order")
    print("=" * 70)

    # Simple topological sort using get_dependencies
    resources = list(_registry.values())
    sorted_resources: list[type] = []
    remaining = set(resources)

    while remaining:
        # Find resources whose dependencies are all satisfied
        ready = [
            r for r in remaining
            if get_dependencies(r).issubset(set(sorted_resources))
        ]

        if not ready:
            # Circular dependency - just take one
            ready = [next(iter(remaining))]

        for r in ready:
            sorted_resources.append(r)
            remaining.remove(r)

    print("\n   Creation order (respecting dependencies):\n")
    for i, cls in enumerate(sorted_resources, 1):
        deps = get_dependencies(cls)
        dep_str = f" (after {', '.join(d.__name__ for d in deps)})" if deps else ""
        print(f"   {i}. {cls.__name__}{dep_str}")


# =============================================================================
# RUN THE DEMO
# =============================================================================

if __name__ == "__main__":
    demo_introspection()
    demo_framework_usage()
    demo_topological_sort()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
    graph-refs provides TODAY:
    ✓ Ref[T], Attr[T, "name"], RefList[T], RefDict[K,V], ContextRef["name"]
    ✓ get_refs(cls) - extract reference metadata from annotations
    ✓ get_dependencies(cls, transitive=True) - compute dependency graph
    ✓ Works with mypy/pyright as valid generic types

    Frameworks build on this to add:
    → Decorators that process resources
    → Serialization to target formats
    → The no-parens pattern (network = MyNetwork)
    → Validation and error reporting

    See docs/RATIONALE.md for design principles.
    See docs/PATTERN.md for the full DSL pattern guide.
    """)
