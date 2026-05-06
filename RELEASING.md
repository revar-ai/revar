# Releasing

`revar` and `revar-models` ship to PyPI together at the same version. Releases
are cut by pushing a `v*` git tag; the rest is automated by
[`.github/workflows/release.yml`](.github/workflows/release.yml).

We use **PyPI Trusted Publishing** (OIDC) — no API tokens are stored as GitHub
secrets. The first release requires a one-time setup on PyPI.

---

## One-time setup (per repository)

You only have to do these steps once for the lifetime of the repo.

### 1. Reserve the names on PyPI

If `revar` and `revar-models` aren't already yours on PyPI, the *first* release
will create them and assign you as owner. If you want to be safe, do a TestPyPI
dry-run first (see below) — TestPyPI mirrors the same name-claim semantics.

### 2. Register the trusted publisher on PyPI

For **each** of the two projects (`revar`, `revar-models`):

1. Go to <https://pypi.org/manage/account/publishing/> and add a "pending publisher" (if the project doesn't exist yet) or, after first release, edit the project on PyPI and add a publisher.
2. Fill in:
   - **PyPI Project Name**: `revar` (or `revar-models`)
   - **Owner**: `<your-github-org-or-user>`
   - **Repository name**: `revar`
   - **Workflow name**: `release.yml`
   - **Environment name**: `pypi`
3. Repeat the same on <https://test.pypi.org/manage/account/publishing/> with environment name `testpypi` if you want dry-runs to TestPyPI.

### 3. Create matching environments in GitHub

In the repo's *Settings → Environments*, create two environments:

- `pypi` — used by tag-driven production releases.
- `testpypi` — used by manual dry-runs from the Actions tab.

You can leave both unprotected for now; later you may want to require an approval
on `pypi` so accidental tags don't auto-publish.

---

## Per-release runbook

```text
1. Confirm main is green.
2. Bump versions:        scripts/bump_version.py 0.1.1
3. Update CHANGELOG.md:  move bullets from [Unreleased] into a [0.1.1] section
4. Commit + push:        git commit -am "release: v0.1.1" && git push
5. (Optional) dry-run:   GitHub Actions → "Release" → Run workflow → testpypi
6. Tag and push:         git tag v0.1.1 && git push --tags
7. Watch the workflow:   gh run watch
8. Verify on PyPI:       pip install --upgrade revar && python -c "import revar; print(revar.__version__)"
```

### What the workflow does, in order

1. **preflight** — installs both packages, runs `ruff check packages` and `pytest packages`, and runs `scripts/check_versions.py` to refuse a half-bumped repo.
2. **build** — produces sdist + wheel for both packages, uploads them as artifacts so subsequent jobs upload identical bits.
3. **publish-models** — uploads `revar-models` to PyPI (or TestPyPI on dispatch).
4. **publish-revar** — uploads `revar` only after models lands; if models fails, revar is skipped and PyPI stays consistent.
5. **github-release** — on tag pushes only, cuts a GitHub Release with notes pulled from `CHANGELOG.md` and attaches both wheels + sdists.

### Dry-running to TestPyPI

From GitHub: *Actions → Release → Run workflow → target: testpypi*. This skips the GitHub Release step and uploads to <https://test.pypi.org>. Smoke-test with:

```bash
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            "revar==0.1.1"
```

(The extra-index is required because `revar` pulls non-revar deps like `httpx` from real PyPI.)

---

## Local-only release (escape hatch)

If you ever need to publish without GitHub Actions (lost OIDC, broken runner, etc.):

```bash
python -m pip install --upgrade build twine
python scripts/check_versions.py
python -m build packages/shared-models
python -m build packages/core-py
python -m twine upload packages/shared-models/dist/* packages/core-py/dist/*
# then: git tag v0.1.1 && git push --tags  (so the changelog/GitHub release still cuts)
```

This requires a PyPI API token in `~/.pypirc` and bypasses the safety nets in CI — prefer the workflow.

---

## Versioning policy

We follow [SemVer](https://semver.org/spec/v2.0.0.html):

- **MAJOR** — incompatible changes to the SDK surface (`Environment`, `Task`, `Adapter`, the `/__test__/*` HTTP contract) or to a published task YAML schema field.
- **MINOR** — additive features (new modifier, new adapter, new task category).
- **PATCH** — bug fixes, doc changes, dependency bumps that don't affect the public API.

Pre-1.0, anything *can* break in a minor release; we still try to call those out clearly in the CHANGELOG.

The two packages always release at the same version. `revar`'s pin on `revar-models==<X.Y.Z>` is updated atomically by `scripts/bump_version.py`.
