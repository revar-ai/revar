# revar

A deterministic, reproducible test environment for AI browser agents.

Real websites are flaky, expensive, rate-limited, and hostile to automated traffic. Static-HTML benchmarks lack state and dynamic behavior. Revar gives your browser agent a realistic, stateful, instrumented playground — locally, in Docker, in 5 minutes.

## What's in v0

- **`shop_v1`** — A production-shaped synthetic e-commerce site (FastAPI + React + SQLite) running in a single Docker container. Catalog, cart, multi-step checkout, auth, accounts, returns. Mobile-responsive. Deliberate ambiguous-UI inventory for testing agent reasoning.
- **Modifiers** — FastAPI middleware that toggles network latency, payment outcomes (declined / 3DS / timeout), server error rates, and session expiration per task. Configured per-task in YAML; no code changes to add new failure-mode combinations.
- **Authoring stack** — A YAML task schema, ~10 failure-mode templates with scripted reference trajectories, and a CLI: `task new`, `task from-template`, `task validate`, `task try`.
- **Adapters** — `browser-use` (DOM/AX-tree native), `stagehand` (via Node subprocess), and a vision-only baseline. All optional installs.
- **Trajectory recording** — Per-step DOM snapshots, screenshots, agent actions, token counts, latencies. Deterministic via SQLite snapshot reset and seeded faker.

## 5-minute quickstart

Prerequisites: Python 3.11+, Docker, Node 20+ (only if you plan to use the Stagehand adapter), and Chromium for Playwright.

```bash
# 1. Install revar with the browser-use adapter
pip install 'revar[browser-use]'

# --- Local-development install (use this until revar is published to PyPI) ---
# git clone https://github.com/revar-ai/revar
# cd revar
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
revar task list

# 5. Run a task with the browser-use adapter
export OPENAI_API_KEY=sk-...
python examples/run_browser_use.py tasks/shop_v1/find/find_product_by_name.yaml
```

You should see something like:

```
[revar] reset shop_v1 to seed=42
[revar] running browser-use agent on find_product_by_name
[revar] step 1: nav https://localhost:8080/
[revar] step 2: click [aria-label="Search"]
[revar] step 3: type "Acme Bluetooth Speaker"
...
[revar] passed=True steps=7 tokens=4123 wall_clock=12.4s
[revar] trajectory saved to ./trajectories/...
```

### Running shop_v1 backend without Docker

Useful if you want to iterate on the backend or read live SQL while debugging:

```bash
pip install -e sites/shop_v1/backend
REVAR_TEST_MODE=1 uvicorn app.main:app --reload --port 8080 --app-dir sites/shop_v1/backend
```

For frontend hacking, `cd sites/shop_v1/frontend && npm install && npm run dev` runs Vite on port 5173 and proxies `/api/*` to the backend.

## Running tests

The full Python test suite runs against `revar` and `revar-models`:

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

Common failures and what they mean:
- `Node binary `node` not on PATH` — install Node 20+ or set `node_bin` on `StagehandAdapter`.
- `Stagehand is not installed` (exit 2 from the bridge) — you skipped `npm install` in `adapters/stagehand/`.
- `OPENAI_API_KEY is not set` — the bridge model needs it; export it before running.

## Authoring your own task

The fastest path is to clone an existing failure-mode template:

```bash
revar task from-template checkout/payment_declined_recovery \
    --product "Acme Bluetooth Speaker" \
    --out tasks/shop_v1/checkout/

revar task validate tasks/shop_v1/checkout/payment_declined_recovery.yaml
revar task try    tasks/shop_v1/checkout/payment_declined_recovery.yaml
```

Or write YAML by hand — see [`docs/architecture.md`](docs/architecture.md#task-yaml) for the schema.

## License

revar is licensed under the **Apache License 2.0**. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

You can use, modify, and redistribute revar — including in proprietary or commercial products — provided you retain the copyright notice and the required attribution from `NOTICE`. Apache 2.0 also includes an explicit patent grant from contributors.

## Contributing

Contributions of new tasks, templates, and bug fixes are very welcome. By submitting a pull request, you agree that your contribution is licensed under Apache 2.0 (per Section 5 of the license). For larger changes, please open a GitHub Discussion first so we can align on direction. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for details.

## Roadmap

See [`docs/roadmap.md`](docs/roadmap.md). Headline v1 items: a correlation study against real OSS shop demos, adversarial modifiers (CAPTCHA, anti-bot, dark patterns), prompt-driven task generation, a second site vertical, and a native Node SDK.
