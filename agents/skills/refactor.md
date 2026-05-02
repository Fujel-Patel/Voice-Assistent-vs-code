# Skill: Refactor

## When to Use
- Extracting classes or functions from large files (e.g., `orchestrator.py` at 463 lines, `pipeline.py` at 834 lines)
- Moving files between directories (e.g., `brain/` → `services/brain/`)
- Splitting monolithic modules into focused units

## Pre-Flight Checklist

1. **Run tests first** — establish baseline
   ```bash
   pytest backend/tests/ -v --tb=short
   ```
2. **Run type checker** — record current state
   ```bash
   mypy --strict backend/
   ```
3. **Identify all importers** — search for every file that imports the target module
   ```bash
   ruff check --select I backend/  # import order
   grep -rn "from <module>" backend/ --include="*.py"
   ```

## Refactor Procedure

### Moving a File
1. Create the new file at the destination with the exact same content
2. Update all imports across the codebase (use `grep -rn` to find them all)
3. Update `__init__.py` re-exports if any
4. Delete the old file
5. Run `mypy --strict backend/` — must pass with 0 errors
6. Run `pytest backend/tests/ -v` — must pass with 0 failures

### Extracting a Class
1. Identify the class boundaries and its dependencies
2. Create the new file with `from __future__ import annotations` as line 1
3. Move the class and its direct dependencies (imports, type aliases)
4. Use `TYPE_CHECKING` guards for circular imports
5. Add the new import to the original file
6. Run quality gates

### Splitting a Large Module
1. Map the module's public API (what other modules import from it)
2. Group related functions/classes into logical units
3. Create new files, maintaining the public API via `__init__.py` re-exports
4. Verify no circular imports with `mypy --strict`

## Critical Rules

- **Never break the `VoicePipeline` state machine logic** — the `THINKING → SPEAKING` transition order is load-bearing
- **Never modify `JarvisConfig`** fields without updating `_ENV_TO_CONFIG_MAP` in `core/config.py`
- **Always preserve `from __future__ import annotations`** as line 1
- **Always run all 3 quality gates** after refactoring:
  ```bash
  ruff check --fix .
  mypy --strict backend/
  pytest backend/tests/ -v
  ```

## Post-Refactor

1. Update `agent/architecture.md` if folder structure changed
2. Update `agent/tasks.md` to mark completed items
3. Run `ruff check --fix .` for import ordering
