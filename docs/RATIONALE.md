# Design Rationale: Typed Graph References

This document explains the design decisions behind graph-refs and explores potential directions for Python's typing system.

## The Problem

Dataclasses naturally model tree-structured data, but many domains require graph structures where objects reference each other:

```python
@dataclass
class Subnet:
    network: ???  # Reference to a Network instance
    cidr: str

@dataclass
class Network:
    subnets: list[???]  # References to Subnet instances
    cidr: str
```

Currently, there's no standard way to express "this field references another dataclass" with full type safety.

### Current Workarounds

**String identifiers:**
```python
@dataclass
class Subnet:
    network_id: str  # No type safety — any string accepted
```

**Forward references:**
```python
@dataclass
class Subnet:
    network: "Network"  # Type checker sees this as the class, not a reference
```

**Custom wrapper types:**
```python
class Ref(Generic[T]):
    def __init__(self, target: type[T]): ...

@dataclass
class Subnet:
    network: Ref[Network]  # Works, but verbose and no attribute access support
```

### What graph-refs Provides

A standardized `Ref[T]` type that:

1. Enables type checkers to verify reference targets
2. Supports IDE autocomplete for valid reference targets
3. Enables static graph analysis (dependency detection, cycle detection)
4. Can integrate with `@dataclass_transform` for DSL decorators

### Use Cases

**Infrastructure-as-Code:**
```python
@infrastructure
class Database:
    resource: RDSInstance
    vpc: Ref[MyVPC]  # Must reference a VPC-type resource
    security_groups: list[Ref[SecurityGroup]]
```

**Configuration Management:**
```python
@config
class ServiceConfig:
    database: Ref[DatabaseConfig]
    cache: Ref[CacheConfig]
```

**Entity Relationships:**
```python
@entity
class Order:
    customer: Ref[Customer]
    items: list[Ref[Product]]
```

## Type Specifications

### `Ref[T]` — Typed Reference

`Ref[T]` represents a reference to an instance of type `T`:

```python
from graph_refs import Ref

@dataclass
class Network:
    cidr: str

@dataclass
class Subnet:
    network: Ref[Network]  # Reference to a Network
    cidr: str
```

#### Type Checker Behavior

- `Ref[T]` is assignable from:
  - The class `T` itself (for implicit reference patterns)
  - An instance of `Ref[T]`
  - Any subclass of `T` (covariant)

- `Ref[T]` is NOT assignable from:
  - Unrelated types
  - `str` (unless explicitly typed as `Ref[T] | str`)

```python
subnet = Subnet(
    network=MyNetwork,      # OK — class reference
    cidr="10.0.1.0/24"
)

subnet = Subnet(
    network=MyBucket,       # Type error — Bucket is not Network
    cidr="10.0.1.0/24"
)
```

#### Runtime Representation

At runtime, `Ref[T]` is equivalent to `type[T] | T`. The generic parameter is erased but available via `__origin__` and `__args__`:

```python
from typing import get_origin, get_args

field_type = Ref[Network]
get_origin(field_type)  # Ref
get_args(field_type)    # (Network,)
```

### `Attr[T, name]` — Typed Attribute Reference

`Attr[T, name]` represents a reference to a specific attribute of type `T`:

```python
from graph_refs import Attr
from typing import Literal

@dataclass
class Role:
    name: str
    Arn: ClassVar[str]
    RoleId: ClassVar[str]

@dataclass
class Function:
    role_arn: Attr[Role, Literal["Arn"]]  # Reference to Role's Arn attribute
```

#### Type Checker Behavior

- `Attr[T, Literal["name"]]` is assignable from:
  - `T.name` (class attribute access)
  - An instance of `Attr[T, Literal["name"]]`

- Type checkers should verify that `T` has an attribute `name`

```python
function = Function(
    role_arn=MyRole.Arn,     # OK — Role has Arn attribute
)

function = Function(
    role_arn=MyRole.Xyz,     # Type error — Role has no Xyz attribute
)

function = Function(
    role_arn=MyBucket.Arn,   # Type error — expected Role, got Bucket
)
```

#### Shorthand Syntax

For convenience, `Attr[T, "name"]` is equivalent to `Attr[T, Literal["name"]]`:

```python
role_arn: Attr[Role, "Arn"]  # Equivalent to Attr[Role, Literal["Arn"]]
```

### `RefList[T]` and `RefDict[K, V]` — Collection Types

For collections of references:

```python
from graph_refs import RefList, RefDict

@dataclass
class LoadBalancer:
    targets: RefList[Instance]  # list[Ref[Instance]] with implicit conversion
    mappings: RefDict[str, TargetGroup]  # dict[str, Ref[TargetGroup]]
```

These are equivalent to `list[Ref[T]]` and `dict[K, Ref[V]]` but signal that the decorator should process elements for implicit reference conversion.

### `ContextRef[name]` — Context Reference

`ContextRef` represents a reference to a context value resolved at serialization time:

```python
from graph_refs import ContextRef
from typing import Literal

@dataclass
class Context:
    project: str
    environment: str
    region: str

@dataclass
class MyResource:
    name: ContextRef[Literal["project"]]  # Resolved from context.project
    region: ContextRef[Literal["region"]]
```

Context references are distinct from resource references — they reference environment values, not other resources in the graph.

## Introspection API

### `get_refs()` — Reference Extraction

Extract reference information from a class:

```python
from graph_refs import get_refs, RefInfo

@dataclass
class Subnet:
    network: Ref[Network]
    gateway: Ref[Gateway]
    cidr: str

refs = get_refs(Subnet)
# Returns:
# {
#     'network': RefInfo(field='network', target=Network, attr=None),
#     'gateway': RefInfo(field='gateway', target=Gateway, attr=None),
# }
```

This enables:
- Dependency graph construction
- Serialization logic
- Validation tools

### `RefInfo` — Reference Metadata

```python
@dataclass
class RefInfo:
    field: str           # Field name
    target: type         # Referenced class
    attr: str | None     # Attribute name (for Attr/ContextRef types)
    is_list: bool        # True if RefList
    is_dict: bool        # True if RefDict
    is_optional: bool    # True if Ref[T] | None
    is_context: bool     # True if ContextRef
```

### `get_dependencies()` — Dependency Graph

Compute the dependency graph from reference information:

```python
from graph_refs import get_dependencies

@dataclass
class Network:
    cidr: str

@dataclass
class Subnet:
    network: Ref[Network]
    cidr: str

@dataclass
class Instance:
    subnet: Ref[Subnet]
    name: str

deps = get_dependencies(Instance)
# Returns: {Subnet}

all_deps = get_dependencies(Instance, transitive=True)
# Returns: {Subnet, Network}
```

This enables:
- Topological sorting for creation ordering
- Cycle detection
- Impact analysis

## Design Rationale

### Why Not Just Use `type[T]`?

`type[T]` means "the class T itself" which is semantically different from "a reference to an instance of T":

```python
# type[T] — I want the class object
def create_instance(cls: type[T]) -> T:
    return cls()

# Ref[T] — I want to reference an instance
@dataclass
class Subnet:
    network: Ref[Network]  # Reference to a Network, not the Network class
```

### Why Not Just Use Forward References?

Forward reference strings (`"Network"`) resolve to the class itself, not a reference relationship. Type checkers treat them as the class type, not a reference type.

### Why `Attr[T, name]` Instead of Just Attribute Access?

Type checkers need to distinguish between:

```python
# Direct attribute access — value is the attribute's type
role_name: str = MyRole.name

# Attribute reference — value is a reference to be resolved later
role_arn: Attr[Role, "Arn"] = MyRole.Arn  # Serializes to {"GetAtt": ["MyRole", "Arn"]}
```

### Why Collection Types?

`RefList[T]` and `RefDict[K, V]` serve two purposes:

1. **Conciseness**: `RefList[T]` vs `list[Ref[T]]`
2. **Signaling**: Indicates the decorator should process elements for implicit conversion

## Relationship to Existing Work

| Foundation | Relationship |
|------------|--------------|
| PEP 484 (Type Hints) | Basic type hint syntax |
| PEP 557 (Dataclasses) | Dataclass foundation |
| PEP 585 | Enables `Ref[T]` generic syntax |
| PEP 586 (Literal) | Enables `Attr[T, Literal["name"]]` |
| PEP 681 (dataclass_transform) | Type checker support for custom decorators |

## Future Directions

These are open questions that would need community input if pursuing stdlib inclusion:

1. **Variance**: Should `Ref[T]` be covariant, contravariant, or invariant? Covariant makes the most sense (a `Ref[Dog]` is a `Ref[Animal]`), but this needs validation.

2. **Generic References**: Should `Ref[T]` work with unbound type variables? `def connect(a: Ref[T], b: Ref[T])` to ensure both reference the same type?

3. **Attribute Type Extraction**: Should `Attr[Role, "Arn"]` expose the type of `Role.Arn`? This would enable: `arn_value: AttrType[Role, "Arn"]`

4. **dataclass_transform Extensions**: Could `@dataclass_transform` gain `ref_types` and `implicit_refs` parameters to better support DSL decorators?

## Rejected Ideas

### Dependent Types

Full dependent type support (`Ref[MyVPC]` where `MyVPC` is a value, not a type) was rejected as too complex for the current type system.

### Reference Validation at Runtime

Runtime validation of references was rejected because:
- Target systems perform their own validation
- Adds runtime overhead
- Type checking provides development-time safety

### Overloading `|` for Reference Unions

```python
network: MyVPC | MyOtherVPC  # Rejected
```

Rejected because `|` already means type union, not reference alternatives.

### Magic Attribute Inference

Automatically inferring `Attr` from any attribute access was rejected because it would break existing code where attribute access returns the attribute value, not a reference.

## Acknowledgements

This library builds on the foundational work of **Eric V. Smith** and PEP 557 (Data Classes), which established dataclasses as a first-class Python feature.

Additional foundations:
- PEP 484 (Type Hints) — Guido van Rossum, Jukka Lehtosalo, Łukasz Langa
- PEP 681 (Data Class Transforms) — Erik De Bonte, Eric Traut
- The attrs library (Hynek Schlawack)
- The pydantic library (Samuel Colvin)
