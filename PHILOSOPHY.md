# Design Philosophy

This document captures the vision and design principles behind `graph-refs`.

## The Problem

Dataclasses naturally model tree-structured data. But many domains require **graph structures** where objects reference each other:

```python
@dataclass
class Subnet:
    network: ???  # How do we express "reference to a Network"?
    cidr: str

@dataclass
class Network:
    subnets: list[???]  # How do we express "list of Subnet references"?
    name: str
```

Currently, there's no standard way to express these relationships with full type safety.

### Current Workarounds

**String identifiers** — No type safety:
```python
network_id: str  # Any string accepted, no validation
```

**Forward reference strings** — Type checker sees the class, not a reference:
```python
network: "Network"  # Ambiguous: is this the value or a reference?
```

**Custom wrapper types** — Verbose, no standardization:
```python
network: Ref[Network]  # Every library defines its own Ref
```

## The Vision

A standard set of type markers for graph references that:

1. **Type checkers understand** — Catch reference type errors at development time
2. **IDEs support** — Autocomplete valid reference targets
3. **Frameworks can introspect** — Build dependency graphs, serialize references
4. **Feel native** — Fit naturally alongside `list[T]`, `Optional[T]`, etc.

## Core Principles

### 1. Types as Documentation

`Ref[T]` expresses intent clearly:

```python
# Clear: This field references a Network
network: Ref[Network]

# Unclear: Is this a Network value or reference?
network: Network
```

The type annotation documents the relationship for humans, type checkers, and tools.

### 2. Zero Runtime Cost

Type markers should be nearly invisible at runtime:

```python
class Ref(Generic[T]):
    __slots__ = ()  # No instance data
```

All the value is at development time (type checking) and framework time (introspection). There's no runtime validation or overhead.

### 3. Introspection for Frameworks

Frameworks need to analyze reference graphs:

```python
# Framework builds dependency order from references
refs = get_refs(MyResource)
deps = get_dependencies(MyResource, transitive=True)
```

The introspection API enables frameworks without requiring them to parse type annotations themselves.

### 4. Compatibility First

Must work with existing tools:
- `get_type_hints()` — Standard introspection
- `get_origin()`, `get_args()` — Generic decomposition
- mypy, pyright — Type checker compatibility
- dataclasses, attrs, pydantic — Framework integration

### 5. Minimal Surface Area

Fewer, well-designed primitives are better than many specialized ones:

| Type | Purpose |
|------|---------|
| `Ref[T]` | Reference to T |
| `Attr[T, "name"]` | Reference to T's attribute |
| `RefList[T]` | List of references (convenience) |
| `RefDict[K, V]` | Dict with reference values (convenience) |
| `ContextRef["name"]` | Context value reference |

That's it. No `WeakRef`, `LazyRef`, `CircularRef`, etc. Frameworks can build those patterns on top of these primitives.

## The No-Parens Pattern

A key motivation is enabling "no-parens" reference patterns in DSLs:

```python
# With parens — ceremony
network = ref(MyNetwork)
role_arn = get_attr(MyRole, "Arn")

# Without parens — declaration
network = MyNetwork
role_arn = MyRole.Arn
```

`graph-refs` provides the type system foundation. DSL decorators can detect when a class attribute is assigned another decorated class and treat it as a `Ref[T]`.

## Relationship to Standards

### Building On

| PEP | Contribution |
|-----|--------------|
| PEP 484 | Type hints foundation |
| PEP 557 | Dataclasses |
| PEP 585 | Generic `Ref[T]` syntax |
| PEP 586 | Literal for `Attr[T, "name"]` |
| PEP 681 | `@dataclass_transform` for DSL decorators |

### Proposed Extensions

The companion PEP proposes:
- Standard `Ref[T]`, `Attr[T, name]` types
- `get_refs()`, `get_dependencies()` introspection
- Extensions to `@dataclass_transform` for reference-aware decorators

See [docs/PEP_TYPING.md](docs/PEP_TYPING.md) for the full proposal.

## Use Case Independence

`graph-refs` is **not** an infrastructure-as-code library. It's a general-purpose typing library useful for:

- **Infrastructure-as-Code** — Resources reference other resources
- **Configuration Management** — Configs reference other configs
- **Entity Relationships** — Entities reference other entities
- **Workflow Systems** — Tasks reference dependencies
- **Schema Definitions** — Fields reference other schemas

The library provides primitives. Domains build on them.

## What graph-refs Is Not

### Not a Validation Library

No runtime type checking:
```python
# graph-refs does NOT do this
subnet = Subnet(network="wrong-type")  # No runtime error
```

Validation belongs in frameworks or type checkers, not in type markers.

### Not a Serialization Library

No JSON/YAML output:
```python
# graph-refs does NOT do this
subnet.to_json()  # No such method
```

Serialization is domain-specific. A CloudFormation reference serializes differently than a Kubernetes reference.

### Not a Graph Database

No query or traversal API:
```python
# graph-refs does NOT do this
graph.find_all(Subnet).where(network=MyNetwork)
```

Graph operations belong in frameworks that manage the full object graph.

## The Path to Stdlib

The goal is inclusion in `typing_extensions` and eventually `typing`:

1. **Prove value** — Adoption in real frameworks
2. **Validate design** — Type checker implementations
3. **Stabilize API** — No breaking changes needed
4. **Write PEP** — Formal proposal with community input
5. **Integration** — `typing_extensions` first, then `typing`

This library is the proving ground for that journey.

## Summary

`graph-refs` provides:
- **Type markers** for expressing reference relationships
- **Introspection** for frameworks to analyze reference graphs
- **Type checker support** for development-time safety
- **Zero runtime cost** through minimal implementation

It does not provide validation, serialization, or graph operations. Those belong in the frameworks that build on these primitives.
