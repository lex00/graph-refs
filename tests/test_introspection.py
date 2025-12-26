"""Tests for graph_refs introspection API."""

from dataclasses import dataclass
from typing import Literal, Union

from graph_refs import (
    Attr,
    ContextRef,
    Ref,
    RefDict,
    RefInfo,
    RefList,
    get_dependencies,
    get_refs,
)


class TestGetRefs:
    """Tests for get_refs function."""

    def test_simple_ref(self) -> None:
        """get_refs should detect Ref[T] fields."""

        class Network:
            pass

        @dataclass
        class Subnet:
            network: Ref[Network]
            cidr: str

        refs = get_refs(Subnet)
        assert "network" in refs
        assert refs["network"].target is Network
        assert refs["network"].attr is None
        assert refs["network"].is_list is False
        assert refs["network"].is_optional is False

    def test_attr_ref(self) -> None:
        """get_refs should detect Attr[T, name] fields."""

        class Role:
            pass

        @dataclass
        class Function:
            role_arn: Attr[Role, "Arn"]

        refs = get_refs(Function)
        assert "role_arn" in refs
        assert refs["role_arn"].target is Role
        assert refs["role_arn"].attr == "Arn"

    def test_attr_ref_with_literal(self) -> None:
        """get_refs should handle Attr[T, Literal[name]]."""

        class Role:
            pass

        @dataclass
        class Function:
            role_arn: Attr[Role, Literal["Arn"]]

        refs = get_refs(Function)
        assert "role_arn" in refs
        assert refs["role_arn"].target is Role
        assert refs["role_arn"].attr == "Arn"

    def test_reflist(self) -> None:
        """get_refs should detect RefList[T] fields."""

        class Instance:
            pass

        @dataclass
        class LoadBalancer:
            targets: RefList[Instance]

        refs = get_refs(LoadBalancer)
        assert "targets" in refs
        assert refs["targets"].target is Instance
        assert refs["targets"].is_list is True

    def test_refdict(self) -> None:
        """get_refs should detect RefDict[K, V] fields."""

        class Endpoint:
            pass

        @dataclass
        class Router:
            routes: RefDict[str, Endpoint]

        refs = get_refs(Router)
        assert "routes" in refs
        assert refs["routes"].target is Endpoint
        assert refs["routes"].is_dict is True

    def test_optional_ref(self) -> None:
        """get_refs should detect optional references."""

        class Gateway:
            pass

        @dataclass
        class Subnet:
            gateway: Ref[Gateway] | None

        refs = get_refs(Subnet)
        assert "gateway" in refs
        assert refs["gateway"].target is Gateway
        assert refs["gateway"].is_optional is True

    def test_context_ref(self) -> None:
        """get_refs should detect ContextRef fields."""

        @dataclass
        class Resource:
            region: ContextRef["region"]

        refs = get_refs(Resource)
        assert "region" in refs
        assert refs["region"].is_context is True
        assert refs["region"].attr == "region"

    def test_non_ref_fields_excluded(self) -> None:
        """get_refs should not include non-reference fields."""

        class Network:
            pass

        @dataclass
        class Subnet:
            network: Ref[Network]
            cidr: str
            count: int

        refs = get_refs(Subnet)
        assert "network" in refs
        assert "cidr" not in refs
        assert "count" not in refs

    def test_multiple_refs(self) -> None:
        """get_refs should detect multiple reference fields."""

        class Network:
            pass

        class SecurityGroup:
            pass

        @dataclass
        class Instance:
            network: Ref[Network]
            security_group: Ref[SecurityGroup]

        refs = get_refs(Instance)
        assert len(refs) == 2
        assert "network" in refs
        assert "security_group" in refs


class TestGetDependencies:
    """Tests for get_dependencies function."""

    def test_direct_dependencies(self) -> None:
        """get_dependencies should return direct dependencies."""

        class Network:
            pass

        @dataclass
        class Subnet:
            network: Ref[Network]

        deps = get_dependencies(Subnet)
        assert Network in deps
        assert len(deps) == 1

    def test_multiple_dependencies(self) -> None:
        """get_dependencies should return multiple dependencies."""

        class Network:
            pass

        class SecurityGroup:
            pass

        @dataclass
        class Instance:
            network: Ref[Network]
            security_group: Ref[SecurityGroup]

        deps = get_dependencies(Instance)
        assert Network in deps
        assert SecurityGroup in deps
        assert len(deps) == 2

    def test_transitive_dependencies(self) -> None:
        """get_dependencies with transitive=True should follow the graph."""

        class Network:
            cidr: str

        @dataclass
        class Subnet:
            network: Ref[Network]

        @dataclass
        class Instance:
            subnet: Ref[Subnet]

        # Direct only
        direct_deps = get_dependencies(Instance, transitive=False)
        assert Subnet in direct_deps
        assert Network not in direct_deps

        # Transitive
        all_deps = get_dependencies(Instance, transitive=True)
        assert Subnet in all_deps
        assert Network in all_deps

    def test_no_dependencies(self) -> None:
        """get_dependencies should return empty set for no refs."""

        @dataclass
        class Simple:
            name: str
            count: int

        deps = get_dependencies(Simple)
        assert len(deps) == 0

    def test_context_refs_excluded(self) -> None:
        """get_dependencies should not include ContextRef as dependencies."""

        class Network:
            pass

        @dataclass
        class Resource:
            network: Ref[Network]
            region: ContextRef["region"]

        deps = get_dependencies(Resource)
        assert Network in deps
        assert len(deps) == 1  # Only Network, not the context


class TestRefInfo:
    """Tests for RefInfo dataclass."""

    def test_refinfo_creation(self) -> None:
        """RefInfo should be creatable with required fields."""

        class Target:
            pass

        info = RefInfo(field="my_field", target=Target)
        assert info.field == "my_field"
        assert info.target is Target
        assert info.attr is None
        assert info.is_list is False
        assert info.is_dict is False
        assert info.is_optional is False

    def test_refinfo_with_attr(self) -> None:
        """RefInfo should support attr field."""

        class Target:
            pass

        info = RefInfo(field="my_field", target=Target, attr="Arn")
        assert info.attr == "Arn"

    def test_refinfo_frozen(self) -> None:
        """RefInfo should be immutable."""
        from dataclasses import FrozenInstanceError

        import pytest

        class Target:
            pass

        info = RefInfo(field="my_field", target=Target)
        with pytest.raises(FrozenInstanceError):
            info.field = "other"  # type: ignore


class TestErrorHandling:
    """Tests for error handling in introspection functions."""

    def test_get_refs_unresolvable_forward_ref(self) -> None:
        """get_refs should return empty dict for unresolvable forward refs."""

        @dataclass
        class Broken:
            ref: "NonExistentClass"  # type: ignore  # noqa: F821

        # Should not raise, should return empty dict
        refs = get_refs(Broken)
        assert refs == {}

    def test_get_refs_non_class_input(self) -> None:
        """get_refs should handle non-class input gracefully."""
        # Passing a string instead of a class
        refs = get_refs("not a class")  # type: ignore
        assert refs == {}

        # Passing None
        refs = get_refs(None)  # type: ignore
        assert refs == {}

        # Passing an integer
        refs = get_refs(42)  # type: ignore
        assert refs == {}

    def test_get_refs_class_without_annotations(self) -> None:
        """get_refs should return empty dict for classes without annotations."""

        class NoAnnotations:
            def __init__(self) -> None:
                self.x = 1

        refs = get_refs(NoAnnotations)
        assert refs == {}

    def test_get_dependencies_transitive_with_failures(self) -> None:
        """get_dependencies should handle failures in transitive analysis."""

        class Network:
            pass

        @dataclass
        class Subnet:
            network: Ref[Network]

        @dataclass
        class Instance:
            subnet: Ref[Subnet]

        # Should complete without error even if some classes fail analysis
        deps = get_dependencies(Instance, transitive=True)
        assert Subnet in deps
        assert Network in deps


class TestUnionTypes:
    """Tests for Union type handling edge cases."""

    def test_union_with_non_ref_type(self) -> None:
        """get_refs should not match Ref[T] | str as optional ref."""

        class Network:
            pass

        @dataclass
        class MixedUnion:
            network: Ref[Network] | str

        # This is not a simple Optional[Ref[T]], so it should not be detected
        refs = get_refs(MixedUnion)
        assert refs == {}

    def test_union_of_two_refs(self) -> None:
        """get_refs should not match Union of two different refs."""

        class NetworkA:
            pass

        class NetworkB:
            pass

        @dataclass
        class DoubleRef:
            network: Ref[NetworkA] | Ref[NetworkB]

        # Neither is None, so this is not Optional - should not match
        refs = get_refs(DoubleRef)
        assert refs == {}

    def test_optional_using_typing_union(self) -> None:
        """get_refs should detect Optional using Union[T, None] syntax."""

        class Network:
            pass

        @dataclass
        class OldStyleOptional:
            network: Union[Ref[Network], None]

        refs = get_refs(OldStyleOptional)
        assert "network" in refs
        assert refs["network"].target is Network
        assert refs["network"].is_optional is True

    def test_triple_union(self) -> None:
        """get_refs should not match Ref[T] | None | int as optional ref."""

        class Network:
            pass

        @dataclass
        class TripleUnion:
            network: Ref[Network] | None | int

        # More than 2 args in union - should not be treated as Optional
        refs = get_refs(TripleUnion)
        assert refs == {}


class TestNestedGenerics:
    """Tests for nested generic type handling."""

    def test_reflist_of_reflist(self) -> None:
        """get_refs should handle RefList[RefList[T]] gracefully."""

        class Item:
            pass

        @dataclass
        class Nested:
            items: RefList[RefList[Item]]

        # Should detect the outer RefList - inner type is RefList[Item]
        refs = get_refs(Nested)
        assert "items" in refs
        assert refs["items"].is_list is True
        # The target is RefList[Item], not Item directly

    def test_optional_reflist(self) -> None:
        """get_refs should detect optional RefList."""

        class Instance:
            pass

        @dataclass
        class OptionalList:
            targets: RefList[Instance] | None

        refs = get_refs(OptionalList)
        assert "targets" in refs
        assert refs["targets"].target is Instance
        assert refs["targets"].is_list is True
        assert refs["targets"].is_optional is True

    def test_optional_contextref(self) -> None:
        """get_refs should detect optional ContextRef."""

        @dataclass
        class OptionalContext:
            region: ContextRef["region"] | None

        refs = get_refs(OptionalContext)
        assert "region" in refs
        assert refs["region"].is_context is True
        assert refs["region"].is_optional is True
        assert refs["region"].attr == "region"
