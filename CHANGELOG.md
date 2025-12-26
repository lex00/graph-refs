# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-12-26

### Added

- Initial release
- Core type markers:
  - `Ref[T]` - typed reference to another class
  - `Attr[T, "name"]` - typed reference to a class attribute
  - `RefList[T]` - list of references
  - `RefDict[K, V]` - dictionary with reference values
  - `ContextRef["name"]` - reference to context values
- Introspection API:
  - `get_refs(cls)` - extract reference information from a class
  - `get_dependencies(cls, transitive=False)` - compute dependency graph
  - `RefInfo` - dataclass containing reference metadata
- Full support for:
  - Optional references (`Ref[T] | None`)
  - Union syntax (both `Union[Ref[T], None]` and `Ref[T] | None`)
  - Nested generics (`RefList[RefList[T]]`)
  - Dataclass inheritance
  - Circular/self-referential classes
- Type checker compatibility (mypy, pyright)
- Zero runtime dependencies
- Python 3.10+ support
- Comprehensive test suite (61 tests, 93% coverage)
- Google-style docstrings throughout
- pdoc-generated API documentation

[unreleased]: https://github.com/lex00/graph-refs/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/lex00/graph-refs/releases/tag/v0.1.0
