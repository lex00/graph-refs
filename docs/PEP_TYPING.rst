PEP: 9999
Title: Typed Graph References for Declarative Dataclasses
Author: Alex Artigues <albert.a.artigues@gmail.com>
Sponsor: TBD
Status: Draft
Type: Standards Track
Topic: Typing
Requires: 484, 557, 585, 681
Created: 26-Dec-2024
Python-Version: 3.14
Post-History:


Abstract
========

This PEP proposes additions to the ``typing`` module to support type-safe
references between dataclass instances in declarative domain-specific
languages. It introduces ``Ref[T]`` for typed references to other classes,
``Attr[T, name]`` for typed attribute access, and extensions to
``@dataclass_transform`` for reference-aware decorators.

These constructs enable static type checkers to verify that resource
relationships in infrastructure-as-code, configuration systems, and other
graph-structured DSLs are correctly typed.


Motivation
==========

The Graph Problem
-----------------

Dataclasses naturally model tree-structured data, but many domains require
graph structures where objects reference each other::

    @dataclass
    class Subnet:
        network: ???  # Reference to a Network instance
        cidr: str

    @dataclass
    class Network:
        subnets: list[???]  # References to Subnet instances
        cidr: str

Currently, there's no standard way to express "this field references another
dataclass" with full type safety.


Current Workarounds
-------------------

**String identifiers:**

::

    @dataclass
    class Subnet:
        network_id: str  # No type safety — any string accepted

**Forward references:**

::

    @dataclass
    class Subnet:
        network: "Network"  # Type checker sees this as the class, not a reference

**Custom wrapper types:**

::

    class Ref(Generic[T]):
        def __init__(self, target: type[T]): ...

    @dataclass
    class Subnet:
        network: Ref[Network]  # Works, but verbose and no attribute access support


The Opportunity
---------------

A standardized ``Ref[T]`` type would:

1. Enable type checkers to verify reference targets
2. Support IDE autocomplete for valid reference targets
3. Enable static graph analysis (dependency detection, cycle detection)
4. Integrate with ``@dataclass_transform`` for DSL decorators


Use Cases
---------

**Infrastructure-as-Code:**

::

    @infrastructure
    class Database:
        resource: RDSInstance
        vpc: Ref[MyVPC]  # Must reference a VPC-type resource
        security_groups: list[Ref[SecurityGroup]]

**Configuration Management:**

::

    @config
    class ServiceConfig:
        database: Ref[DatabaseConfig]
        cache: Ref[CacheConfig]

**Entity Relationships:**

::

    @entity
    class Order:
        customer: Ref[Customer]
        items: list[Ref[Product]]


Specification
=============

``Ref[T]`` — Typed Reference
----------------------------

``Ref[T]`` represents a reference to an instance of type ``T``::

    from typing import Ref

    @dataclass
    class Network:
        cidr: str

    @dataclass
    class Subnet:
        network: Ref[Network]  # Reference to a Network
        cidr: str


Type Checker Behavior
~~~~~~~~~~~~~~~~~~~~~

- ``Ref[T]`` is assignable from:

  - The class ``T`` itself (for implicit reference patterns)
  - An instance of ``Ref[T]``
  - Any subclass of ``T`` (covariant)

- ``Ref[T]`` is NOT assignable from:

  - Unrelated types
  - ``str`` (unless explicitly typed as ``Ref[T] | str``)

::

    subnet = Subnet(
        network=MyNetwork,      # OK — class reference
        cidr="10.0.1.0/24"
    )

    subnet = Subnet(
        network=MyBucket,       # Type error — Bucket is not Network
        cidr="10.0.1.0/24"
    )


Runtime Representation
~~~~~~~~~~~~~~~~~~~~~~

At runtime, ``Ref[T]`` is equivalent to ``type[T] | T``. The generic parameter
is erased but available via ``__origin__`` and ``__args__``::

    from typing import get_origin, get_args

    field_type = Ref[Network]
    get_origin(field_type)  # Ref
    get_args(field_type)    # (Network,)


``Attr[T, name]`` — Typed Attribute Reference
---------------------------------------------

``Attr[T, name]`` represents a reference to a specific attribute of type ``T``::

    from typing import Attr, Literal

    @dataclass
    class Role:
        name: str

        # Attributes available for reference
        Arn: ClassVar[str]
        RoleId: ClassVar[str]

    @dataclass
    class Function:
        role_arn: Attr[Role, Literal["Arn"]]  # Reference to Role's Arn attribute


Type Checker Behavior
~~~~~~~~~~~~~~~~~~~~~

- ``Attr[T, Literal["name"]]`` is assignable from:

  - ``T.name`` (class attribute access)
  - An instance of ``Attr[T, Literal["name"]]``

- Type checkers SHOULD verify that ``T`` has an attribute ``name``

::

    function = Function(
        role_arn=MyRole.Arn,     # OK — Role has Arn attribute
    )

    function = Function(
        role_arn=MyRole.Xyz,     # Type error — Role has no Xyz attribute
    )

    function = Function(
        role_arn=MyBucket.Arn,   # Type error — expected Role, got Bucket
    )


Shorthand Syntax
~~~~~~~~~~~~~~~~

For convenience, ``Attr[T, "name"]`` is equivalent to ``Attr[T, Literal["name"]]``::

    role_arn: Attr[Role, "Arn"]  # Equivalent to Attr[Role, Literal["Arn"]]


``RefList[T]`` and ``RefDict[K, V]`` — Collection Types
-------------------------------------------------------

For collections of references::

    from typing import RefList, RefDict

    @dataclass
    class LoadBalancer:
        targets: RefList[Instance]  # list[Ref[Instance]] with implicit conversion
        mappings: RefDict[str, TargetGroup]  # dict[str, Ref[TargetGroup]]

These are equivalent to ``list[Ref[T]]`` and ``dict[K, Ref[V]]`` but signal
that the decorator should process elements for implicit reference conversion.


Extensions to ``@dataclass_transform``
--------------------------------------

``ref_types`` Parameter
~~~~~~~~~~~~~~~~~~~~~~~

A new parameter to ``@dataclass_transform`` indicating which types should be
treated as references::

    from typing import dataclass_transform, Ref, Attr

    @dataclass_transform(
        ref_types=(Ref, Attr),  # Types to treat as references
    )
    def infrastructure(cls):
        ...


``implicit_refs`` Parameter
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A boolean indicating whether class references should be implicitly converted
to ``Ref[T]``::

    @dataclass_transform(
        implicit_refs=True,  # Enable no-parens pattern
    )
    def infrastructure(cls):
        ...

    @infrastructure
    class Subnet:
        network = MyNetwork  # Implicitly Ref[MyNetwork]

When ``implicit_refs=True``, type checkers SHOULD:

1. Infer ``Ref[T]`` when a class ``T`` is assigned to a field
2. Infer ``Attr[T, name]`` when ``T.name`` is assigned to a field
3. Process list/dict literals for nested references


``get_refs()`` — Reference Introspection
----------------------------------------

A new function to extract reference information from a class::

    from typing import get_refs, RefInfo

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

This enables:

- Dependency graph construction
- Serialization logic
- Validation tools


``RefInfo`` — Reference Metadata
--------------------------------

::

    @dataclass
    class RefInfo:
        field: str           # Field name
        target: type         # Referenced class
        attr: str | None     # Attribute name (for Attr/ContextRef types)
        is_list: bool        # True if RefList
        is_dict: bool        # True if RefDict
        is_optional: bool    # True if Ref[T] | None
        is_context: bool     # True if ContextRef


``ContextRef[name]`` — Context Reference
----------------------------------------

``ContextRef`` represents a reference to a context value resolved at
serialization time::

    from typing import ContextRef, Literal

    @dataclass
    class Context:
        project: str
        environment: str
        region: str

    @dataclass
    class MyResource:
        name: ContextRef[Literal["project"]]  # Resolved from context.project
        region: ContextRef[Literal["region"]]

Context references are distinct from resource references — they reference
environment values, not other resources in the graph.


``get_dependencies()`` — Dependency Graph Extraction
----------------------------------------------------

A function to compute the dependency graph from reference information::

    from typing import get_dependencies

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

This enables:

- Topological sorting for creation ordering
- Cycle detection
- Impact analysis


Rationale
=========

Why Not Just Use ``type[T]``?
-----------------------------

``type[T]`` means "the class T itself" which is semantically different from
"a reference to an instance of T"::

    # type[T] — I want the class object
    def create_instance(cls: type[T]) -> T:
        return cls()

    # Ref[T] — I want to reference an instance
    @dataclass
    class Subnet:
        network: Ref[Network]  # Reference to a Network, not the Network class


Why Not Just Use Forward References?
------------------------------------

Forward reference strings (``"Network"``) resolve to the class itself, not a
reference relationship. Type checkers treat them as the class type, not a
reference type.


Why ``Attr[T, name]`` Instead of Just Attribute Access?
-------------------------------------------------------

Type checkers need to distinguish between::

    # Direct attribute access — value is the attribute's type
    role_name: str = MyRole.name

    # Attribute reference — value is a reference to be resolved later
    role_arn: Attr[Role, "Arn"] = MyRole.Arn  # Serializes to {"GetAtt": ["MyRole", "Arn"]}


Why Collection Types?
---------------------

``RefList[T]`` and ``RefDict[K, V]`` serve two purposes:

1. **Conciseness**: ``RefList[T]`` vs ``list[Ref[T]]``
2. **Signaling**: Indicates the decorator should process elements for implicit conversion


Relationship to Existing PEPs
-----------------------------

======= ================================================
PEP     Relationship
======= ================================================
PEP 484 Foundation — basic type hints
PEP 557 Foundation — dataclasses
PEP 585 Enables ``Ref[T]`` generic syntax
PEP 586 Enables ``Attr[T, Literal["name"]]``
PEP 681 Extended with ``ref_types`` and ``implicit_refs``
PEP 695 Alternative syntax: ``class Subnet[N: Network]:``
======= ================================================


Backwards Compatibility
=======================

All proposed constructs are new additions to the ``typing`` module. Existing
code is unaffected.

Libraries currently using custom ``Ref`` types can adopt the standard type
gradually. Type checkers should support both custom and standard types during
transition.


Security Implications
=====================

Reference types themselves have no security implications. However, DSLs using
these types for infrastructure-as-code should implement appropriate validation
to prevent security misconfigurations.


How to Teach This
=================

For DSL Users
-------------

"Use ``Ref[T]`` when one resource references another. The type checker will
verify you're referencing the right kind of resource."

::

    @infrastructure
    class Subnet:
        network: Ref[VPC]  # Must reference a VPC

    subnet = Subnet(network=MyVPC)       # OK
    subnet = Subnet(network=MyBucket)    # Type error!


For DSL Implementers
--------------------

"Decorate your decorator with ``@dataclass_transform(ref_types=(Ref, Attr))``
so type checkers understand your reference patterns."


For Type Checker Implementers
-----------------------------

1. Treat ``Ref[T]`` as a distinct generic type
2. Allow assignment from ``type[T]`` when in a dataclass context
3. Implement attribute validation for ``Attr[T, name]``
4. Support the new ``@dataclass_transform`` parameters


Reference Implementation
========================

A reference implementation is available as the `graph-refs`_ package on PyPI::

    pip install graph-refs

The package provides all proposed types and introspection functions with zero
dependencies, designed for potential inclusion in ``typing_extensions`` or the
standard library.

.. _graph-refs: https://pypi.org/project/graph-refs/

Key implementation components::

    # typing.py additions

    class Ref(Generic[T]):
        """A typed reference to another class."""
        __slots__ = ()

        def __class_getitem__(cls, item):
            return _GenericAlias(cls, (item,))

    class Attr(Generic[T, NameT]):
        """A typed reference to an attribute of another class."""
        __slots__ = ()

        def __class_getitem__(cls, args):
            if len(args) != 2:
                raise TypeError("Attr requires exactly two arguments")
            return _GenericAlias(cls, args)

    @dataclass
    class RefInfo:
        field: str
        target: type
        attr: str | None
        is_list: bool = False
        is_dict: bool = False
        is_optional: bool = False
        is_context: bool = False

    def get_refs(cls: type) -> dict[str, RefInfo]:
        """Extract reference information from a class."""
        refs = {}
        hints = get_type_hints(cls)
        for name, hint in hints.items():
            origin = get_origin(hint)
            if origin is Ref:
                refs[name] = RefInfo(name, get_args(hint)[0], None, False, False, False, False)
            elif origin is Attr:
                args = get_args(hint)
                refs[name] = RefInfo(name, args[0], args[1], False, False, False, False)
            # ... handle RefList, RefDict, Union with None
        return refs

    class ContextRef(Generic[NameT]):
        """A typed reference to a context value."""
        __slots__ = ()

        def __class_getitem__(cls, item):
            return _GenericAlias(cls, (item,))

    def get_dependencies(cls: type, transitive: bool = False) -> set[type]:
        """Extract dependency graph from reference information."""
        refs = get_refs(cls)
        deps = {info.target for info in refs.values() if not info.is_context}
        if transitive:
            visited = set()
            to_visit = list(deps)
            while to_visit:
                current = to_visit.pop()
                if current not in visited:
                    visited.add(current)
                    nested = get_dependencies(current, transitive=False)
                    to_visit.extend(nested - visited)
            return visited
        return deps


Rejected Ideas
==============

Dependent Types
---------------

Full dependent type support (``Ref[MyVPC]`` where ``MyVPC`` is a value, not a
type) was rejected as too complex for the current type system.


Reference Validation at Runtime
-------------------------------

Runtime validation of references was rejected because:

- Target systems perform their own validation
- Adds runtime overhead
- Type checking provides development-time safety


Overloading ``|`` for Reference Unions
--------------------------------------

::

    network: MyVPC | MyOtherVPC  # Rejected

Rejected because ``|`` already means type union, not reference alternatives.


Magic Attribute Inference
-------------------------

Automatically inferring ``Attr`` from any attribute access was rejected because
it would break existing code where attribute access returns the attribute value,
not a reference.


Open Issues
===========

1. ~~**Syntax for Optional References**: Should ``Ref[T] | None`` be the
   standard pattern, or should there be ``OptionalRef[T]``?~~ **Resolved**: The
   reference implementation uses ``Ref[T] | None`` which works well with both
   old (``Union[Ref[T], None]``) and new (``Ref[T] | None``) syntax.

2. **Variance**: Should ``Ref[T]`` be covariant, contravariant, or invariant?
   Covariant makes the most sense (a ``Ref[Dog]`` is a ``Ref[Animal]``), but
   this needs validation.

3. **Generic References**: Should ``Ref[T]`` work with unbound type variables?
   ``def connect(a: Ref[T], b: Ref[T])`` to ensure both reference the same type?

4. **Attribute Type Extraction**: Should ``Attr[Role, "Arn"]`` expose the type
   of ``Role.Arn``? This would enable: ``arn_value: AttrType[Role, "Arn"]``

5. ~~**Circular References**: How should type checkers handle ``Ref[A]`` where
   ``A`` has ``Ref[B]`` and ``B`` has ``Ref[A]``?~~ **Resolved**: The reference
   implementation handles circular references gracefully in ``get_dependencies()``
   by tracking visited nodes. Self-referential classes (e.g., tree nodes with
   ``parent: Ref["TreeNode"] | None``) work correctly.


Acknowledgements
================

This proposal builds directly upon the foundational work of **Eric V. Smith**
and PEP 557 (Data Classes), which established dataclasses as a first-class
Python feature. The typed reference pattern proposed here is a natural
extension of that vision into graph-structured domains.

Additional foundations:

- PEP 484 (Type Hints) — Guido van Rossum, Jukka Lehtosalo, Lukasz Langa
- PEP 681 (Data Class Transforms) — Erik De Bonte, Eric Traut
- The attrs library (Hynek Schlawack)
- The pydantic library (Samuel Colvin)


Copyright
=========

This document is placed in the public domain or under the CC0-1.0-Universal
license, whichever is more permissive.
