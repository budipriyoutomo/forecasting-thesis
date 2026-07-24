"""
Fase 1 — RBAC dependency require_role (FR-8.2, AGENTS.md §3 test Forbidden).
"""
import pytest

from app.api.deps import CurrentUser, require_role
from app.utils.exceptions import ForbiddenRoleError


@pytest.mark.asyncio
async def test_require_role_lolos_kalau_role_cocok():
    checker = require_role("admin")
    user = CurrentUser(user_id="u1", role="admin")

    assert await checker(user=user) is user


@pytest.mark.asyncio
async def test_require_role_menerima_beberapa_role():
    checker = require_role("admin", "ppic")
    user = CurrentUser(user_id="u1", role="ppic")

    assert await checker(user=user) is user


@pytest.mark.asyncio
async def test_require_role_forbidden_kalau_role_tak_cocok():
    checker = require_role("admin")
    user = CurrentUser(user_id="u1", role="viewer")

    with pytest.raises(ForbiddenRoleError):
        await checker(user=user)
