# revar architecture (v0)

## High level

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Agent (Browser Use / Stagehand / Vision baseline / your adapter)        │
│        ▲                                                                 │
│        │ actions                                                         │
│        ▼                                                                 │
│   Adapter                                                                │
│        ▲                                                                 │
│        │ DOM / screenshot / accessibility tree                           │
│        ▼                                                                 │
│   Headless Chromium (Playwright)                                         │
│        ▲ HTTP                                                            │
│        ▼                                                                 │
│   shop_v1 container ─────────────────────────────────────────────┐       │
│     React SPA  ──────────►  FastAPI  ──────────►  SQLite         │       │
│     (Vite build, served as static files by FastAPI)              │       │
│     /api/*  ··· catalog, cart, auth, checkout, account           │       │
│     /__test__/*  ··· reset, configure modifiers, freeze time,    │       │
│                       state, query (test-mode only)              │       │
│   ───────────────────────────────────────────────────────────────┘       │
│                                                                          │
│   Runner (revar.Runner)                                            │
│     1. env.reset(seed)                                                   │
│     2. env.configure(modifiers)                                          │
│     3. launch browser context (auth pre-filled if requested)             │
│     4. agent.run() within budget                                         │
│     5. evaluate task.success against env.query()                         │
│     6. write Trajectory artifact                                         │
└──────────────────────────────────────────────────────────────────────────┘
```

Key idea: the agent's only legal interface to shop_v1 is the browser. The
**Runner**'s only privileged channel is `/__test__/*`. **success_fn predicates
read state via SQL queries** on the same tables the site writes to, so success
is never measured by reading flaky DOM.

## Why this architecture

- **FastAPI + React + SQLite in one Docker container.** All Python on the
  agent side, including the SDK and the site backend. SQLite snapshot reset
  is fast enough that every task run can start from a known-fresh state.
- **Shared SQLModel schema** lives in `packages/shared-models`. Both the site
  (writer) and the SDK (reader, via `/__test__/query`) use the same Python
  classes. There is no JSON contract drift between the two.
- **Modifier middleware** is a process-wide config dataclass mutated by
  `/__test__/configure`. New failure modes are added by writing a single
  Starlette middleware (or extending an existing one) — no per-task code
  changes needed.

## Task YAML

A complete task:

```yaml
id: shop_v1.checkout.payment_declined_recovery
site: shop_v1
category: checkout                # find | cart | checkout | account | multistep | adversarial | mobile
hardness: medium                  # easy | medium | hard
viewport: desktop                 # desktop | mobile_iphone15 | mobile_pixel7
seed: 42                          # determines product list, user, addresses
goal: |
  Buy 1 of "Acme Bluetooth Speaker"… (NL prompt for the agent)
user_credentials:                 # if set, runner pre-auths the browser context
  email: alex@example.com
  password: password123
parameters: { product_slug: ... } # arbitrary parameters the agent prompt can reference
modifiers:
  latency_profile: fast           # fast | realistic | slow_3g | none
  payment_outcome:
    sequence: [declined, success] # consumed in order, last value sticks
  server_error_rate: 0.0
  session_ttl_s: null
  frozen_time_iso: null
success:
  type: state_predicate           # or "python" for an escape hatch
  query: |
    SELECT COUNT(*) AS count FROM "order"
    WHERE user_id = :seeded_user_id AND status = 'paid' AND payment_attempts >= 2
  predicate: result >= 1
  also_assert:
    - SELECT COUNT(*) FROM paymentattempt WHERE outcome = 'declined' >= 1
budget:
  max_steps: 40
  max_tokens: 100000
  max_wall_clock_s: 240
tags: [checkout, recovery]
```

The schema is enforced via `packages/core-py/revar/schemas/task.schema.json`
and surfaced through `revar task validate`.

## Modifier framework

Modifiers are layered onto the FastAPI app:

| Modifier | Where | What it does |
|---|---|---|
| `latency_profile` | `LatencyMiddleware` | sleeps before each `/api/*` response according to per-route min/max profile |
| `payment_outcome` | `PaymentOutcomeMiddleware` (logic in `/api/checkout/confirm`) | consumes a configured sequence; supports success / declined / 3ds_required / timeout |
| `server_error_rate` | `ServerErrorRateMiddleware` | injects 503 errors at a configurable rate on whitelisted paths |
| `session_ttl_s` | `SessionTTLMiddleware` (used in `auth.create_session`) | overrides session expiry to force re-auth |

Future adversarial modifiers (CAPTCHA, anti-bot, cookie banner, rate limit) are
v1; the v0 framework is a load-bearing demonstration that the abstraction
holds up.

## CSR realism mitigations

The SPA is client-rendered, but DOM-snapshot-before-hydration agents still see
structural content because:

1. `index.html` ships a pre-rendered shell (header, primary nav, footer, "Loading…" placeholder).
2. The FastAPI catch-all rewrites `<title>` and `<meta name="description">` per route on every SPA request.
3. Suspense boundaries with skeleton placeholders mean partial DOM is available even mid-render.

We document this trade-off explicitly so users running brittle DOM-snapshot
agents know what they're getting. v1 will revisit with a Next.js stack if
empirical evidence shows the gap matters in practice.

## Trajectories

Per-run, the Runner writes `trajectories/<timestamp>_<agent>_<task>/trajectory.json`
with per-step records (action, URL, optional screenshot path, tokens). Adapters
populate steps; the Runner adds final metrics on top.
