# The Declarative Dataclass Pattern

A pattern for using Python dataclasses as the foundation for declarative domain-specific languages (DSLs), particularly suited for infrastructure-as-code, configuration management, and schema-driven systems.

## Overview

This pattern emphasizes flat, readable declarations where resource relationships are expressed through class references rather than function calls, enabling both human readability and machine accessibility.

**Key principles:**
- Flat by default — no unnecessary nesting
- No parens for wiring — references are class names, not function calls
- Type-safe without ceremony — annotations add safety without boilerplate
- Graph-native — resources and relationships are first-class concepts

## Motivation

### The Problem with Existing Approaches

Infrastructure-as-code and configuration DSLs face a tension between power and readability:

1. **YAML/JSON configurations** are readable but lack type safety, IDE support, and abstraction capabilities

2. **Imperative SDKs** (constructors, method chaining) are powerful but obscure intent:
   ```python
   # Intent is buried in imperative calls
   bucket = storage.Bucket(self, "Data", bucket_name="data")
   bucket.add_lifecycle_rule(expiration=Duration.days(90))
   bucket.grant_read(some_function)  # Mutation after construction
   ```

3. **Existing dataclass usage** often still relies on function calls in field assignments:
   ```python
   @dataclass
   class MyResource:
       name: str = field(default_factory=lambda: generate_name())
       reference: str = some_helper_function(OtherResource)
   ```

### The Opportunity

Python dataclasses provide an ideal foundation for declarative DSLs because:

- **Static shape, dynamic values** — Classes define schema, fields hold configuration
- **Type annotations** — Enable IDE autocomplete and static analysis
- **Serialization transparency** — `asdict()` maps directly to JSON/YAML
- **Introspection** — `fields()` enables metaprogramming
- **Inheritance** — Natural model for configuration variants

## The Wrapper Pattern

The core pattern wraps domain objects (resources, configurations, entities) in user-defined dataclasses:

```python
@infrastructure_dataclass
class MyDatabase:
    resource: DatabaseInstance
    instance_class = "db.t3.micro"
    storage_size = 100
    encryption = Enabled
```

Key characteristics:

- The `resource:` field declares the underlying type
- Other fields configure that resource
- The decorator handles registration, serialization, and reference resolution

## The No-Parens Principle

**Observation:** Function calls in field assignments are ceremony that obscures intent.

```python
# Ceremony — function calls required
network_id = ref(MyNetwork)
role_arn = get_att(MyRole, "Arn")
subnets = [ref(S1), ref(S2), ref(S3)]

# Declaration — just class references
network_id = MyNetwork
role_arn = MyRole.Arn
subnets = [S1, S2, S3]
```

The decorator can inspect assigned values at class creation time and determine:

- **Class reference to another wrapper** → Generate a reference/relationship
- **Class attribute access** → Generate an attribute reference
- **Literal value** → Pass through as-is
- **List/dict of references** → Process each element

This is achievable using `__set_name__` (PEP 487) for descriptors and class introspection in the decorator.

### The Paren Boundary

Not everything should be paren-free. The principle is:

| Category | Paren-Free | Rationale |
|----------|------------|-----------|
| Resource references | Yes | `network = MyNetwork` |
| Attribute references | Yes | `arn = MyRole.Arn` |
| Nested configurations | Yes | `encryption = MyEncryption` |
| Literal values | Yes | `name = "data"` |
| Collections of refs | Yes | `items = [A, B, C]` |
| Intrinsic functions | No | `Sub()`, `Join()` are computations |
| Conditional values | No | `when()`, `match()` express logic |
| Replication | No | `ForEach()` is a transformation |
| External data | No | `Import()`, `Parameter()` are external |

**The 90% case (wiring resources) is paren-free. The 10% case (logic, computation, external data) uses explicit calls.**

## Implementation Guide

### Decorator Behavior

A conforming decorator should:

1. Transform the decorated class into a dataclass (or equivalent)
2. Register the class in a global or scoped registry
3. Inspect class attributes for reference patterns
4. Provide serialization to the target format (JSON, YAML, etc.)

Use `@dataclass_transform` (PEP 681) for type checker compatibility:

```python
from typing import dataclass_transform

@dataclass_transform()
def infrastructure_dataclass(cls):
    # Implementation
    return cls
```

### Reference Detection

When the decorator encounters a class attribute whose value is another decorated class, treat this as a reference relationship:

```python
@infrastructure_dataclass
class MyNetwork:
    resource: VirtualNetwork
    cidr = "10.0.0.0/16"

@infrastructure_dataclass
class MySubnet:
    resource: Subnet
    network = MyNetwork  # Detected as reference to MyNetwork
    cidr = "10.0.1.0/24"
```

Implementation mechanism:

```python
def infrastructure_dataclass(cls):
    for name, value in list(cls.__dict__.items()):
        if is_infrastructure_dataclass(value):
            # Replace with a descriptor that serializes as reference
            setattr(cls, name, ReferenceDescriptor(value))
    return cls
```

### Using graph-refs for Typing

The [graph-refs](https://pypi.org/project/graph-refs/) library provides typed reference markers:

```python
from graph_refs import Ref, Attr, RefList, get_refs, get_dependencies

@dataclass
class MySubnet:
    network: Ref[Network]           # Typed reference
    gateway: Ref[Gateway] | None    # Optional reference
    security_groups: RefList[SecurityGroup]  # List of references

# Introspection
refs = get_refs(MySubnet)  # Extract reference metadata
deps = get_dependencies(MySubnet, transitive=True)  # Compute dependency graph
```

### Collection Handling

Lists and dicts containing references should be processed recursively:

```python
@infrastructure_dataclass
class MyFunction:
    resource: Function
    security_groups = [SG1, SG2, SG3]  # List of references
    environment = {
        "DB_HOST": MyDatabase,           # Reference
        "DB_ARN": MyDatabase.Arn,        # Attribute reference
        "REGION": "us-east-1",           # Literal
    }
```

### Preset Classes (Inheritance-Based Defaults)

Using `__init_subclass__` (PEP 487), base classes can provide default configurations:

```python
class EncryptedStorage:
    """Mixin that applies encryption defaults."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, 'encryption'):
            cls.encryption = DefaultEncryption

@infrastructure_dataclass
class MyBucket(EncryptedStorage):
    resource: Bucket
    name = "data"
    # encryption inherited from EncryptedStorage
```

### Traits (Cross-Cutting Concerns)

Traits apply configurations across multiple resource types:

```python
class Tagged:
    """Trait that applies standard tags."""

    def __init_subclass__(cls, environment: str, team: str, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._tags = [
            ("Environment", environment),
            ("Team", team),
        ]

@infrastructure_dataclass
class MyBucket(Tagged, environment="prod", team="platform"):
    resource: Bucket
    name = "data"
```

### Registry Pattern

Decorated classes should register themselves for later discovery:

```python
class Registry:
    def __init__(self):
        self._resources: dict[str, type] = {}
        self._by_type: dict[str, list[type]] = {}

    def register(self, cls: type, resource_type: str) -> None:
        self._resources[cls.__name__] = cls
        self._by_type.setdefault(resource_type, []).append(cls)

    def get_all(self, scope_package: str | None = None) -> list[type]:
        """Get all resources, optionally filtered by package."""
        resources = list(self._resources.values())
        if scope_package:
            resources = [r for r in resources if r.__module__.startswith(scope_package)]
        return resources

registry = Registry()
```

**Scoped discovery** prevents pollution across unrelated packages:

```python
# Only resources from this package
resources = registry.get_all(scope_package="my_project.resources")
```

### Template Pattern

A `Template` class aggregates resources from the registry and provides serialization:

```python
class Template:
    @classmethod
    def from_registry(
        cls,
        scope_package: str | None = None,
        context: Context | None = None
    ) -> "Template":
        """Build template from registered resources."""
        resources = registry.get_all(scope_package=scope_package)
        return cls(resources=resources, context=context)

    def to_dict(self) -> dict:
        """Serialize to dictionary format."""
        ...

    def to_json(self) -> str:
        """Serialize to JSON."""
        ...

    def to_yaml(self) -> str:
        """Serialize to YAML."""
        ...
```

### Context Pattern

A `Context` object provides environment-specific values resolved at serialization time:

```python
@dataclass
class Context:
    project: str
    environment: str
    region: str | None = None

# Usage
context = Context(project="myapp", environment="prod", region="us-east-1")
template = Template.from_registry(context=context)
```

Context values can be referenced in resource definitions using `ContextRef` from graph-refs:

```python
from graph_refs import ContextRef

@infrastructure_dataclass
class MyResource:
    resource: SomeType
    name = ContextRef("project")  # Resolved at serialization time
```

### Dependency Graph

Implementations should compute dependency ordering from reference analysis:

```python
from graph_refs import get_dependencies

def topological_sort(resources: list[type]) -> list[type]:
    """Sort resources by dependency order."""
    graph = {r: get_dependencies(r) for r in resources}
    # Kahn's algorithm or Tarjan's for topological sort
    ...
```

**Circular dependencies** (A → B → A) require special handling:
- Group into strongly connected components
- Place together in output
- Generate explicit dependency declarations if the target format supports them

### Forward References

When Class A references Class B which is defined later:

```python
@infrastructure_dataclass
class MySubnet:
    resource: Subnet
    network = MyNetwork  # MyNetwork not yet defined!

@infrastructure_dataclass
class MyNetwork:
    resource: Network
```

Solutions:
1. **Defer resolution** — Store class names as strings, resolve at serialization time
2. **Two-phase initialization** — Register all classes first, resolve references second
3. **Registry lookup** — `network = "MyNetwork"` with registry-based resolution

### Computed Values

For values derived from other fields:

```python
@infrastructure_dataclass
class MyBucket:
    resource: Bucket
    project: str
    environment: str

    @computed
    def name(self) -> str:
        return f"{self.project}-{self.environment}-data"
```

### Conditional Values

For values that depend on conditions:

```python
@infrastructure_dataclass
class MyDatabase:
    resource: Database
    instance_class = when(
        environment == "production",
        then="db.r5.large",
        else_="db.t3.micro"
    )
```

## Related Work

| Library/PEP | Relationship |
|-------------|--------------|
| PEP 557 (Dataclasses) | Foundation — this pattern extends dataclasses for domain-specific use |
| PEP 681 (dataclass_transform) | Enables custom decorators to be recognized by type checkers |
| PEP 487 | Provides `__set_name__` and `__init_subclass__` hooks |
| graph-refs | Reference implementation of typed graph references (`Ref[T]`, `Attr[T, name]`, etc.) |
| attrs / pydantic | Similar goals but different philosophy — this pattern emphasizes flatness over validation |

## Open Questions

1. **Forward Reference Syntax** — What's the cleanest way to handle forward references? String names? Deferred resolution? `TYPE_CHECKING` guards?

2. **Attribute Reference Mechanism** — Should `MyResource.Attr` use metaclass `__getattr__`, class descriptors, or a different mechanism?

3. **Validation Hooks** — Should the pattern include standard hooks for cross-resource validation?

4. **Multi-Provider Resources** — When a single resource definition targets multiple providers, how should provider-specific properties be handled?

## Acknowledgements

This pattern builds on the foundational work of **Eric V. Smith** and PEP 557 (Data Classes), which established dataclasses as a first-class Python feature.

Additional inspiration from:
- The attrs library (Hynek Schlawack)
- The broader infrastructure-as-code community and its evolution toward declarative, graph-based resource models
