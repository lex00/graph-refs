# Contributing to graph-refs

Thank you for your interest in contributing to graph-refs! This library aims to become part of the Python standard library or `typing_extensions`, so contributions must meet high standards for quality, compatibility, and design.

## Design Constraints

Before contributing, understand these non-negotiable constraints:

1. **Zero dependencies** — Only Python stdlib imports allowed
2. **Python 3.10+** — Must work with Python 3.10 and later
3. **Type checker compatibility** — Must work with mypy and pyright
4. **Runtime minimal** — Types are markers; heavy logic belongs in frameworks using this library

## Getting Started

### Prerequisites

- Python 3.10+
- Git
- uv (recommended) or pip

### Development Setup

```bash
# Clone the repository
git clone https://github.com/lex00/graph-refs.git
cd graph-refs

# Create virtual environment and install dependencies
uv sync --all-extras

# Or with pip
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=graph_refs --cov-report=term-missing

# Run type checking
uv run mypy src/
uv run pyright src/
```

### Code Style

```bash
# Format code
uv run black src/ tests/

# Lint code
uv run ruff check src/ tests/

# Fix auto-fixable issues
uv run ruff check --fix src/ tests/
```

## Types of Contributions

### Bug Reports

When filing a bug report, include:

1. Python version
2. Type checker and version (if relevant)
3. Minimal reproduction case
4. Expected behavior
5. Actual behavior

### Feature Requests

Before proposing a feature:

1. Check if it aligns with the [design philosophy](PHILOSOPHY.md)
2. Consider if it belongs in graph-refs or in a framework using it
3. Ensure it maintains zero-dependency constraint
4. Verify type checker compatibility is feasible

### Code Contributions

#### For new type markers

1. Add type definition to `_types.py`
2. Add introspection support to `_introspection.py`
3. Add comprehensive tests
4. Add type checker tests (mypy, pyright)
5. Update documentation

#### For introspection API changes

1. Ensure backwards compatibility
2. Consider performance implications
3. Add edge case tests (Optional, Union, forward refs)
4. Verify type checker behavior

## Code Guidelines

### Type Definitions

Type markers should be:
- Generic where appropriate
- Compatible with `get_origin()` and `get_args()`
- Recognized by type checkers
- Minimal at runtime

```python
# Good: Simple, compatible
class Ref(Generic[T]):
    __slots__ = ()

    def __class_getitem__(cls, item: type[T]) -> type["Ref[T]"]:
        return _GenericAlias(cls, (item,))

# Bad: Too much runtime logic
class Ref(Generic[T]):
    def __init__(self, target: T):  # No instantiation needed
        self.target = target
```

### Introspection Functions

Introspection should be:
- Pure functions (no side effects)
- Cached where beneficial
- Handle edge cases gracefully

```python
# Good: Handles edge cases
def get_refs(cls: type) -> dict[str, RefInfo]:
    hints = get_type_hints(cls, include_extras=True)
    # Handle ForwardRef, Optional, Union...

# Bad: Assumes happy path
def get_refs(cls: type) -> dict[str, RefInfo]:
    hints = cls.__annotations__  # Doesn't resolve forward refs
```

### Tests

Tests should cover:
- Basic functionality
- Edge cases (None, Union, forward refs)
- Type checker behavior
- Error conditions

```python
def test_ref_basic():
    """Ref[T] should be recognized as a reference."""

def test_ref_with_optional():
    """Ref[T] | None should have is_optional=True."""

def test_ref_forward_reference():
    """Ref["ClassName"] should resolve correctly."""
```

## Pull Request Process

1. **Before submitting:**
   - All tests pass (`uv run pytest`)
   - Type checks pass (`uv run mypy src/`)
   - Code is formatted (`uv run black src/ tests/`)
   - Linting passes (`uv run ruff check src/ tests/`)

2. **PR description should include:**
   - Summary of changes
   - Motivation (why is this needed?)
   - Type checker compatibility notes
   - Breaking changes (if any)

3. **Review criteria:**
   - Maintains zero-dependency constraint
   - Works with mypy and pyright
   - Follows existing code patterns
   - Includes appropriate tests
   - Documentation updated

## Commit Messages

Use clear, descriptive commit messages:

```
feat: add RefSet type for unordered reference collections

fix: handle ForwardRef in get_dependencies

docs: clarify Attr[T, name] behavior with ClassVar

test: add edge cases for Optional[Ref[T]]
```

## Standards Track Considerations

This library is designed for potential stdlib inclusion. Contributions should consider:

1. **API stability** — Changes should be backwards compatible
2. **Minimal surface** — Prefer fewer, well-designed primitives
3. **Type system fit** — Should feel natural alongside existing typing constructs
4. **Documentation quality** — Clear, precise documentation required

## Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** — Incompatible API changes
- **MINOR** — New functionality, backwards compatible
- **PATCH** — Bug fixes, backwards compatible

### Version Locations

The version is stored in two places that must stay in sync:

| File | Location |
|------|----------|
| `pyproject.toml` | Line 3: `version = "X.Y.Z"` |
| `src/graph_refs/__init__.py` | `__version__ = "X.Y.Z"` |

### Bumping Versions

Use the provided script to update both locations:

```bash
# Bump patch version (0.1.0 → 0.1.1)
python scripts/bump_version.py patch

# Bump minor version (0.1.0 → 0.2.0)
python scripts/bump_version.py minor

# Bump major version (0.1.0 → 1.0.0)
python scripts/bump_version.py major

# Set specific version
python scripts/bump_version.py 2.0.0
```

### Changelog

Update `CHANGELOG.md` when making releases:

1. Move items from `[Unreleased]` to a new version section
2. Add the release date
3. Categorize changes: Added, Changed, Deprecated, Removed, Fixed, Security

## Questions?

- Open a GitHub issue for bugs or features
- Start a GitHub discussion for design questions
- Read [PHILOSOPHY.md](PHILOSOPHY.md) for design rationale

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 license.
