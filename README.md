# College Profile Comparator

A lightweight modular-monolith backend for a three-person team. It converts ChanceMe-style text into structured data, tags activities and awards, and produces an explainable profile comparison.

This scaffold deliberately **does not** calculate admission probabilities. It also keeps race and gender as optional metadata and does not use them to score activities or determine match quality.

## Architecture

```text
raw profile text
      |
      v
   Parser  --------> Profile
      |
      v
   Tagger  --------> TaggedProfile
      |
      v
 Diff Engine ------> DiffResult
      |
      v
 Advisor (later) --> AdviceResult
```

Only `app/schema.py` is shared as a data contract. Each stage exposes one primary public function:

```python
parse_profile(raw_input: str) -> Profile
tag_profile(profile: Profile) -> TaggedProfile
compare_profiles(left: TaggedProfile, right: TaggedProfile) -> DiffResult
```

## Folder structure

```text
college-profile-comparator/
├── .github/workflows/test.yml
├── backend/
│   ├── app/
│   │   ├── advisor/
│   │   ├── diff_engine/
│   │   ├── parser/
│   │   ├── tagger/
│   │   ├── main.py
│   │   ├── pipeline.py
│   │   └── schema.py
│   └── tests/
│       └── fixtures/
├── frontend/
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

## Windows PowerShell setup

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the API:

```powershell
python -m uvicorn app.main:app --reload --app-dir backend
```

Open:

- API docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

Run tests:

```powershell
python -m pytest
```

Run linting:

```powershell
python -m ruff check .
```

## API endpoints

- `GET /health`
- `POST /profiles/parse`
- `POST /profiles/tag`
- `POST /profiles/compare`
- `POST /pipeline/compare-raw`

Use the interactive `/docs` page to try them.

## Recommended team ownership

- **Parser owner:** `backend/app/parser/`
- **Tagger owner:** `backend/app/tagger/`
- **Diff/integration owner:** `backend/app/diff_engine/`, `pipeline.py`, and `main.py`
- **Joint ownership:** `schema.py` and `backend/tests/fixtures/`

Changes to `schema.py` should be reviewed by another teammate before merging.

## Git workflow

First merge the scaffold and schema into `main`. Then each developer creates a branch:

```powershell
git switch main
git pull
git switch -c feature/parser
```

Other suggested branches:

```text
feature/tagger
feature/diff-engine
schema/profile-v1
```

Commit and push:

```powershell
git add .
git commit -m "Implement parser section handling"
git push -u origin feature/parser
```

Open a pull request on GitHub, review it, and merge it into `main`.

## Current placeholder behavior

The parser uses deterministic regular expressions and heading detection. The tagger uses a keyword taxonomy. The diff engine uses explainable rule-based matching. These are intentionally simple so each module can be replaced without changing the shared contracts.

## Adding the advisor later

`app/advisor/advisor.py` accepts a `Profile` and `DiffResult` and returns an `AdviceResult`. A future LLM call belongs only inside that module. The parser, tagger, and diff engine never import it, so adding or replacing the advisor does not modify the existing three stages.

Before using a real LLM, add tests for factual grounding, feasibility, unsupported claims, and advice that encourages unhealthy profile copying.
