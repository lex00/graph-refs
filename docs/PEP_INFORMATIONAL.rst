PEP: 9998
Title: Declarative Dataclasses for Infrastructure and Configuration DSLs
Author: Alex Artigues <albert.a.artigues@gmail.com>
Status: Draft
Type: Informational
Created: 26-Dec-2024
Post-History:


Abstract
========

This PEP describes a pattern for using Python dataclasses as the foundation
for declarative domain-specific languages (DSLs), particularly suited for
infrastructure-as-code, configuration management, and schema-driven systems.
The pattern emphasizes flat, readable declarations where resource relationships
are expressed through class references rather than function calls, enabling
both human readability and AI-agent accessibility.

This document provides guidance on implementing such DSLs using existing Python
features including ``@dataclass_transform`` (PEP 681), ``__set_name__`` and
``__init_subclass__`` (PEP 487), and standard typing constructs. No language
changes are proposed.


Motivation
==========

The Problem with Existing Approaches
------------------------------------

Infrastructure-as-code and configuration DSLs face a tension between power and
readability:

1. **YAML/JSON configurations** are readable but lack type safety, IDE support,
   and abstraction capabilities

2. **Imperative SDKs** (constructors, method chaining) are powerful but obscure
   intent::

       # Intent is buried in imperative calls
       bucket = storage.Bucket(self, "Data", bucket_name="data")
       bucket.add_lifecycle_rule(expiration=Duration.days(90))
       bucket.grant_read(some_function)  # Mutation after construction

3. **Existing dataclass usage** often still relies on function calls in field
   assignments::

       @dataclass
       class MyResource:
           name: str = field(default_factory=lambda: generate_name())
           reference: str = some_helper_function(OtherResource)


The Opportunity
---------------

Python dataclasses provide an ideal foundation for declarative DSLs because:

- **Static shape, dynamic values** — Classes define schema, fields hold configuration
- **Type annotations** — Enable IDE autocomplete and static analysis
- **Serialization transparency** — ``asdict()`` maps directly to JSON/YAML
- **Introspection** — ``fields()`` enables metaprogramming
- **Inheritance** — Natural model for configuration variants

What's missing is a **codified pattern** for building DSLs that maximize these
benefits while maintaining flat, readable declarations.


Design Goals
------------

1. **Flat by default** — No unnecessary nesting or constructor calls in assignments
2. **No parens for wiring** — Resource relationships expressed as class references
3. **Type-safe without ceremony** — Annotations add safety without boilerplate
4. **Power when needed** — Advanced features use explicit syntax
5. **Graph-native** — Resources and relationships are first-class concepts


Rationale
=========

The Wrapper Pattern
-------------------

The core pattern wraps domain objects (resources, configurations, entities) in
user-defined dataclasses::

    @infrastructure_dataclass
    class MyDatabase:
        resource: DatabaseInstance
        instance_class = "db.t3.micro"
        storage_size = 100
        encryption = Enabled

Key characteristics:

- The ``resource:`` field declares the underlying type
- Other fields configure that resource
- The decorator handles registration, serialization, and reference resolution


The No-Parens Principle
-----------------------

**Observation:** Function calls in field assignments are ceremony that obscures
intent.

::

    # Ceremony — function calls required
    network_id = ref(MyNetwork)
    role_arn = get_att(MyRole, "Arn")
    subnets = [ref(S1), ref(S2), ref(S3)]

    # Declaration — just class references
    network_id = MyNetwork
    role_arn = MyRole.Arn
    subnets = [S1, S2, S3]

The decorator can inspect assigned values at class creation time and determine:

- **Class reference to another wrapper** → Generate a reference/relationship
- **Class attribute access** → Generate an attribute reference
- **Literal value** → Pass through as-is
- **List/dict of references** → Process each element

This is achievable using ``__set_name__`` (PEP 487) for descriptors and class
introspection in the decorator.


The Paren Boundary
------------------

Not everything should be paren-free. The principle is:

======================== ========== ==========================================
Category                 Paren-Free Rationale
======================== ========== ==========================================
Resource references      Yes        ``network = MyNetwork``
Attribute references     Yes        ``arn = MyRole.Arn``
Nested configurations    Yes        ``encryption = MyEncryption``
Literal values           Yes        ``name = "data"``
Collections of refs      Yes        ``items = [A, B, C]``
Intrinsic functions      No         ``Sub()``, ``Join()`` are computations
Conditional values       No         ``when()``, ``match()`` express logic
Replication              No         ``ForEach()`` is a transformation
External data            No         ``Import()``, ``Parameter()`` are external
======================== ========== ==========================================

**The 90% case (wiring resources) is paren-free. The 10% case (logic,
computation, external data) uses explicit calls.**


Comparison to Related Work
--------------------------

**PEP 557 (Data Classes):** Foundation. This pattern extends dataclasses for
domain-specific use.

**PEP 681 (Data Class Transforms):** Enables custom decorators to be recognized
by type checkers. Essential for IDE support.

**PEP 487 (Simpler Class Creation):** Provides ``__set_name__`` and
``__init_subclass__`` hooks that enable implicit reference detection and
inheritance-based configuration.

**graph-refs:** Reference implementation of typed graph references
(``Ref[T]``, ``Attr[T, name]``, etc.) that provides the typing foundation for
this pattern. See the companion Standards Track PEP for the typing primitives
specification.

**attrs / pydantic:** Libraries with similar goals but different philosophy.
This pattern emphasizes flatness and the no-parens principle over validation
and conversion features.


Specification
=============

Decorator Behavior
------------------

A conforming decorator MUST:

1. Transform the decorated class into a dataclass (or equivalent)
2. Register the class in a global or scoped registry
3. Inspect class attributes for reference patterns
4. Provide serialization to the target format (JSON, YAML, etc.)

A conforming decorator SHOULD:

1. Use ``@dataclass_transform`` (PEP 681) for type checker compatibility
2. Support the no-parens reference patterns described below
3. Preserve the class for introspection


Reference Detection
-------------------

When the decorator encounters a class attribute whose value is another
decorated class, it SHOULD treat this as a reference relationship::

    @infrastructure_dataclass
    class MyNetwork:
        resource: VirtualNetwork
        cidr = "10.0.0.0/16"

    @infrastructure_dataclass
    class MySubnet:
        resource: Subnet
        network = MyNetwork  # Detected as reference to MyNetwork
        cidr = "10.0.1.0/24"

Implementation mechanism::

    def infrastructure_dataclass(cls):
        for name, value in list(cls.__dict__.items()):
            if is_infrastructure_dataclass(value):
                # Replace with a descriptor that serializes as reference
                setattr(cls, name, ReferenceDescriptor(value))
        return cls


Attribute References
--------------------

For attribute access patterns (``MyResource.AttributeName``), the decorator
SHOULD add class-level descriptors that return attribute reference objects::

    @infrastructure_dataclass
    class MyRole:
        resource: Role
        # After decoration, MyRole.Arn returns AttributeReference("MyRole", "Arn")

Implementation uses ``__getattr__`` on a metaclass or class-level descriptors
populated from the resource type's known attributes.


Collection Handling
-------------------

Lists and dicts containing references SHOULD be processed recursively::

    @infrastructure_dataclass
    class MyFunction:
        resource: Function
        security_groups = [SG1, SG2, SG3]  # List of references
        environment = {
            "DB_HOST": MyDatabase,           # Reference
            "DB_ARN": MyDatabase.Arn,        # Attribute reference
            "REGION": "us-east-1",           # Literal
        }


Preset Classes (Inheritance-Based Defaults)
-------------------------------------------

Using ``__init_subclass__`` (PEP 487), base classes can provide default
configurations::

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


Traits (Cross-Cutting Concerns)
-------------------------------

Traits apply configurations across multiple resource types::

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


Registry Pattern
----------------

Decorated classes SHOULD register themselves for later discovery::

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

        def get_by_type(self, resource_type: type | str) -> list[type]:
            """Query resources by their underlying type."""
            if isinstance(resource_type, type):
                resource_type = getattr(resource_type, 'resource_type', str(resource_type))
            return list(self._by_type.get(resource_type, []))

    registry = Registry()

**Scoped discovery** prevents pollution across unrelated packages::

    # Only resources from this package
    resources = registry.get_all(scope_package="my_project.resources")

This enables template/configuration builders to discover all declared resources
without explicit wiring.


Template Pattern
----------------

A ``Template`` class aggregates resources from the registry and provides
serialization::

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

Domain-specific implementations MAY provide additional output formats
appropriate to their target systems.


Context Pattern
---------------

A ``Context`` object provides environment-specific values resolved at
serialization time::

    @dataclass
    class Context:
        project: str
        environment: str
        region: str | None = None

    # Usage
    context = Context(project="myapp", environment="prod", region="us-east-1")
    template = Template.from_registry(context=context)

Context values can be referenced in resource definitions::

    @infrastructure_dataclass
    class MyResource:
        resource: SomeType
        name = ContextRef("project")  # Resolved at serialization time

**Pseudo-parameters** are pre-defined context references::

    # Domain-specific pseudo-parameters
    PROJECT = ContextRef("project")
    ENVIRONMENT = ContextRef("environment")
    REGION = ContextRef("region")

    @infrastructure_dataclass
    class MyResource:
        resource: SomeType
        region = REGION  # Resolved from context at serialization


Serialization
-------------

Classes MUST provide serialization to the target format::

    @infrastructure_dataclass
    class MyBucket:
        resource: Bucket
        name = "data"

    # Serialization
    my_bucket_dict = MyBucket.to_dict()
    # Returns: {"Type": "Bucket", "Properties": {"Name": "data"}}

The serialization MUST:

- Resolve references to appropriate format (IDs, names, keys, etc.)
- Handle attribute references
- Process nested configurations
- Apply any format-specific transformations


Dependency Graph
----------------

Implementations SHOULD compute dependency ordering from reference analysis::

    def compute_dependencies(wrapper_class: type) -> set[type]:
        """Extract all classes this resource depends on."""
        deps = set()
        for field in fields(wrapper_class):
            value = getattr(wrapper_class, field.name, None)
            if isinstance(value, ReferenceDescriptor):
                deps.add(value.target_class)
            elif isinstance(value, list):
                for item in value:
                    if is_infrastructure_dataclass(item):
                        deps.add(item)
        return deps

    def topological_sort(resources: list[type]) -> list[type]:
        """Sort resources by dependency order."""
        graph = {r: compute_dependencies(r) for r in resources}
        # Kahn's algorithm or Tarjan's for topological sort
        # Handle cycles by grouping strongly connected components
        ...

**Circular dependencies** (A → B → A) require special handling:

- Group into strongly connected components
- Place together in output
- Generate explicit dependency declarations if the target format supports them

**Deletion ordering** may differ from creation ordering:

- Resources with no dependents should be deleted first
- Implementations MAY generate ordering hints (annotations, waves) for deletion


Provider Abstraction
--------------------

For DSLs that support multiple output formats or target systems, a provider
interface abstracts the differences::

    from abc import ABC, abstractmethod

    class Provider(ABC):
        """Abstract interface for output format providers."""

        name: str

        @abstractmethod
        def serialize(self, template: Template) -> str:
            """Serialize template to provider-specific format."""
            pass

        @abstractmethod
        def get_reference_format(self, source: type, target: type) -> Any:
            """Return provider-specific reference representation."""
            pass

Implementations can then support multiple providers::

    class JSONProvider(Provider):
        name = "json"

        def serialize(self, template: Template) -> str:
            return json.dumps(template.to_dict(), indent=2)

    class YAMLProvider(Provider):
        name = "yaml"

        def serialize(self, template: Template) -> str:
            return yaml.dump(template.to_dict())

This enables a single declarative definition to target multiple output systems.


Implementation Guidance
=======================

Using ``__set_name__`` for Descriptors
--------------------------------------

Descriptors that need to know their attribute name can use ``__set_name__``::

    class ReferenceDescriptor:
        def __set_name__(self, owner, name):
            self.name = name
            self.owner = owner

        def __get__(self, obj, objtype=None):
            if obj is None:
                return self
            return self.resolve_reference()


Using ``@dataclass_transform`` for Type Checker Support
-------------------------------------------------------

To ensure type checkers understand the decorator::

    from typing import dataclass_transform

    @dataclass_transform()
    def infrastructure_dataclass(cls):
        # Implementation
        return cls

This tells type checkers that decorated classes behave like dataclasses.


Forward References
------------------

When Class A references Class B which is defined later::

    @infrastructure_dataclass
    class MySubnet:
        resource: Subnet
        network = MyNetwork  # MyNetwork not yet defined!

    @infrastructure_dataclass
    class MyNetwork:
        resource: Network

Solutions:

1. **Defer resolution** — Store class names as strings, resolve at serialization time
2. **Two-phase initialization** — Register all classes first, resolve references second
3. **Registry lookup** — ``network = "MyNetwork"`` with registry-based resolution


Computed Values
---------------

For values derived from other fields::

    @infrastructure_dataclass
    class MyBucket:
        resource: Bucket
        project: str
        environment: str

        @computed
        def name(self) -> str:
            return f"{self.project}-{self.environment}-data"

The ``@computed`` decorator marks methods for evaluation at serialization time.


Conditional Values
------------------

For values that depend on conditions::

    @infrastructure_dataclass
    class MyDatabase:
        resource: Database
        instance_class = when(
            environment == "production",
            then="db.r5.large",
            else_="db.t3.micro"
        )

The ``when()`` helper creates a deferred conditional that evaluates at
serialization time against provided context.


Backwards Compatibility
=======================

This PEP is informational and proposes no changes to Python. All described
patterns are implementable with existing Python 3.10+ features.

Libraries implementing this pattern should consider:

- Compatibility with standard dataclass tooling
- Integration with existing type checkers via ``@dataclass_transform``
- Migration paths from imperative SDK usage


Security Implications
=====================

DSLs for infrastructure-as-code inherently deal with security-sensitive
configurations. Implementations SHOULD:

- Validate that security-critical fields are not accidentally omitted
- Provide lint rules for common security misconfigurations
- Support policy-as-code patterns for compliance


How to Teach This
=================

For Users New to the Pattern
----------------------------

1. Start with simple resources using literal values
2. Introduce references between resources
3. Show inheritance for configuration reuse
4. Demonstrate the serialization output


For Library Implementers
------------------------

1. Study PEP 681 (``@dataclass_transform``) for type checker integration
2. Study PEP 487 (``__set_name__``, ``__init_subclass__``) for hooks
3. Implement the reference detection algorithm
4. Build serialization for target format


Key Concepts to Emphasize
-------------------------

- **Flat is readable** — Avoid nesting when possible
- **No parens for wiring** — References are class names, not function calls
- **The decorator does the work** — Users declare, implementation translates


Rejected Ideas
==============

Runtime Type Validation (Pydantic-style)
----------------------------------------

Rejected because:

- Adds runtime overhead
- Target systems (cloud providers, orchestrators) perform their own validation
- Type checkers provide development-time safety


Constructor-Based Instantiation
-------------------------------

::

    # Rejected pattern
    subnet = Subnet(network=network, cidr="10.0.1.0/24")

Rejected because:

- Requires explicit instantiation
- Obscures the declarative nature
- Complicates reference resolution


Explicit Reference Wrappers
---------------------------

::

    # Rejected pattern
    network = Ref(MyNetwork)

Rejected because:

- Adds ceremony without benefit
- The decorator can detect references automatically
- Violates the no-parens principle


Magic String Interpolation
--------------------------

::

    # Rejected pattern
    name = f"{project}-{environment}-data"  # Evaluated at definition time

Rejected because:

- Evaluated too early (class definition time, not serialization time)
- Doesn't integrate with target system's interpolation features
- Use ``@computed`` or intrinsic functions instead


Open Issues
===========

1. **Forward Reference Syntax** — What's the cleanest way to handle forward
   references? String names? Deferred resolution? ``TYPE_CHECKING`` guards?
   *Note: The graph-refs implementation handles forward references via*
   ``get_type_hints()`` *with graceful fallback.*

2. **Attribute Reference Mechanism** — Should ``MyResource.Attr`` use metaclass
   ``__getattr__``, class descriptors, or a different mechanism?

3. **Validation Hooks** — Should the pattern include standard hooks for
   cross-resource validation?

4. **Diff/Preview Integration** — Should serialization include hooks for
   structural diff computation?

5. **Context Resolution Timing** — Should context values be resolved at
   serialization time, or should they generate deferred references for the
   target system to resolve? *Note: The graph-refs* ``ContextRef`` *type marks
   context references; resolution timing is left to framework implementations.*

6. **Multi-Provider Resources** — When a single resource definition targets
   multiple providers, how should provider-specific properties be handled?

7. **Lint Rule Framework** — Should the pattern define a standard interface for
   lint rules that detect common mistakes (raw dicts instead of typed helpers,
   string constants instead of enums)?


Acknowledgements
================

This pattern builds directly upon the foundational work of **Eric V. Smith**
and PEP 557 (Data Classes), which established dataclasses as a first-class
Python feature and inspired this extension into domain-specific languages.

Additional inspiration from:

- The attrs library (Hynek Schlawack)
- The broader infrastructure-as-code community and its evolution toward
  declarative, graph-based resource models


Copyright
=========

This document is placed in the public domain or under the CC0-1.0-Universal
license, whichever is more permissive.
