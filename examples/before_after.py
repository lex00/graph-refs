"""Before/After: Typed Graph References

This example shows how graph-refs addresses limitations in expressing
resource dependencies with type safety.

Run with: python examples/before_after.py
"""

from dataclasses import dataclass
from typing import Any

# =============================================================================
# BEFORE: Without graph-refs
# =============================================================================

# Problem 1: String-based references - no type safety
@dataclass
class SubnetBefore:
    cidr: str
    network_id: str  # Just a string - any value accepted


@dataclass
class NetworkBefore:
    cidr: str
    name: str


# This compiles fine but is wrong - "my-bucket" is not a network!
bad_subnet = SubnetBefore(cidr="10.0.1.0/24", network_id="my-bucket")

# Problem 2: No way to introspect dependencies
def get_dependencies_before(cls: type) -> set[type]:
    """We'd have to parse field names or use conventions."""
    # How do we know network_id refers to NetworkBefore?
    # We can't - it's just a string field.
    return set()  # No way to determine this automatically


# Problem 3: Forward references don't express "reference" semantics
@dataclass
class SubnetForwardRef:
    cidr: str
    network: "NetworkBefore"  # Type checker sees this as the class itself


# =============================================================================
# AFTER: With graph-refs
# =============================================================================

from graph_refs import Ref, get_refs, get_dependencies


@dataclass
class Network:
    cidr: str
    name: str


@dataclass
class Subnet:
    cidr: str
    network: Ref[Network]  # Explicitly a REFERENCE to Network


# Benefit 1: Type safety - wrong types caught at development time
# subnet = Subnet(cidr="10.0.1.0/24", network=Bucket)  # Type error!

# Benefit 2: Introspection - frameworks can analyze the graph
refs = get_refs(Subnet)
print("References in Subnet:")
for name, info in refs.items():
    print(f"  {name}: -> {info.target.__name__}")

# Benefit 3: Dependency analysis
deps = get_dependencies(Subnet)
print(f"\nSubnet depends on: {[d.__name__ for d in deps]}")


# =============================================================================
# Real-world example: Instance with multiple dependencies
# =============================================================================

@dataclass
class SecurityGroup:
    name: str
    vpc: Ref[Network]


@dataclass
class Instance:
    name: str
    subnet: Ref[Subnet]
    security_group: Ref[SecurityGroup]


# Transitive dependency analysis
all_deps = get_dependencies(Instance, transitive=True)
print(f"\nInstance depends on (transitive): {[d.__name__ for d in all_deps]}")

# Output:
# References in Subnet:
#   network: -> Network
#
# Subnet depends on: ['Network']
#
# Instance depends on (transitive): ['Subnet', 'SecurityGroup', 'Network']
