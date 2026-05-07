<h1 align="center">
  Resurf
</h1>

<p align="center">
  <strong>Realistic, Reproducible Test Framework for AI Browser Agents</strong>
</p>

<div align="center">
  <a href="https://pypi.org/project/resurf/">
    <img src="https://img.shields.io/pypi/v/resurf?logo=pypi&logoColor=white" alt="PyPI" /></a>
  <a href="https://github.com/revar-ai/resurf/actions/workflows/test.yml">
      <img src="https://img.shields.io/github/actions/workflow/status/revar-ai/resurf/ci.yml?branch=main"
          alt="Test status (main branch)"></a>
  <a href="https://github.com/revar-ai/resurf/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/revar-ai/resurf" alt="License" /></a>
</div>

Systematic testing of browser agents today is not easy: real websites are flaky, rate-limited and expensive (bot unblocking), while static-HTML benchmarks lack state and dynamic behavior. Resurf gives your browser agent a realistic, stateful, instrumented framework — built on synthetic websites with failure-mode injection.

| | **Mind2Web** | **WebVoyager** | **Resurf** |
|---|:---:|:---:|:---:|
| Realistic, dynamic, interactive environment    | ❌ | ✅ | ✅ |
| Deterministic & reproducible      | ✅ | ❌ | ✅ |
| Failure-mode injection (latency, payment errors, 5xx) | ❌ | ❌ | ✅ |
| Auditable success eval (DB state, not LLM judge) | ❌ | ❌ | ✅ |
| No dependency on live websites    | ✅ | ❌ | ✅ |

## What's in v0

- **`shop_v1`** — A production-shaped synthetic e-commerce site (FastAPI + React + SQLite) running in a single Docker container. Catalog, cart, multi-step checkout, auth, accounts, returns. Mobile-responsive. Deliberate ambiguous-UI inventory for testing agent reasoning.
- **Modifiers (failure-mode injection)** — FastAPI middleware that toggles network latency, payment outcomes (declined / 3DS / timeout), server error rates, and session expiration per task. Configured per-task in YAML; no code changes to add new failure-mode combinations.
- **Authoring stack** — A YAML task schema, ~10 failure-mode templates with scripted reference trajectories, and a CLI: `task new`, `task from-template`, `task validate`, `task try`.
- **Adapters** — `browser-use` (DOM/AX-tree native), `stagehand` (via Node subprocess), and a vision-only baseline. All optional installs.
- **Trajectory recording** — Per-step DOM snapshots, screenshots, agent actions, token counts, latencies. Deterministic via SQLite snapshot reset and seeded faker.

v0 ships a single site — `shop_v1` — to keep the focus on getting the abstractions (`Environment`, modifiers, success predicates, the `/__test__/*` admin protocol) right against several adapters. E-commerce was picked because it exercises forms, multi-step flows, auth, money, and obvious failure-mode hooks in a small amount of code. Adding more sites is now content work, not platform work — see [Adding a new site](#adding-a-new-site).

## 5-minute quickstart

Prerequisites: Python 3.11+, Docker, Node 20+ (only if you plan to use the Stagehand adapter), and Chromium for Playwright.

```bash
# 1. Install resurf with the browser-use adapter
pip install 'resurf[browser-use]'   # imports as `resurf`

# --- Local-development install (use this until resurf is published to PyPI) ---
# git clone https://github.com/revar-ai/resurf
# cd resurf
# python3.11 -m venv .venv && source .venv/bin/activate
# pip install -e packages/shared-models
# pip install -e 'packages/core-py[dev,browser-use]'

# 2. Install Chromium for Playwright (one-time)
playwright install chromium

# 3. Start shop_v1
docker compose up -d shop_v1
# Wait ~3s for the container to be healthy
curl -s http://localhost:8080/api/health

# 4. List bundled tasks
resurf task list

# 5. Run a task with the browser-use adapter
export OPENAI_API_KEY=sk-...
python examples/run_browser_use.py tasks/shop_v1/find/find_product_by_name.yaml

# Tip: set REVAR_HEADED=1 to watch the browser drive in a visible window.
#   REVAR_HEADED=1 python examples/run_browser_use.py <task.yaml>
# Works for all four example runners (browser-use, scripted, vision, stagehand).
```

You should see something like:

```
[resurf] reset shop_v1 to seed=42
[resurf] running browser-use agent on find_product_by_name
[resurf] step 1: nav https://localhost:8080/
[resurf] step 2: click [aria-label="Search"]
[resurf] step 3: type "Acme Bluetooth Speaker"
...
[resurf] passed=True steps=7 tokens=4123 wall_clock=12.4s
[resurf] trajectory saved to ./trajectories/...
```

### Running shop_v1 backend without Docker

Useful if you want to iterate on the backend or read live SQL while debugging:

```bash
pip install -e sites/shop_v1/backend
REVAR_TEST_MODE=1 uvicorn app.main:app --reload --port 8080 --app-dir sites/shop_v1/backend
```

For frontend hacking, `cd sites/shop_v1/frontend && npm install && npm run dev` runs Vite on port 5173 and proxies `/api/*` to the backend.

## Running tests

The full Python test suite runs against `resurf` and `resurf-models`:

```bash
# From the repo root, with the venv from quickstart activated
pytest
```

This is also exactly what CI runs. Useful subsets:

```bash
pytest packages/core-py            # SDK + CLI + task validation
pytest packages/shared-models      # SQLModel schema and seed determinism
pytest -k schema                   # task YAML schema validation only
```

End-to-end smoke test against a running `shop_v1` (Docker container or local uvicorn):

```bash
docker compose up -d shop_v1
python examples/run_scripted.py tasks/shop_v1/find/find_product_by_name.yaml
# expects: passed=True
```

### Testing the Stagehand adapter

Stagehand runs in Node, so the Stagehand adapter shells out to `adapters/stagehand/bridge.mjs` over stdio. One-time setup:

```bash
# 1. Install Node 20+, then install Stagehand into the bridge folder
cd adapters/stagehand
npm install @browserbasehq/stagehand

# 2. (Optional) Smoke-test the bridge in isolation — proves Node + Stagehand are wired up
#    Requires a running shop_v1 on :8080 and OPENAI_API_KEY set.
export OPENAI_API_KEY=sk-...
npm run smoke
# Expect: a single-line JSON `{ "steps": [...], ... }` and exit 0.
```

Then drive a real task through the Python adapter:

```bash
cd ../..    # back to repo root
docker compose up -d shop_v1
python examples/run_stagehand.py tasks/shop_v1/find/find_acme_bluetooth_speaker.yaml
```

## Authoring your own task

The fastest path is to clone an existing failure-mode template:

```bash
resurf task from-template checkout/payment_declined_recovery \
    -p product_name="Acme Bluetooth Speaker" \
    -p product_slug=acme-bluetooth-speaker \
    --out tasks/shop_v1/checkout/

resurf task validate tasks/shop_v1/checkout/acme_bluetooth_speaker_payment_declined_recovery.yaml
resurf task try      tasks/shop_v1/checkout/acme_bluetooth_speaker_payment_declined_recovery.yaml
```

Or write YAML by hand — see [`docs/architecture.md`](docs/architecture.md#task-yaml) for the schema.

## Modifiers (failure-mode injection)

Modifiers are how a task says "make the site behave like X." They're set under `modifiers:` in the task YAML, and resurf applies them at reset time via `POST /__test__/configure`. Nothing in `shop_v1`'s product code needs to know about specific failure modes — middlewares handle them transparently.

### Available modifiers

| Key                  | Type                 | Values / shape                                              | Default            | Effect                                                                                          |
|----------------------|----------------------|-------------------------------------------------------------|--------------------|-------------------------------------------------------------------------------------------------|
| `latency_profile`    | string               | `none` \| `fast` \| `realistic` \| `slow_3g`                | `fast`             | Sleeps before each `/api/*` response per the profile's per-route (min, max) seconds.            |
| `payment_outcome`    | string \| list \| object | `success` \| `declined` \| `3ds_required` \| `timeout`, **or** `[..., ...]` for a sequence consumed in order, **or** `{ sequence: [...] }` | `success`          | Drives `/api/checkout/confirm`. Sequences let you script "decline once, then succeed."          |
| `server_error_rate`  | number (0.0–1.0)     | e.g. `0.1` for ~10% 503s                                    | `0.0`              | Probability of injecting a 503 on requests matching `server_error_paths`.                       |
| `server_error_paths` | list[string]         | e.g. `["/api/products", "/api/cart"]`                       | `["/api/products"]` | URL-prefixes eligible for the error injector above.                                             |
| `session_ttl_s`      | int \| null          | seconds                                                     | site default       | Forces a shorter session expiry — useful for testing mid-flow re-auth.                           |
| `frozen_time_iso`    | string (ISO 8601)    | e.g. `2026-05-01T12:00:00Z`                                 | unset              | Pins server-side "now" — use it to make coupon expiry / order timestamps deterministic.          |

### Example: payment-declined-then-succeed checkout

```yaml
id: shop_v1.checkout.acme_speaker_decline_recovery
site: shop_v1
goal: |
  Buy 1 Acme Bluetooth Speaker. Your first payment will be declined; retry
  to recover and complete the order.
modifiers:
  latency_profile: realistic
  payment_outcome:
    sequence: [declined, success]   # first /confirm fails, second succeeds
  server_error_rate: 0.0
  frozen_time_iso: "2026-05-01T12:00:00Z"
budget:
  max_steps: 25
  max_wall_clock_s: 120
success:
  type: state_predicate
  query: SELECT COUNT(*) AS count FROM "order" WHERE status = 'paid'
  predicate: result == 1
```

### Configuring at runtime (without a task)

The same knobs are available via the admin API — handy for ad-hoc poking or building your own runner:

```bash
curl -s http://localhost:8080/__test__/configure -H 'content-type: application/json' \
  -d '{"latency_profile":"slow_3g","payment_outcome":"3ds_required"}'
```

Or from Python:

```python
env = Environment(site="shop_v1")
env.configure({"latency_profile": "slow_3g", "payment_outcome": "3ds_required"})
```

### Adding a new modifier

The contract is intentionally small. A modifier is just a key in `ModifierConfig` plus the middleware/handler that reads it. Concretely:

1. **Add the field** in `sites/shop_v1/backend/app/modifiers.py` (`ModifierConfig` dataclass, `reset()`, `update()`, `to_dict()`).
2. **Implement the behavior** — either as a new ASGI middleware in `sites/shop_v1/backend/app/middleware/`, or inline in the API handler that should react to it.
3. **Wire it in** in `sites/shop_v1/backend/app/main.py` (only if it's a middleware).
4. **Document the YAML key** in this README's table and in `docs/architecture.md`'s modifier table.
5. **(Optional) Update the task JSON Schema** at `packages/core-py/resurf/schemas/task.schema.json` if you want strict validation of the new key.

A good first example to copy is `LatencyMiddleware` (one file, ~30 lines) — it shows the read-config-and-act pattern end-to-end.

## Adding a new site

A site is just an HTTP service that implements six admin endpoints — `GET /api/health`, `POST /__test__/{reset,configure,query,freeze_time}`, and `GET /__test__/state` — guarded by `REVAR_TEST_MODE=1`. The contract is HTTP-shaped, so any backend stack works.

To add one: scaffold under `sites/<your_site>/`, add a deterministic seeder under `packages/shared-models/resurf_models/<your_site>/`, register a service block in `docker-compose.yml`, and drop tasks under `tasks/<your_site>/` with `site: <your_site>` in the YAML. Copy from `shop_v1` — `app/modifiers.py` and `api/test_endpoints.py` are near-verbatim reusable. Contributions welcome.

## Releasing

Cut a release by bumping versions with `scripts/bump_version.py X.Y.Z`, updating `CHANGELOG.md`, and pushing a `vX.Y.Z` tag. CI handles the PyPI upload (via Trusted Publishing) and the GitHub Release. Full runbook in [`RELEASING.md`](RELEASING.md).

## License

resurf is licensed under the **Apache License 2.0**. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).


## Contributing

Contributions of new tasks, templates, and bug fixes are very welcome. By submitting a pull request, you agree that your contribution is licensed under Apache 2.0 (per Section 5 of the license). For larger changes, please open a GitHub Discussion first so we can align on direction. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for details.

## Roadmap

See [`docs/roadmap.md`](docs/roadmap.md). Headline v1 items: a correlation study against real OSS shop demos, adversarial modifiers (CAPTCHA, anti-bot, dark patterns), prompt-driven task generation, a second site vertical, and a native Node SDK.
