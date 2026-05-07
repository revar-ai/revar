# resurf-models

Shared SQLModel schema and deterministic seed data for resurf sites.

This package is imported by both the site backend (FastAPI) and the resurf SDK so that:
- There is exactly one source of truth for the data schema
- `success_fn` predicates in tasks can read backend state via the same models the site writes
- Seeded fixtures are byte-for-byte reproducible across the SDK and the site

Each site has its own subpackage (e.g. `resurf_models.shop_v1`).
