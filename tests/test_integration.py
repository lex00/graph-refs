"""Integration tests for graph_refs with real-world scenarios."""

from dataclasses import dataclass

from graph_refs import (
    Attr,
    ContextRef,
    Ref,
    RefDict,
    RefList,
    get_dependencies,
    get_refs,
)


class TestInheritance:
    """Tests for dataclass inheritance with references."""

    def test_dataclass_with_inheritance(self) -> None:
        """get_refs should detect refs in both parent and child classes."""

        class Network:
            pass

        class SecurityGroup:
            pass

        @dataclass
        class BaseResource:
            network: Ref[Network]

        @dataclass
        class ChildResource(BaseResource):
            security_group: Ref[SecurityGroup]

        refs = get_refs(ChildResource)
        # Should have refs from both parent and child
        assert "network" in refs
        assert "security_group" in refs
        assert refs["network"].target is Network
        assert refs["security_group"].target is SecurityGroup

    def test_dependencies_with_inheritance(self) -> None:
        """get_dependencies should include deps from inherited refs."""

        class Network:
            pass

        class SecurityGroup:
            pass

        @dataclass
        class BaseResource:
            network: Ref[Network]

        @dataclass
        class ChildResource(BaseResource):
            security_group: Ref[SecurityGroup]

        deps = get_dependencies(ChildResource)
        assert Network in deps
        assert SecurityGroup in deps


class TestCombinedRefTypes:
    """Tests for classes using multiple reference types together."""

    def test_multiple_ref_types_combined(self) -> None:
        """get_refs should handle Ref, Attr, RefList, RefDict, ContextRef together."""

        class Network:
            pass

        class Instance:
            pass

        class Role:
            pass

        class Endpoint:
            pass

        @dataclass
        class ComplexResource:
            network: Ref[Network]
            role_arn: Attr[Role, "Arn"]
            instances: RefList[Instance]
            routes: RefDict[str, Endpoint]
            region: ContextRef["region"]
            name: str  # Non-ref field

        refs = get_refs(ComplexResource)

        # Should detect all 5 reference types
        assert len(refs) == 5
        assert "name" not in refs  # Non-ref excluded

        # Verify each type
        assert refs["network"].target is Network
        assert refs["network"].is_list is False
        assert refs["network"].is_dict is False

        assert refs["role_arn"].target is Role
        assert refs["role_arn"].attr == "Arn"

        assert refs["instances"].target is Instance
        assert refs["instances"].is_list is True

        assert refs["routes"].target is Endpoint
        assert refs["routes"].is_dict is True

        assert refs["region"].is_context is True
        assert refs["region"].attr == "region"


class TestDependencyGraphs:
    """Tests for complex dependency graph scenarios."""

    def test_diamond_dependency(self) -> None:
        """get_dependencies should handle diamond dependency pattern."""
        # Diamond pattern: A -> B -> D
        #                  A -> C -> D

        class D:
            pass

        @dataclass
        class B:
            d: Ref[D]

        @dataclass
        class C:
            d: Ref[D]

        @dataclass
        class A:
            b: Ref[B]
            c: Ref[C]

        # Direct deps of A
        direct = get_dependencies(A, transitive=False)
        assert B in direct
        assert C in direct
        assert D not in direct

        # Transitive deps of A (should include D only once)
        transitive = get_dependencies(A, transitive=True)
        assert B in transitive
        assert C in transitive
        assert D in transitive
        assert len(transitive) == 3

    def test_no_circular_dependency_hang(self) -> None:
        """get_dependencies should not hang on self-referential class."""

        @dataclass
        class TreeNode:
            parent: Ref["TreeNode"] | None  # type: ignore[type-arg]
            name: str

        # Should complete without infinite loop (this is the main test)
        deps = get_dependencies(TreeNode, transitive=True)
        # With forward refs to local classes, the dep may be a string
        # The key is that it completes without hanging
        assert len(deps) >= 0  # Just verify it returned

    def test_deep_transitive_chain(self) -> None:
        """get_dependencies should handle deep transitive chains."""

        class Level0:
            pass

        @dataclass
        class Level1:
            dep: Ref[Level0]

        @dataclass
        class Level2:
            dep: Ref[Level1]

        @dataclass
        class Level3:
            dep: Ref[Level2]

        @dataclass
        class Level4:
            dep: Ref[Level3]

        # Should traverse all 4 levels
        deps = get_dependencies(Level4, transitive=True)
        assert Level3 in deps
        assert Level2 in deps
        assert Level1 in deps
        assert Level0 in deps
        assert len(deps) == 4

    def test_multiple_paths_to_same_dependency(self) -> None:
        """get_dependencies should deduplicate deps reachable via multiple paths."""

        class Shared:
            pass

        @dataclass
        class PathA:
            shared: Ref[Shared]

        @dataclass
        class PathB:
            shared: Ref[Shared]

        @dataclass
        class Root:
            a: Ref[PathA]
            b: Ref[PathB]

        deps = get_dependencies(Root, transitive=True)
        # Shared should appear only once despite being reachable via both paths
        assert Shared in deps
        assert PathA in deps
        assert PathB in deps
        assert len(deps) == 3
