# Changelog

All notable changes to `revar` and `revar-models` are documented here. The two
packages ship in lockstep at the same version.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

## [0.1.0] - TBD

Initial public release.

### Added

- `revar` SDK: `Environment`, `Task`, `Runner`, `Trajectory`, adapter ABC.
- `shop_v1` synthetic e-commerce site (FastAPI + React + SQLite) with
  modifier middleware (`latency`, `payment_outcome`, `server_error_rate`,
  `session_ttl`, `frozen_time`).
- Adapters: `browser-use`, `stagehand`, `vision_baseline`.
- ~10 failure-mode templates and ~10 bundled tasks across find / cart /
  checkout / account / adversarial / mobile.
- CLI: `revar task new | from-template | validate | try | list`.
- `revar-models`: shared SQLModel schema + deterministic `seed_database`.
