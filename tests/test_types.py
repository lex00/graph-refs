"""Tests for graph_refs type definitions."""

from graph_refs import Attr, ContextRef, Ref, RefDict, RefList


class TestRef:
    """Tests for Ref[T] type."""

    def test_ref_getitem(self) -> None:
        """Ref[T] should return a generic alias."""

        class MyClass:
            pass

        ref_type = Ref[MyClass]
        assert ref_type is not None

    def test_ref_origin(self) -> None:
        """Ref[T] should have correct __origin__."""

        class MyClass:
            pass

        ref_type = Ref[MyClass]
        assert ref_type.__origin__ is Ref

    def test_ref_args(self) -> None:
        """Ref[T] should have correct __args__."""

        class MyClass:
            pass

        ref_type = Ref[MyClass]
        assert ref_type.__args__ == (MyClass,)

    def test_ref_repr(self) -> None:
        """Ref[T] should have readable repr."""

        class Network:
            pass

        ref_type = Ref[Network]
        assert "Ref" in repr(ref_type)
        assert "Network" in repr(ref_type)

    def test_ref_equality(self) -> None:
        """Ref[T] should be equal to itself."""

        class MyClass:
            pass

        assert Ref[MyClass] == Ref[MyClass]

    def test_ref_inequality(self) -> None:
        """Ref[T] should not equal Ref[U] for different types."""

        class A:
            pass

        class B:
            pass

        assert Ref[A] != Ref[B]


class TestAttr:
    """Tests for Attr[T, name] type."""

    def test_attr_getitem(self) -> None:
        """Attr[T, name] should return a generic alias."""

        class Role:
            pass

        attr_type = Attr[Role, "Arn"]
        assert attr_type is not None

    def test_attr_origin(self) -> None:
        """Attr[T, name] should have correct __origin__."""

        class Role:
            pass

        attr_type = Attr[Role, "Arn"]
        assert attr_type.__origin__ is Attr

    def test_attr_args(self) -> None:
        """Attr[T, name] should have correct __args__."""

        class Role:
            pass

        attr_type = Attr[Role, "Arn"]
        assert attr_type.__args__ == (Role, "Arn")

    def test_attr_requires_two_args(self) -> None:
        """Attr should require exactly two arguments."""
        import pytest

        class Role:
            pass

        with pytest.raises(TypeError):
            Attr[Role]  # type: ignore


class TestRefList:
    """Tests for RefList[T] type."""

    def test_reflist_getitem(self) -> None:
        """RefList[T] should return a generic alias."""

        class Instance:
            pass

        reflist_type = RefList[Instance]
        assert reflist_type is not None

    def test_reflist_origin(self) -> None:
        """RefList[T] should have correct __origin__."""

        class Instance:
            pass

        reflist_type = RefList[Instance]
        assert reflist_type.__origin__ is RefList

    def test_reflist_args(self) -> None:
        """RefList[T] should have correct __args__."""

        class Instance:
            pass

        reflist_type = RefList[Instance]
        assert reflist_type.__args__ == (Instance,)


class TestRefDict:
    """Tests for RefDict[K, V] type."""

    def test_refdict_getitem(self) -> None:
        """RefDict[K, V] should return a generic alias."""

        class Endpoint:
            pass

        refdict_type = RefDict[str, Endpoint]
        assert refdict_type is not None

    def test_refdict_origin(self) -> None:
        """RefDict[K, V] should have correct __origin__."""

        class Endpoint:
            pass

        refdict_type = RefDict[str, Endpoint]
        assert refdict_type.__origin__ is RefDict

    def test_refdict_args(self) -> None:
        """RefDict[K, V] should have correct __args__."""

        class Endpoint:
            pass

        refdict_type = RefDict[str, Endpoint]
        assert refdict_type.__args__ == (str, Endpoint)

    def test_refdict_requires_two_args(self) -> None:
        """RefDict should require exactly two arguments."""
        import pytest

        class Endpoint:
            pass

        with pytest.raises(TypeError):
            RefDict[Endpoint]  # type: ignore


class TestContextRef:
    """Tests for ContextRef[name] type."""

    def test_contextref_getitem(self) -> None:
        """ContextRef[name] should return a generic alias."""
        contextref_type = ContextRef["region"]
        assert contextref_type is not None

    def test_contextref_origin(self) -> None:
        """ContextRef[name] should have correct __origin__."""
        contextref_type = ContextRef["region"]
        assert contextref_type.__origin__ is ContextRef

    def test_contextref_args(self) -> None:
        """ContextRef[name] should have correct __args__."""
        contextref_type = ContextRef["region"]
        assert contextref_type.__args__ == ("region",)


class TestEdgeCases:
    """Tests for edge cases in type system."""

    def test_ref_hash_consistency(self) -> None:
        """Ref[T] should have consistent hash values."""

        class MyClass:
            pass

        ref1 = Ref[MyClass]
        ref2 = Ref[MyClass]
        # Equal objects must have equal hashes
        assert ref1 == ref2
        assert hash(ref1) == hash(ref2)

    def test_ref_inequality_with_non_alias(self) -> None:
        """Ref[T] should not equal non-_GenericAlias objects."""

        class MyClass:
            pass

        ref_type = Ref[MyClass]
        assert ref_type != "not an alias"
        assert ref_type != 42
        assert ref_type != None  # noqa: E711
        assert ref_type != MyClass

    def test_attr_too_many_args(self) -> None:
        """Attr should reject more than two arguments."""
        import pytest

        class Role:
            pass

        with pytest.raises(TypeError):
            Attr[Role, "Arn", "extra"]  # type: ignore

    def test_refdict_too_many_args(self) -> None:
        """RefDict should reject more than two arguments."""
        import pytest

        class Endpoint:
            pass

        with pytest.raises(TypeError):
            RefDict[str, Endpoint, int]  # type: ignore

    def test_ref_union_with_none(self) -> None:
        """Ref[T] | None should create a Union type."""

        class MyClass:
            pass

        optional_ref = Ref[MyClass] | None
        # Should be a Union type
        from typing import Union, get_args, get_origin

        assert get_origin(optional_ref) is Union
        args = get_args(optional_ref)
        assert len(args) == 2
        assert type(None) in args

    def test_none_union_with_ref(self) -> None:
        """None | Ref[T] should also create a Union type (reverse order)."""

        class MyClass:
            pass

        optional_ref = None | Ref[MyClass]  # type: ignore[operator]
        from typing import Union, get_origin

        assert get_origin(optional_ref) is Union
