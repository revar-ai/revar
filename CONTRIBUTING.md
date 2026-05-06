# Contributing to revar

Thanks for your interest. revar is in v0 and contributions are very welcome — especially **new failure-mode templates** and **task contributions**, which are the highest-leverage ways to grow the project.

## Before you open a PR

For small fixes (typos, obvious bugs, single-task contributions), feel free to open a PR directly. For anything larger — new templates, adapter changes, schema or core-py refactors — **please open a GitHub Discussion first** so we can align on direction before you invest time.

Use the `pull-requests` Discussions category. Include:
- What you plan to change and why
- Which type of contribution (template, task, code, docs)
- Any design decisions you'd like input on

## Types of contribution

### 1. Task contributions (data, easiest path)

A task is a YAML file under `tasks/shop_v1/<category>/`. Tasks are data, not code — they describe a goal and a success predicate.

Quick recipe:
```bash
revar task from-template <category>/<template> --out tasks/shop_v1/<category>/
revar task validate tasks/shop_v1/<category>/<your-task>.yaml
revar task try      tasks/shop_v1/<category>/<your-task>.yaml
```

Open a Discussion linking your task; we'll review and merge.

### 2. Template contributions (highest leverage)

A template parameterizes a whole *class* of tasks. Templates live under `templates/<category>/<name>.yaml.j2` and ship with a Playwright-scripted reference trajectory at `templates/<category>/<name>.scripted.py` that proves the template is solvable end-to-end.

Template-contribution checklist:
- A doc header in the `.yaml.j2` declaring parameters, required modifiers, and a one-line description
- A scripted reference trajectory that runs green via `revar task try`
- At least one example task generated from the template under `tasks/shop_v1/`
- A short README addition or doc note

### 3. Code contributions

For code changes, please:
- Open a Discussion before writing significant code so we can align on approach.
- Keep PRs focused and reviewable; one logical change per PR.
- Include tests for new behavior in `packages/core-py/tests` or `packages/shared-models/tests`.
- Follow the existing module layout and SPDX header convention.

## Development setup

```bash
# Clone
git clone https://github.com/<org>/revar
cd revar

# Install both packages in editable mode
pip install -e packages/shared-models -e 'packages/core-py[dev,browser-use]'

# Start shop_v1
docker compose up -d shop_v1

# Run tests
pytest
```

For frontend work:
```bash
cd sites/shop_v1/frontend
npm install
npm run dev    # dev server at localhost:5173, proxies /api/* to backend
```

For backend work without Docker:
```bash
cd sites/shop_v1/backend
pip install -e .
REVAR_TEST_MODE=1 uvicorn app.main:app --reload --port 8080
```

## Code style

- Python: ruff for lint + format, mypy for typing where it pays off
- TypeScript: ESLint + Prettier, strict TS
- All source files carry an `SPDX-License-Identifier: Apache-2.0` header

## License of contributions

revar is licensed under the Apache License 2.0. Per Section 5 of that license, contributions you submit (e.g., via pull request) are licensed to the project under Apache 2.0 unless you explicitly state otherwise. By submitting a contribution you affirm that you have the right to do so.

If your employer claims rights to your contributions, please make sure you have permission to contribute under Apache 2.0 (most employers' open-source policies cover this for permissive licenses).
