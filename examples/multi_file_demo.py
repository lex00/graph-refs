"""Multi-file Before/After Demo

Demonstrates how graph-refs enables type-safe references across multiple files
with asterisk imports.

Run with: python examples/multi_file_demo.py
"""

print("=" * 60)
print("BEFORE: String-based references across files")
print("=" * 60)

# Import all resources with asterisk import
from multi_file_before import *

# Create resources - but references are just strings
prod_network = Network(name="prod-vpc", cidr="10.0.0.0/16")
prod_subnet = Subnet(
    name="prod-subnet",
    cidr="10.0.1.0/24",
    network_id="prod-vpc",  # Just a string - could be anything
)
prod_sg = SecurityGroup(
    name="prod-sg",
    network_id="prod-vpc",
)
prod_instance = Instance(
    name="web-server",
    subnet_id="prod-subnet",
    security_group_id="prod-sg",
)

print(f"Created: {prod_instance}")
print("\nProblems:")
print("  - network_id='prod-vpc' is just a string - no type checking")
print("  - Typo like 'prod-vp' would not be caught")
print("  - No way to automatically discover dependencies")
print("  - Refactoring is error-prone")

# Try to get dependencies - we can't!
print("\n  Dependency analysis: NOT POSSIBLE with strings")


print("\n" + "=" * 60)
print("AFTER: Typed references with graph-refs")
print("=" * 60)

# Import all resources with asterisk import
from multi_file_after import *
from graph_refs import get_refs, get_dependencies

# Now we can analyze the types themselves
print("\nReference analysis (no instances needed):")

for cls in [Subnet, SecurityGroup, Instance]:
    refs = get_refs(cls)
    if refs:
        print(f"\n  {cls.__name__} references:")
        for name, info in refs.items():
            print(f"    .{name} -> {info.target.__name__}")

# Compute full dependency graph
print("\n\nDependency graph:")
for cls in [Network, Subnet, SecurityGroup, Instance]:
    deps = get_dependencies(cls, transitive=True)
    dep_names = sorted(d.__name__ for d in deps) if deps else ["(none)"]
    print(f"  {cls.__name__} depends on: {dep_names}")

print("\nBenefits:")
print("  - Type checker catches wrong reference types")
print("  - IDE autocomplete works across files")
print("  - Automatic dependency discovery")
print("  - Safe refactoring with type checker support")
