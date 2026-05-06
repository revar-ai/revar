# Roadmap

## v0 (this release)

The initial OSS launch. Goals:

- A 5-minute quickstart that takes a developer from `pip install revar` to a passing task run.
- A site (`shop_v1`) realistic enough to surface common agent failure modes.
- A modifier framework that proves we can compose latency, payment outcomes, server errors, and session expiry per task without site code changes.
- A task authoring stack: YAML schema, ~5 templates with scripted reference trajectories, and a CLI for `task new / from-template / validate / try`.
- Three adapters: Browser Use (flagship), Stagehand (Node bridge), vision baseline (screenshot-only).

What v0 explicitly is NOT:
- A correlation study against real shopping sites
- A hosted SaaS
- A monetization plan
- A second site vertical

## v1 (next, prioritized)

In priority order:

1. **Correlation study against real OSS shop demos.** The single biggest claim revar makes is "this is realistic." We need to back it up. Pick 3 OSS shop demos (e.g. mediusion-style or Shopify hydrogen demos) and run a fixed task suite through agents on both. Publish per-task pass-rate correlation and headline R² for the suite.
2. **Adversarial modifiers.** CAPTCHA prompts, cookie banners, rate limiting, basic anti-bot heuristics (mouse movement variance, fingerprint checks). Pure additions to the modifier framework.
3. **Prompt-driven task generation (BYOK LLM).** A `revar task generate` command that, given an NL goal and live-site introspection, drafts a task YAML grounded in seeded product/user data, with a draft success predicate the user reviews before saving.
4. **shop_v2.** A second vertical (e.g. SaaS settings + admin console, or a travel-booking flow) so we have at least two unrelated domains. Forces the SDK abstractions to be site-agnostic.
5. **Native Node SDK.** Today the SDK is Python-only; Node teams use the Stagehand bridge. A first-class `@revar/sdk` Node package would close that gap.
6. **More templates.** Filling out the failure-mode template library: password reset, address change mid-checkout, filter-then-paginate, infinite-scroll-then-select, mobile checkout happy path, etc.

## After v1 (with concrete user demand)

- Hosted MVP: PR-comment posting of run results, dashboards, regression detection across PRs.
- Pro tier: image-driven authoring (screenshot of a real-site failure → generated task).
- Enterprise: private site upload, on-prem.
