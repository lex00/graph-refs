"""
Type definitions for graph references.

This module defines the core type markers used to express reference
relationships between dataclass instances. These types enable:

- Type-safe references between classes (`Ref[T]`)
- Attribute references (`Attr[T, "name"]`)
- Collection types (`RefList[T]`, `RefDict[K, V]`)
- Context value references (`ContextRef["name"]`)

All types are designed to work with standard Python type checkers (mypy, pyright)
and the typing module's introspection functions (`get_origin`, `get_args`).

Example:
    Basic usage with dataclasses::

        from dataclasses import dataclass
        from graph_refs import Ref, Attr

        @dataclass
        class Network:
            cidr: str

        @dataclass
        class Subnet:
            network: Ref[Network]  # Reference to Network
            cidr: str

        @dataclass
        class Instance:
            subnet: Ref[Subnet]
            role_arn: Attr[Role, "Arn"]  # Reference to Role's Arn attribute
"""

from typing import Any, Generic, TypeVar

__all__ = [
    "Ref",
    "Attr",
    "RefList",
    "RefDict",
    "ContextRef",
]

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
NameT = TypeVar("NameT")


class _RefMeta(type):
    """Metaclass that enables Ref[T] subscript syntax.

    This metaclass implements `__getitem__` to allow the `Ref[T]` syntax,
    returning a `_GenericAlias` that preserves the origin and type arguments
    for later introspection.
    """

    def __getitem__(cls, item: type[T]) -> Any:
        """Create a generic alias for Ref[T].

        Args:
            item: The type parameter T for the reference.

        Returns:
            A _GenericAlias representing Ref[T].
        """
        return _GenericAlias(cls, (item,))


class Ref(Generic[T], metaclass=_RefMeta):
    """A typed reference to an instance of type T.

    Use `Ref[T]` in type annotations to indicate that a field references
    another class. This enables type checkers to verify that only appropriate
    types are assigned, and enables frameworks to detect and process
    reference relationships.

    At runtime, `Ref[T]` is a type marker with no instances. The actual value
    assigned to a field annotated with `Ref[T]` can be:

    - The class T itself (for no-parens patterns in DSLs)
    - An instance of T
    - A reference descriptor or proxy object

    Attributes:
        __origin__: The Ref class itself (accessible via get_origin).
        __args__: A tuple containing the type parameter T.

    Example:
        Using Ref in a dataclass::

            from dataclasses import dataclass
            from graph_refs import Ref

            @dataclass
            class Network:
                cidr: str

            @dataclass
            class Subnet:
                network: Ref[Network]  # Must reference a Network
                cidr: str

        Type checker catches errors::

            subnet = Subnet(network=MyNetwork, cidr="10.0.1.0/24")  # OK
            subnet = Subnet(network=MyBucket, cidr="10.0.1.0/24")   # Type error!

    See Also:
        - `Attr`: For referencing specific attributes of a class.
        - `RefList`: For lists of references.
        - `get_refs`: For extracting reference information from a class.
    """

    __slots__ = ()


class _AttrMeta(type):
    """Metaclass that enables Attr[T, "name"] subscript syntax.

    This metaclass implements `__getitem__` to allow the `Attr[T, "name"]`
    syntax, returning a `_GenericAlias` that preserves both the target type
    and attribute name for later introspection.
    """

    def __getitem__(cls, args: tuple[type[T], str]) -> Any:
        """Create a generic alias for Attr[T, "name"].

        Args:
            args: A tuple of (target_type, attribute_name).

        Returns:
            A _GenericAlias representing Attr[T, "name"].

        Raises:
            TypeError: If args is not a tuple of exactly two elements.
        """
        if not isinstance(args, tuple) or len(args) != 2:
            raise TypeError("Attr requires exactly two arguments: Attr[T, 'name']")
        return _GenericAlias(cls, args)


class Attr(Generic[T, NameT], metaclass=_AttrMeta):
    """A typed reference to a specific attribute of type T.

    Use `Attr[T, "name"]` in type annotations to indicate that a field
    references a specific attribute of another class. This is useful when
    you need to reference a computed or derived value rather than the
    entire object.

    The attribute name can be specified as a string literal or using
    `typing.Literal` for additional type safety.

    Attributes:
        __origin__: The Attr class itself (accessible via get_origin).
        __args__: A tuple containing (target_type, attribute_name).

    Example:
        Using Attr in a dataclass::

            from dataclasses import dataclass
            from graph_refs import Attr

            @dataclass
            class Role:
                name: str
                # Assume Arn is a computed attribute

            @dataclass
            class Function:
                role_arn: Attr[Role, "Arn"]  # References Role's Arn attribute

        With Literal for stricter typing::

            from typing import Literal
            from graph_refs import Attr

            @dataclass
            class Function:
                role_arn: Attr[Role, Literal["Arn"]]

    See Also:
        - `Ref`: For referencing entire objects.
        - `get_refs`: For extracting reference information including attributes.
    """

    __slots__ = ()


class _RefListMeta(type):
    """Metaclass that enables RefList[T] subscript syntax.

    This metaclass implements `__getitem__` to allow the `RefList[T]` syntax,
    returning a `_GenericAlias` for introspection.
    """

    def __getitem__(cls, item: type[T]) -> Any:
        """Create a generic alias for RefList[T].

        Args:
            item: The type parameter T for the list elements.

        Returns:
            A _GenericAlias representing RefList[T].
        """
        return _GenericAlias(cls, (item,))


class RefList(Generic[T], metaclass=_RefListMeta):
    """A list of references to type T.

    `RefList[T]` is a semantic alias for `list[Ref[T]]` that signals to
    frameworks that each element in the list should be processed as a
    reference. This provides clearer intent and enables frameworks to
    apply reference-specific logic to list elements.

    Attributes:
        __origin__: The RefList class itself (accessible via get_origin).
        __args__: A tuple containing the element type T.

    Example:
        Using RefList in a dataclass::

            from dataclasses import dataclass
            from graph_refs import RefList

            @dataclass
            class Instance:
                name: str

            @dataclass
            class LoadBalancer:
                targets: RefList[Instance]  # List of Instance references

        Introspection::

            from graph_refs import get_refs

            refs = get_refs(LoadBalancer)
            assert refs["targets"].is_list is True
            assert refs["targets"].target is Instance

    See Also:
        - `Ref`: For single references.
        - `RefDict`: For dictionaries with reference values.
    """

    __slots__ = ()


class _RefDictMeta(type):
    """Metaclass that enables RefDict[K, V] subscript syntax.

    This metaclass implements `__getitem__` to allow the `RefDict[K, V]`
    syntax, returning a `_GenericAlias` for introspection.
    """

    def __getitem__(cls, args: tuple[type[K], type[V]]) -> Any:
        """Create a generic alias for RefDict[K, V].

        Args:
            args: A tuple of (key_type, value_type).

        Returns:
            A _GenericAlias representing RefDict[K, V].

        Raises:
            TypeError: If args is not a tuple of exactly two elements.
        """
        if not isinstance(args, tuple) or len(args) != 2:
            raise TypeError("RefDict requires exactly two arguments: RefDict[K, V]")
        return _GenericAlias(cls, args)


class RefDict(Generic[K, V], metaclass=_RefDictMeta):
    """A dictionary with reference values.

    `RefDict[K, V]` is a semantic alias for `dict[K, Ref[V]]` that signals
    to frameworks that each value in the dictionary should be processed as
    a reference. The keys can be any hashable type.

    Attributes:
        __origin__: The RefDict class itself (accessible via get_origin).
        __args__: A tuple containing (key_type, value_type).

    Example:
        Using RefDict in a dataclass::

            from dataclasses import dataclass
            from graph_refs import RefDict

            @dataclass
            class Endpoint:
                url: str

            @dataclass
            class Router:
                routes: RefDict[str, Endpoint]  # String keys, Endpoint references

        Introspection::

            from graph_refs import get_refs

            refs = get_refs(Router)
            assert refs["routes"].is_dict is True
            assert refs["routes"].target is Endpoint

    See Also:
        - `RefList`: For lists of references.
        - `Ref`: For single references.
    """

    __slots__ = ()


class _ContextRefMeta(type):
    """Metaclass that enables ContextRef["name"] subscript syntax.

    This metaclass implements `__getitem__` to allow the `ContextRef["name"]`
    syntax, returning a `_GenericAlias` for introspection.
    """

    def __getitem__(cls, item: str) -> Any:
        """Create a generic alias for ContextRef["name"].

        Args:
            item: The context value name as a string.

        Returns:
            A _GenericAlias representing ContextRef["name"].
        """
        return _GenericAlias(cls, (item,))


class ContextRef(Generic[NameT], metaclass=_ContextRefMeta):
    """A reference to a context value resolved at runtime.

    Use `ContextRef["name"]` to reference values that are provided by a
    context object at serialization or evaluation time. This is distinct
    from resource references (`Ref[T]`) which reference other objects in
    the graph.

    Common use cases include:

    - Environment-specific values (region, environment name)
    - Runtime configuration (account IDs, project names)
    - Pseudo-parameters in infrastructure-as-code

    Attributes:
        __origin__: The ContextRef class itself (accessible via get_origin).
        __args__: A tuple containing the context value name.

    Example:
        Using ContextRef in a dataclass::

            from dataclasses import dataclass
            from graph_refs import ContextRef

            @dataclass
            class Resource:
                region: ContextRef["region"]
                account_id: ContextRef["account_id"]

        Introspection::

            from graph_refs import get_refs

            refs = get_refs(Resource)
            assert refs["region"].is_context is True
            assert refs["region"].attr == "region"

    See Also:
        - `Ref`: For references to other objects in the graph.
        - `get_refs`: For extracting reference information.
    """

    __slots__ = ()


class _GenericAlias:
    """A generic alias that preserves origin and args for introspection.

    This class makes `Ref[T]`, `Attr[T, "name"]`, and other parameterized
    types compatible with the typing module's introspection functions
    (`get_origin`, `get_args`) and supports the union operator (`|`) for
    optional types.

    Attributes:
        __origin__: The original generic class (e.g., Ref, Attr).
        __args__: The type arguments as a tuple.

    Example:
        Introspection with _GenericAlias::

            from graph_refs import Ref

            ref_type = Ref[MyClass]
            assert ref_type.__origin__ is Ref
            assert ref_type.__args__ == (MyClass,)

        Using with Optional::

            from graph_refs import Ref

            optional_ref = Ref[MyClass] | None
            # Creates typing.Union[Ref[MyClass], None]
    """

    __slots__ = ("__origin__", "__args__")

    def __init__(self, origin: type, args: tuple[Any, ...]) -> None:
        """Initialize a generic alias.

        Args:
            origin: The original generic class (e.g., Ref, Attr).
            args: The type arguments as a tuple.
        """
        self.__origin__ = origin
        self.__args__ = args

    def __repr__(self) -> str:
        """Return a string representation of the generic alias.

        Returns:
            A string in the format "ClassName[arg1, arg2, ...]".
        """
        args_str = ", ".join(
            arg.__name__ if isinstance(arg, type) else repr(arg)
            for arg in self.__args__
        )
        return f"{self.__origin__.__name__}[{args_str}]"

    def __eq__(self, other: object) -> bool:
        """Check equality with another generic alias.

        Args:
            other: The object to compare with.

        Returns:
            True if both have the same origin and args, False otherwise.
        """
        if isinstance(other, _GenericAlias):
            return (
                self.__origin__ == other.__origin__
                and self.__args__ == other.__args__
            )
        return False

    def __hash__(self) -> int:
        """Return a hash value for the generic alias.

        Returns:
            A hash based on the origin and args.
        """
        return hash((self.__origin__, self.__args__))

    def __or__(self, other: Any) -> Any:
        """Support for `Ref[T] | None` syntax.

        Args:
            other: The type to union with (typically None).

        Returns:
            A typing.Union of this alias and the other type.
        """
        import typing

        return typing.Union[self, other]

    def __ror__(self, other: Any) -> Any:
        """Support for `None | Ref[T]` syntax.

        Args:
            other: The type to union with (typically None).

        Returns:
            A typing.Union of the other type and this alias.
        """
        import typing

        return typing.Union[other, self]
