"""
Introspection API for graph references.

This module provides functions to extract reference information from
classes and compute dependency graphs. These tools enable frameworks
to analyze dataclass definitions and understand the relationships
between objects.

Key functions:

- `get_refs`: Extract all reference fields from a class
- `get_dependencies`: Compute direct or transitive dependencies

Example:
    Extracting references from a class::

        from dataclasses import dataclass
        from graph_refs import Ref, get_refs, get_dependencies

        @dataclass
        class Network:
            cidr: str

        @dataclass
        class Subnet:
            network: Ref[Network]
            cidr: str

        # Get reference information
        refs = get_refs(Subnet)
        print(refs["network"].target)  # <class 'Network'>

        # Get dependencies
        deps = get_dependencies(Subnet)
        print(deps)  # {<class 'Network'>}
"""

from dataclasses import dataclass
from typing import Any, Union, get_args, get_origin, get_type_hints

from graph_refs._types import Attr, ContextRef, Ref, RefDict, RefList

__all__ = [
    "RefInfo",
    "get_refs",
    "get_dependencies",
]


@dataclass(frozen=True)
class RefInfo:
    """Metadata about a reference field.

    This dataclass captures all relevant information about a field that
    contains a reference type (`Ref`, `Attr`, `RefList`, `RefDict`, or
    `ContextRef`). It is returned by `get_refs` for each reference field
    found in a class.

    Attributes:
        field: The name of the field containing the reference.
        target: The referenced class. For `ContextRef`, this is `type(None)`.
        attr: The attribute name for `Attr` types, or the context value name
            for `ContextRef`. None for other reference types.
        is_list: True if the field is a `RefList`.
        is_dict: True if the field is a `RefDict`.
        is_optional: True if the reference is optional (`Ref[T] | None`).
        is_context: True if the field is a `ContextRef`.

    Example:
        Inspecting RefInfo objects::

            from dataclasses import dataclass
            from graph_refs import Ref, Attr, get_refs

            @dataclass
            class Role:
                name: str

            @dataclass
            class Function:
                role: Ref[Role]
                role_arn: Attr[Role, "Arn"]

            refs = get_refs(Function)

            # Ref field
            assert refs["role"].target is Role
            assert refs["role"].attr is None

            # Attr field
            assert refs["role_arn"].target is Role
            assert refs["role_arn"].attr == "Arn"
    """

    field: str
    target: type
    attr: str | None = None
    is_list: bool = False
    is_dict: bool = False
    is_optional: bool = False
    is_context: bool = False


def get_refs(cls: type) -> dict[str, RefInfo]:
    """Extract reference information from a class.

    Analyzes the type hints of a class to find all fields that are
    `Ref`, `Attr`, `RefList`, `RefDict`, or `ContextRef` types. Returns
    a dictionary mapping field names to `RefInfo` objects containing
    metadata about each reference.

    This function handles:

    - Simple references: `Ref[T]`
    - Attribute references: `Attr[T, "name"]` or `Attr[T, Literal["name"]]`
    - List references: `RefList[T]`
    - Dict references: `RefDict[K, V]`
    - Context references: `ContextRef["name"]`
    - Optional references: `Ref[T] | None` or `Optional[Ref[T]]`

    Args:
        cls: The class to analyze. Should be a dataclass or any class
            with type annotations.

    Returns:
        A dictionary mapping field names to `RefInfo` objects. Fields
        without reference types are not included.

    Example:
        Basic usage::

            from dataclasses import dataclass
            from graph_refs import Ref, get_refs

            @dataclass
            class Network:
                cidr: str

            @dataclass
            class Subnet:
                network: Ref[Network]
                gateway: Ref[Gateway] | None
                cidr: str

            refs = get_refs(Subnet)
            # Returns:
            # {
            #     'network': RefInfo(field='network', target=Network, ...),
            #     'gateway': RefInfo(..., target=Gateway, is_optional=True),
            # }

        Note that 'cidr' is not included because it's not a reference type.

    See Also:
        - `RefInfo`: The metadata class returned for each reference.
        - `get_dependencies`: For computing the dependency graph.
    """
    refs: dict[str, RefInfo] = {}

    try:
        hints = get_type_hints(cls, include_extras=True)
    except Exception:
        # If we can't get type hints (e.g., unresolvable forward references),
        # return empty dict rather than raising
        return refs

    for name, hint in hints.items():
        info = _analyze_type(name, hint)
        if info is not None:
            refs[name] = info

    return refs


def _get_origin(hint: Any) -> Any:
    """Get the origin of a type hint, handling custom _GenericAlias.

    This function extends `typing.get_origin` to also handle our custom
    `_GenericAlias` class, which doesn't work with the standard function.

    Args:
        hint: A type hint to analyze.

    Returns:
        The origin type (e.g., `Ref` for `Ref[T]`), or None if the hint
        is not a parameterized generic.
    """
    # First try the standard get_origin
    origin = get_origin(hint)
    if origin is not None:
        return origin
    # Fall back to checking __origin__ directly for our custom types
    if hasattr(hint, "__origin__"):
        return hint.__origin__
    return None


def _get_args(hint: Any) -> tuple[Any, ...]:
    """Get the type arguments of a type hint, handling custom _GenericAlias.

    This function extends `typing.get_args` to also handle our custom
    `_GenericAlias` class, which doesn't work with the standard function.

    Args:
        hint: A type hint to analyze.

    Returns:
        A tuple of type arguments (e.g., `(Network,)` for `Ref[Network]`),
        or an empty tuple if the hint has no type arguments.
    """
    # First try the standard get_args
    args = get_args(hint)
    if args:
        return args
    # Fall back to checking __args__ directly for our custom types
    if hasattr(hint, "__args__"):
        result: tuple[Any, ...] = hint.__args__
        return result
    return ()


def _analyze_type(field: str, hint: Any) -> RefInfo | None:
    """Analyze a type hint and return RefInfo if it's a reference type.

    This is an internal function that examines a single type hint and
    determines if it represents a reference type. If so, it constructs
    and returns the appropriate `RefInfo` object.

    Args:
        field: The name of the field being analyzed.
        hint: The type hint for the field.

    Returns:
        A `RefInfo` object if the hint is a reference type, None otherwise.
    """
    origin = _get_origin(hint)
    args = _get_args(hint)

    # Handle Optional / Union with None
    if origin is Union:
        # Check if it's Optional (Union with None)
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            # It's Optional[T] - analyze the inner type
            inner_info = _analyze_type(field, non_none_args[0])
            if inner_info is not None:
                return RefInfo(
                    field=inner_info.field,
                    target=inner_info.target,
                    attr=inner_info.attr,
                    is_list=inner_info.is_list,
                    is_dict=inner_info.is_dict,
                    is_optional=True,
                    is_context=inner_info.is_context,
                )
        return None

    # Handle Ref[T]
    if origin is Ref:
        if args:
            return RefInfo(field=field, target=args[0])
        return None

    # Handle Attr[T, "name"]
    if origin is Attr:
        if len(args) >= 2:
            attr_name = args[1]
            # Handle Literal["name"] - extract the actual string
            attr_origin = _get_origin(attr_name)
            if attr_origin is not None:
                literal_args = _get_args(attr_name)
                if literal_args:
                    attr_name = literal_args[0]
            return RefInfo(field=field, target=args[0], attr=attr_name)
        return None

    # Handle RefList[T]
    if origin is RefList:
        if args:
            return RefInfo(field=field, target=args[0], is_list=True)
        return None

    # Handle RefDict[K, V]
    if origin is RefDict:
        if len(args) >= 2:
            # The value type (args[1]) is the reference target
            return RefInfo(field=field, target=args[1], is_dict=True)
        return None

    # Handle ContextRef["name"]
    if origin is ContextRef:
        if args:
            context_name = args[0]
            # Handle Literal["name"] - extract the actual string
            context_origin = _get_origin(context_name)
            if context_origin is not None:
                literal_args = _get_args(context_name)
                if literal_args:
                    context_name = literal_args[0]
            # For ContextRef, target is None (no class target)
            return RefInfo(
                field=field,
                target=type(None),  # No class target for context refs
                attr=context_name,
                is_context=True,
            )
        return None

    return None


def get_dependencies(cls: type, transitive: bool = False) -> set[type]:
    """Compute the dependency graph for a class.

    Extracts all classes that the given class references through `Ref`,
    `Attr`, `RefList`, or `RefDict` fields. This enables:

    - Topological sorting for creation/deletion ordering
    - Cycle detection in reference graphs
    - Impact analysis for changes

    By default, only direct dependencies are returned. Set `transitive=True`
    to compute the full transitive closure (all dependencies, including
    dependencies of dependencies).

    Args:
        cls: The class to analyze.
        transitive: If True, include all transitive dependencies.
            If False (default), include only direct dependencies.

    Returns:
        A set of classes that the given class depends on. `ContextRef`
        fields are not included as dependencies since they don't reference
        other classes in the graph.

    Example:
        Computing dependencies::

            from dataclasses import dataclass
            from graph_refs import Ref, get_dependencies

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

            # Direct dependencies only
            deps = get_dependencies(Instance)
            print(deps)  # {<class 'Subnet'>}

            # Transitive dependencies
            all_deps = get_dependencies(Instance, transitive=True)
            print(all_deps)  # {<class 'Subnet'>, <class 'Network'>}

        Use case - topological sort for creation order::

            from graph_refs import get_dependencies

            def creation_order(classes):
                '''Return classes sorted by dependency order.'''
                result = []
                remaining = set(classes)

                while remaining:
                    # Find classes with no unprocessed dependencies
                    ready = [
                        c for c in remaining
                        if get_dependencies(c) <= set(result)
                    ]
                    if not ready:
                        raise ValueError("Circular dependency detected")
                    result.extend(ready)
                    remaining -= set(ready)

                return result

    See Also:
        - `get_refs`: For detailed information about each reference field.
    """
    refs = get_refs(cls)
    # Exclude context refs since they don't reference other classes
    deps = {info.target for info in refs.values() if not info.is_context}
    # Remove None type (from ContextRef which has target=type(None))
    deps.discard(type(None))

    if not transitive:
        return deps

    # Compute transitive closure using iterative approach
    visited: set[type] = set()
    to_visit = list(deps)

    while to_visit:
        current = to_visit.pop()
        if current in visited:
            continue
        visited.add(current)

        try:
            nested_deps = get_dependencies(current, transitive=False)
            to_visit.extend(nested_deps - visited)
        except Exception:
            # If we can't analyze a dependency (e.g., it's not a class
            # with type hints), skip it gracefully
            pass

    return visited
