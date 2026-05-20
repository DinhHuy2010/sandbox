# DHForge Project Report

Generated on 2026-05-19.

## Executive Summary

DHForge is a small FastAPI application that exposes HTTP endpoints for inspecting and managing local Git repositories. The project is organized around clear layers:

- `dhforge/main.py` creates the FastAPI application, configures observability, and mounts routers under `/api/v1`.
- `dhforge/routes/` defines the public API surface for health checks, Git metadata, and repository operations.
- `dhforge/services/` contains service objects for Git subprocess execution, repository index management, and dependency construction.
- `dhforge/models/` contains response-domain models for Git commits, authors, and branches.
- `config.toml` points the app at a local JSON repository index and repository storage directory.

The codebase is compact and understandable, but it currently looks like an early prototype. Several route comments still say "Placeholder implementation", test coverage is absent, error handling is inconsistent, repository creation has behavioral mismatches, and the repository index format/path logic needs tightening before this service is reliable as a local repository management API.

## Project Purpose

The application appears intended to be a local Git repository management and inspection service. It can:

- Report service health.
- Report the installed Git binary version.
- List registered repositories from a JSON index.
- Retrieve repository metadata.
- Initialize and register new repositories.
- Remove repositories from the index.
- List commits and branches for a repository.
- Produce diffs between two commits.
- Create and delete branches through Git refs.

The project does not currently clone repositories, fetch remotes, inspect working tree status, commit changes, expose file trees, or perform authentication/authorization.

## Technology Stack

Runtime:

- Python `>=3.12`
- FastAPI
- Pydantic v2-style models and dataclasses
- Logfire for local observability and FastAPI instrumentation
- `content-negotiation` for root-route response selection
- System `git` binary invoked through async subprocesses

Declared dependencies in `pyproject.toml`:

- `content-negotiation>=2.0.1`
- `fastapi[standard]>=0.135.2`
- `logfire[fastapi]>=4.33.0`

Static analysis:

- Pyright configured with `typeCheckingMode = "standard"`

## Repository Structure

```text
.
├── app.py
├── config.toml
├── pyproject.toml
├── REPORT.md
├── dhforge/
│   ├── __init__.py
│   ├── config.py
│   ├── logger.py
│   ├── main.py
│   ├── models/
│   │   └── git.py
│   ├── routes/
│   │   ├── git.py
│   │   ├── health.py
│   │   └── repositories.py
│   └── services/
│       ├── deps.py
│       ├── git.py
│       └── repositories.py
└── repositories/
    ├── index.json
    ├── hello-world.git/
    └── logfire.git/
```

Runtime-generated files are present in the tree, including `__pycache__/` directories and `.logfire/logfire_credentials.json`. These should normally stay out of version control.

## Application Entry Point

`app.py` imports `app` from `dhforge.main` and runs Uvicorn when executed directly:

```python
uvicorn.run("app:app", log_config=None)
```

This supports both:

- `fastapi dev app.py` or equivalent ASGI tooling.
- `python app.py` for local development.

The root FastAPI application is defined in `dhforge/main.py`.

## HTTP API Surface

All API routes are mounted under `/api/v1`.

### Root Route

`GET /`

Uses content negotiation:

- Returns JSON when `Accept` resolves to `application/json`.
- Redirects to FastAPI docs when `Accept` resolves to `text/html`.
- Raises `406 Not Acceptable` for unsupported content types.

### Health

`GET /api/v1/health`

Returns:

```json
{"status": "ok"}
```

This is simple and appropriate for a liveness check. It does not validate dependencies such as config, index file access, or Git availability.

### Git

`GET /api/v1/git/version`

Returns the installed Git version using `git --version`. The value is cached by `GitService`.

### Repositories

`GET /api/v1/repositories`

Lists repository names from `repositories/index.json`.

`POST /api/v1/repositories`

Creates and registers a new repository. The request model contains both `name` and `path`, but the current implementation ignores `path` and creates a directory based only on `name`.

`GET /api/v1/repositories/{name}`

Returns the repository name and resolved filesystem path.

`DELETE /api/v1/repositories/{name}`

Removes the repository from the JSON index. It does not delete the underlying repository directory.

`GET /api/v1/repositories/{name}/commits`

Returns recent commits parsed from `git log`.

Query parameters:

- `count`: positive integer, defaults to `10`
- `start_from`: optional Git reference or commit hash

`GET /api/v1/repositories/{name}/branches`

Returns branches parsed from `git branch --format`.

`GET /api/v1/repositories/{name}/diff/{commit_a}/{commit_b}`

Returns plain text output from `git diff commit_a..commit_b`.

`POST /api/v1/repositories/{name}/branches`

Creates a branch by creating a Git ref under `refs/heads/{branch_name}`.

`DELETE /api/v1/repositories/{name}/branches/{branch_name:path}`

Deletes a branch by deleting its Git ref.

## Configuration

`config.toml`:

```toml
[repositories]
index-file = "repositories/index.json"
repositories-base-dir = "repositories"
```

`dhforge/config.py` defines:

- `RepositoriesConfig.index_file`
- `RepositoriesConfig.repositories_base_dir`
- `Config.repositories`
- `read_config()`

The app reads config from `config.toml` relative to the process working directory. This is convenient for local development but fragile when the process is started from another directory.

## Data Model

The repository index is JSON:

```json
{
  "repositories": [
    {
      "name": "hello-world",
      "path": "./hello-world.git"
    },
    {
      "name": "logfire",
      "path": "./logfire.git"
    }
  ]
}
```

Each repository entry has:

- `name`: public API identifier.
- `path`: path appended to `repositories-base-dir`.

Git API models:

- `Author`
  - `name`
  - `email`
- `Commit`
  - `hash`
  - `author`
  - `date`
  - `message`
- `Branch`
  - `name`
  - `is_current`
  - `commit_hash`

## Service Layer

### Dependency Construction

`dhforge/services/deps.py` keeps process-global singleton instances in `_singletons`.

Strengths:

- Simple to understand.
- Avoids repeatedly checking the Git binary path.
- Keeps Git version cache alive for the process.

Risks:

- Singletons are hard to reset in tests.
- `RepositoryService` captures the first loaded config and will not reflect config changes.
- No locking protects singleton creation under concurrent startup/load scenarios.

### GitService

`GitService` wraps Git commands using `asyncio.create_subprocess_exec`.

Strengths:

- Uses argument arrays instead of shell strings, which avoids shell injection.
- Supports async request handling without blocking the event loop during subprocess execution.
- Captures stderr and raises on non-zero exit.
- Uses Logfire spans around Git operations.

Limitations:

- All Git failures become generic `RuntimeError`.
- API routes generally do not translate Git failures into clear HTTP responses.
- There is no timeout for subprocesses.
- There is no allowlist or validation for refs passed into operations.
- Large diffs or command output are read fully into memory.
- The optional `stdin` parameter is exposed but not used elsewhere.

### RepositoryService

`RepositoryService` reads and writes the JSON repository index.

Strengths:

- Centralizes repository lookup and index mutation.
- Caches the index after first read.
- Invalidates the cache after writes.
- Resolves repository paths before use.

Limitations and bugs:

- `_read_index()` returns `Any`; there is no schema validation for the index file.
- `_write_index()` writes directly to the target file instead of using an atomic replace.
- Concurrent writes can race and lose updates.
- `add_repository()` creates a path as `repositories_base_dir / name`, but stores `str(path)` in the index.
- `get_repository()` later resolves paths as `repositories_base_dir / got["path"]`. For newly added repositories, this can become `repositories/repositories/{name}` depending on the stored path shape.
- `RepositoryCreateRequestModel.path` is ignored by the route and service.
- `add_repository()` uses `path.mkdir()` without `parents=True` and without `exist_ok`.
- Failure during `git init` can leave a created directory without an index entry.
- `remove_repository()` only removes the index entry; the repository directory remains on disk.

## Observability

`dhforge/logger.py` configures Logfire locally:

```python
logfire.configure(local=True)
```

`dhforge/main.py` instruments FastAPI with header capture enabled:

```python
logger.instrument_fastapi(app, capture_headers=True)
```

The service layer also adds spans for repository and Git operations.

Observability is a strong early choice for this project, but header capture can expose sensitive data. If the app ever handles authorization headers, cookies, tokens, or private network metadata, header capture should be reviewed and scrubbed.

## Error Handling

Current explicit HTTP handling:

- Unknown repository names become `404`.
- Duplicate repository creation in the route becomes `400`.
- Unsupported root content type becomes `406`.

Untranslated exceptions:

- Missing or malformed config.
- Missing or inaccessible repository index.
- Invalid repository index shape.
- Repository directory missing.
- Git command failures.
- Branch creation/deletion failures.
- Permission errors during directory creation or index writes.

These failures currently bubble up as generic server errors. For an API, they should usually become structured responses with stable status codes and messages.

## Security Analysis

Positive points:

- Git subprocess calls use `create_subprocess_exec` with argument lists, not shell command strings.
- Repository operations are scoped through named index entries for most endpoints.

Important risks:

- Branch names and commit references are accepted directly from API input and passed to Git.
- `RepositoryCreateRequestModel.path` suggests user-controlled paths may be intended, but the behavior is not defined.
- There is no authentication or authorization.
- The API can mutate repositories and Git refs.
- Header capture in Logfire may record sensitive request headers.
- The repository index can point outside the intended base directory if paths are crafted with `..` unless validation is added.
- There is no CSRF protection. If this service is browser-accessible on localhost, mutating endpoints could be reached by malicious local-web interactions unless protected.

Recommended guardrails:

- Add authentication before exposing beyond trusted local development.
- Validate repository names and branch names.
- Resolve paths and enforce that repositories remain under `repositories-base-dir`.
- Consider making destructive operations opt-in or protected.
- Add subprocess timeouts and output limits.

## Correctness Issues Found

### `POST /api/v1/repositories` response does not match its model

`RepositoryCreateOKResponseModel` requires:

- `message`
- `name`
- `path`

The route returns only:

- `message`
- `path`

FastAPI response validation may fail because `name` is missing.

### Repository creation ignores request `path`

The create request asks clients for `path`, but `add_repository()` only accepts `name` and computes its own path.

This is confusing API behavior. Either remove `path` from the request model or implement path-based registration intentionally.

### New repository path may be stored incorrectly

Existing index entries store relative paths such as `./hello-world.git`.

`add_repository()` stores `str(path)` where `path = repositories_base_dir / name`, which is likely `repositories/{name}`. `get_repository()` later joins that value to `repositories_base_dir`, which can point at `repositories/repositories/{name}`.

The index should store a path relative to the base directory, or the service should store absolute paths and not rejoin them.

### Route parameter declaration inconsistency

`delete_repository(name: str, ...)` relies on FastAPI inferring `name` from the router path. This works, but other routes use `FastAPIPath` annotations. Using the same explicit annotation would improve generated docs and consistency.

### Bare repository assumptions are unclear

The current stored repositories are named `hello-world.git` and `logfire.git`, suggesting bare repositories. `git branch`, `git log`, and `git diff` can work in bare repositories, but branch creation/deletion semantics should be documented because there is no working tree.

## API Design Observations

The service currently mixes two concepts:

- Register an existing repository path.
- Create a new repository under the managed base directory.

The route name "Add a new repository" and request body `path` suggest registration. The service implementation performs creation. This should be split or clarified.

Possible design:

- `POST /repositories`
  - Register an existing repository by name and path.
- `POST /repositories/{name}/init`
  - Initialize a new managed repository.

Alternative simpler design:

- Keep only `POST /repositories` to initialize managed repositories.
- Remove `path` from the request body.
- Store `path` as a normalized relative path generated by the service.

## Testing Status

No test files were found in the project.

Recommended test layers:

- Unit tests for `GitService` command parsing with mocked `call()`.
- Unit tests for `RepositoryService` index read/write, path resolution, duplicate detection, and missing repository handling.
- FastAPI route tests with dependency overrides.
- Integration tests using temporary Git repositories.

High-value initial tests:

- `GET /api/v1/health` returns `200`.
- `GET /api/v1/git/version` returns the mocked Git version.
- `GET /api/v1/repositories` lists names from a temp index.
- `POST /api/v1/repositories` response validates against its model.
- Newly added repositories can be fetched immediately by name.
- Missing repository returns `404`.
- Git subprocess failures produce expected HTTP responses after route-level error mapping is added.

## Maintainability

Strengths:

- The project is small and layered.
- Service classes are easy to locate.
- Route models are explicit and documented.
- Git parsing is centralized.
- Observability is already integrated.

Concerns:

- Pydantic dataclasses are used for service classes and custom exceptions. This works, but regular dataclasses may be simpler for non-validation service objects.
- Some imports and comments suggest prototype code remains.
- The `DB` constant in `dhforge/services/repositories.py` is unused.
- `PrivateAttr` is imported but unused.
- Placeholder comments should be removed once behavior is real.
- The repository index should have a typed model instead of `Any`.

## Operational Considerations

Startup requirements:

- Python 3.12+
- Git installed and available on `PATH`
- `config.toml` available in the current working directory
- `repositories/index.json` available and writable for mutation endpoints
- Managed repository directories available under `repositories/`

Potential runtime failures:

- Starting the app from a different directory can make `config.toml` unavailable.
- Running without Git installed breaks Git endpoints.
- Permission issues on `repositories/index.json` break list/create/delete operations.
- Concurrent mutation requests can corrupt or lose repository index changes.

## Recommended Roadmap

### Immediate Fixes

1. Fix `POST /repositories` response to include `name`.
2. Decide whether repository creation should use `request.path`; either implement it or remove the field.
3. Normalize index path storage and lookup.
4. Add route-level error handling for Git failures and repository path failures.
5. Add basic tests around repository creation and lookup.

### Short-Term Hardening

1. Add typed models for the repository index.
2. Add atomic index writes.
3. Validate repository names, branch names, and refs.
4. Add subprocess timeouts.
5. Make config path resolution independent of process working directory.
6. Remove unused imports, constants, and placeholder comments.

### Medium-Term Improvements

1. Add authentication if the service will be exposed beyond a trusted local process.
2. Add endpoints for repository status, refs, tags, remotes, and file tree browsing.
3. Add structured error models.
4. Add OpenAPI examples for common flows.
5. Add integration tests using temporary repositories.
6. Consider an async lock or a small embedded database if repository index mutation grows.

## Overall Assessment

DHForge has a clean foundation for a local Git-management HTTP API. Its separation between FastAPI routes, dependency construction, repository indexing, and Git execution is sensible. The largest current risks are not architectural; they are correctness and hardening details around path handling, response validation, error translation, concurrent index writes, and tests.

With a small round of fixes and a focused test suite, this project can become a reliable base for higher-level Git automation features.
