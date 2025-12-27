# Demo: What graph-refs Does Today

The [`demo.py`](demo.py) example demonstrates the current capabilities of graph-refs and clarifies the boundary between what the library provides and what frameworks build on top of it.

## What graph-refs Provides

**Type markers** that work with type checkers today:
- `Ref[T]` — Reference to a class
- `Attr[T, "name"]` — Reference to an attribute
- `RefList[T]`, `RefDict[K, V]` — Collection variants
- `ContextRef["name"]` — Runtime context references

**Introspection API** for analyzing classes at runtime:
- `get_refs(cls)` — Extract reference fields from annotations
- `get_dependencies(cls, transitive=True)` — Compute dependency graphs

## What Frameworks Add

The demo includes a minimal `@infra` decorator to illustrate how a framework would build on graph-refs:

- **Decorators** that register and process resources
- **Serialization** to target formats (CloudFormation, Terraform, etc.)
- **Validation** that references point to valid resources
- **Ordering** using `get_dependencies()` for creation order

## Run the Demo

```bash
python examples/demo.py
```

This will show:
1. Reference extraction from type annotations
2. Dependency graph computation
3. Topological sort for creation order
4. Clear distinction between library and framework territory

## Further Reading

- [RATIONALE.md](../docs/RATIONALE.md) — Design principles and rationale
- [PATTERN.md](../docs/PATTERN.md) — Full guide to the declarative dataclass pattern
