# graph-refs

Typed graph references for Python dataclasses.

[![PyPI version](https://badge.fury.io/py/graph-refs.svg)](https://badge.fury.io/py/graph-refs)
[![Python versions](https://img.shields.io/pypi/pyversions/graph-refs.svg)](https://pypi.org/project/graph-refs/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Overview

`graph-refs` provides type markers for expressing references between dataclass instances in graph-structured domains. It enables type checkers to verify that relationships are correctly typed, while providing runtime introspection for frameworks that need to analyze reference graphs.

```python
from dataclasses import dataclass
from graph_refs import Ref, Attr, get_refs

@dataclass
class Network:
    cidr: str

@dataclass
class Subnet:
    network: Ref[Network]    # Reference to a Network
    cidr: str

@dataclass
class Instance:
    subnet: Ref[Subnet]      # Reference to a Subnet
    role_arn: Attr[Role, "Arn"]  # Reference to Role's Arn attribute
```

## Installation

```bash
pip install graph-refs
```

## Features

### Type Markers

| Type | Purpose | Example |
|------|---------|---------|
| `Ref[T]` | Reference to class T | `network: Ref[Network]` |
| `Attr[T, "name"]` | Reference to T's attribute | `arn: Attr[Role, "Arn"]` |
| `RefList[T]` | List of references | `subnets: RefList[Subnet]` |
| `RefDict[K, V]` | Dict with reference values | `mappings: RefDict[str, Target]` |
| `ContextRef["name"]` | Reference to context value | `region: ContextRef["region"]` |

### Introspection API

```python
from graph_refs import get_refs, get_dependencies, RefInfo

# Extract reference information from a class
refs = get_refs(Subnet)
# {'network': RefInfo(field='network', target=Network, attr=None, ...)}

# Compute dependency graph
deps = get_dependencies(Instance)
# {Subnet}

deps = get_dependencies(Instance, transitive=True)
# {Subnet, Network}
```

### Type Checker Support

`graph-refs` works with mypy, pyright, and other type checkers:

```python
@dataclass
class Subnet:
    network: Ref[Network]

# Type checker catches this error:
subnet = Subnet(network=MyBucket)  # Error: expected Network, got Bucket
```

## Use Cases

### Infrastructure-as-Code

```python
@infrastructure
class Database:
    resource: RDSInstance
    vpc: Ref[MyVPC]
    security_groups: RefList[SecurityGroup]
```

### Configuration Management

```python
@config
class ServiceConfig:
    database: Ref[DatabaseConfig]
    cache: Ref[CacheConfig]
```

### Entity Relationships

```python
@entity
class Order:
    customer: Ref[Customer]
    items: RefList[Product]
```

### Workflow Systems

```python
@task
class ProcessData:
    depends_on: RefList[Task]
    output: Attr[Storage, "Path"]
```

## API Reference

### Types

#### `Ref[T]`

A typed reference to an instance of type `T`.

```python
from graph_refs import Ref

@dataclass
class Subnet:
    network: Ref[Network]  # Must reference a Network
```

#### `Attr[T, name]`

A typed reference to a specific attribute of type `T`.

```python
from graph_refs import Attr

@dataclass
class Function:
    role_arn: Attr[Role, "Arn"]  # Reference to Role's Arn attribute
```

#### `RefList[T]`

Semantic alias for `list[Ref[T]]`.

```python
from graph_refs import RefList

@dataclass
class LoadBalancer:
    targets: RefList[Instance]  # List of Instance references
```

#### `RefDict[K, V]`

Semantic alias for `dict[K, Ref[V]]`.

```python
from graph_refs import RefDict

@dataclass
class Router:
    routes: RefDict[str, Endpoint]  # String keys, Endpoint references
```

#### `ContextRef[name]`

A reference to a context value resolved at runtime.

```python
from graph_refs import ContextRef

@dataclass
class Resource:
    region: ContextRef["region"]  # Resolved from context
```

### Functions

#### `get_refs(cls) -> dict[str, RefInfo]`

Extract reference information from a class.

```python
from graph_refs import get_refs

refs = get_refs(MyClass)
for name, info in refs.items():
    print(f"{name}: references {info.target}")
```

#### `get_dependencies(cls, transitive=False) -> set[type]`

Compute the dependency graph for a class.

```python
from graph_refs import get_dependencies

# Direct dependencies only
deps = get_dependencies(MyClass)

# All transitive dependencies
all_deps = get_dependencies(MyClass, transitive=True)
```

### Data Classes

#### `RefInfo`

Metadata about a reference field.

```python
@dataclass
class RefInfo:
    field: str           # Field name
    target: type         # Referenced class
    attr: str | None     # Attribute name (for Attr types)
    is_list: bool        # True if RefList
    is_dict: bool        # True if RefDict
    is_optional: bool    # True if Ref[T] | None
```

## Design Philosophy

See [docs/RATIONALE.md](docs/RATIONALE.md) for design principles and rationale.

## Related Work

- [PEP 557](https://peps.python.org/pep-0557/) — Data Classes
- [PEP 681](https://peps.python.org/pep-0681/) — Data Class Transforms
- [PEP 484](https://peps.python.org/pep-0484/) — Type Hints

## Acknowledgments

This library builds on Python's dataclasses, created by Eric V. Smith ([PEP 557](https://peps.python.org/pep-0557/)). His work on dataclasses and `@dataclass_transform` ([PEP 681](https://peps.python.org/pep-0681/)) made this library possible.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 — see [LICENSE](LICENSE).
