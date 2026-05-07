# SPDX-License-Identifier: Apache-2.0
"""Schema validation, template rendering, and task loading tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from resurf.task import Task, validate_task_dict
from resurf.templating import parse_template_header, render_template_to_dict

REPO = Path(__file__).resolve().parents[3]


def test_repo_is_findable():
    assert (REPO / "tasks").is_dir()
    assert (REPO / "templates").is_dir()


def test_all_bundled_tasks_validate():
    tasks_dir = REPO / "tasks"
    paths = list(tasks_dir.rglob("*.yaml"))
    assert paths, "expected at least one bundled task yaml"
    for p in paths:
        data = yaml.safe_load(p.read_text())
        validate_task_dict(data)
        # also exercise Task construction
        Task.from_yaml(p)


def test_template_renders_with_required_params():
    template = REPO / "templates" / "catalog" / "find_product_by_name.yaml.j2"
    data = render_template_to_dict(
        template,
        {"product_name": "Acme Bluetooth Speaker", "product_slug": "acme-bluetooth-speaker"},
    )
    validate_task_dict(data)
    assert data["category"] == "find"
    assert "Acme Bluetooth Speaker" in data["goal"]


def test_template_header_parses():
    template = REPO / "templates" / "checkout" / "buy_with_coupon.yaml.j2"
    header = parse_template_header(template)
    assert "parameters" in header
    assert header["parameters"]["coupon"]["required"] is True


def test_invalid_task_raises():
    bad = {
        "id": "INVALID-NAME",  # not snake_dotted
        "site": "shop_v1",
        "category": "find",
        "goal": "do thing",
        "success": {"type": "state_predicate", "query": "SELECT 1", "predicate": "True"},
    }
    with pytest.raises(ValueError):
        validate_task_dict(bad)


def test_task_generator_renders_combos():
    from resurf.task import TaskGenerator

    gen = TaskGenerator(
        template_path=str(REPO / "templates" / "catalog" / "find_product_by_name.yaml.j2"),
        site="shop_v1",
        parameters={
            "product_name": ["Acme Bluetooth Speaker", "Northwood Pulse Watch"],
            "product_slug": ["acme-bluetooth-speaker", "northwood-pulse-watch"],
        },
    )
    tasks = list(gen.generate())
    # 2x2 combinations (we don't filter mismatched name/slug pairs in v0)
    assert len(tasks) == 4
    assert all(t.site == "shop_v1" for t in tasks)
