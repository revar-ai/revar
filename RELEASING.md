# Releasing

`resurf` and `resurf-models` ship to PyPI together at the same version.
Releases are cut by pushing a `v*` git tag; the rest is automated by
[`.github/workflows/release.yml`](.github/workflows/release.yml).

Auth is via PyPI **API tokens** stored as GitHub Actions secrets. Tokens are
simpler than Trusted Publishing and good enough for a small project; if you
later want OIDC's stricter security model, see "Switching to Trusted
Publishing" at the bottom of this doc.

---

## One-time setup (per repository)

You only have to do these once for the lifetime of the repo.

### 1. Create PyPI API tokens

Generate two tokens — one production, one TestPyPI:

1. Sign in at <https://pypi.org/account/login/>.
2. Go to <https://pypi.org/manage/account/token/> → **Add API token**.
3. **First release only:** scope it to "Entire account" — project-scoped tokens can't *create* new projects. Once both `resurf` and `resurf-models` exist on PyPI, replace this with two project-scoped tokens (one per project) and concatenate or use whichever you prefer.
4. Copy the `pypi-...` value. **You can only see it once** — if you lose it, you regenerate.
5. (Optional) Repeat at <https://test.pypi.org/manage/account/token/> for TestPyPI dry-runs.

### 2. Add the tokens as GitHub secrets

In the repo's *Settings → Secrets and variables → Actions → New repository secret*:

| Name                    | Value                       | Required for                |
|-------------------------|-----------------------------|------------------------------|
| `PYPI_API_TOKEN`        | the `pypi-...` token        | Tag-driven production releases |
| `TEST_PYPI_API_TOKEN`   | the test.pypi `pypi-...` token | Manual TestPyPI dry-runs only |

The release workflow refers to them by exactly those names.

### 3. (After first release) Re-scope to project tokens

Account-scoped tokens can publish anything in your account, which is overkill
for a CI secret. After the first successful release:

1. Generate a new token at <https://pypi.org/manage/account/token/> scoped to **`resurf`** only.
2. Generate another scoped to **`resurf-models`** only.
3. Concatenate both into a single secret value separated by newlines (twine accepts both), or split into two secrets (`PYPI_API_TOKEN_RESURF`, `PYPI_API_TOKEN_MODELS`) and update the workflow to use them per job.
4. Delete the original account-scoped token.

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
8. Verify on PyPI:       pip install --upgrade resurf && python -c "import resurf; print(resurf.__version__)"
```

### What the workflow does, in order

1. **preflight** — installs both packages, runs `ruff check packages` and `pytest packages`, and runs `scripts/check_versions.py` to refuse a half-bumped repo.
2. **build** — produces sdist + wheel for both packages, uploads them as artifacts so subsequent jobs upload identical bits.
3. **publish-models** — uploads `resurf-models` to PyPI (or TestPyPI on dispatch).
4. **publish-resurf** — uploads `resurf` only after models lands; if models fails, resurf is skipped and PyPI stays consistent.
5. **github-release** — on tag pushes only, cuts a GitHub Release with notes pulled from `CHANGELOG.md` and attaches both wheels + sdists.

### Dry-running to TestPyPI

From GitHub: *Actions → Release → Run workflow → target: testpypi*. This skips the GitHub Release step and uploads to <https://test.pypi.org>. Smoke-test with:

```bash
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            "resurf==0.1.1"
```

(The extra-index is required because `resurf` pulls non-resurf deps like `httpx` from real PyPI.)

---

## Local-only release (escape hatch)

If you ever need to publish without GitHub Actions (broken runner, lost CI access, etc.):

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

The two packages always release at the same version. `resurf`'s pin on `resurf-models==<X.Y.Z>` is updated atomically by `scripts/bump_version.py`.

---

## Switching to Trusted Publishing (OIDC)

If you later want to drop the long-lived API tokens, PyPI Trusted Publishing
mints a fresh OIDC token on every workflow run — no secrets in repo settings.
The migration is mechanical:

1. On PyPI, go to each project (`resurf`, `resurf-models`) → *Manage → Publishing → Add a new pending publisher*. Fill in: workflow file `release.yml`, environment `pypi`, owner = your GitHub org/user.
2. In *Settings → Environments* on GitHub, create environments `pypi` and (optionally) `testpypi`.
3. In `release.yml`, on each `publish-*` job, add:

    ```yaml
    environment: { name: pypi }
    permissions: { id-token: write }
    ```

   …and remove the `password: ${{ secrets.PYPI_API_TOKEN }}` line under each `pypi-publish` step (the action auto-detects OIDC when the token-write permission is set).
4. Delete the `PYPI_API_TOKEN` / `TEST_PYPI_API_TOKEN` repository secrets.

The benefit is mainly defense-in-depth: a malicious PR or compromised
maintainer key can't exfiltrate a token that doesn't exist. Worth the click
budget once you have outside contributors with write access.
