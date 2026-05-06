# SPDX-License-Identifier: Apache-2.0
from fastapi import APIRouter

from ..modifiers import get_config

router = APIRouter()


@router.get("/api/health")
def health() -> dict:
    return {"ok": True, "modifiers": get_config().to_dict()}
