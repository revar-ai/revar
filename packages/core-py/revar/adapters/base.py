# SPDX-License-Identifier: Apache-2.0
"""Adapter ABC: the interface every framework adapter implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext

    from ..env import Environment
    from ..task import Task
    from ..trajectory import Trajectory


@dataclass
class Action:
    type: str  # nav | click | type | scroll | screenshot | extract | other
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterResult:
    actions_taken: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    notes: dict[str, Any] = field(default_factory=dict)


class Adapter(ABC):
    """Base class for framework adapters.

    Adapters drive the Playwright BrowserContext and emit step records into
    the provided Trajectory. Returning an AdapterResult with token counts and
    metadata lets the Runner compute consistent metrics across frameworks.
    """

    name: str = "base"

    @abstractmethod
    async def run(
        self,
        *,
        task: Task,
        env: Environment,
        context: BrowserContext,
        trajectory: Trajectory,
    ) -> AdapterResult:
        ...
