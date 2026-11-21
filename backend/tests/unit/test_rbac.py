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


# ── CR v3.5 §3 — matriks role final (sumber tunggal: app/utils/permissions.py) ──

import re  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402
from pathlib import Path  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402

import jwt  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.utils.permissions import PERMISSIONS  # noqa: E402

ROLES = ("admin", "ppic", "purchasing", "viewer")
ADMIN = ("admin",)
PLANNER = ("admin", "ppic")

# Matriks CR v3.5 §3.2/§3.3 — ditulis ulang di sini (bukan diimpor) supaya perubahan
# peta izin di kode harus disengaja dan ikut mengubah test.
EXPECTED_PERMISSIONS = {
    "master.write": ADMIN,
    "settings.write": ADMIN,
    "extvar.define": ADMIN,
    "extvar.import": PLANNER,
    "data.upload": PLANNER,
    "data.import_stock": PLANNER,
    "forecast.run": PLANNER,
    "forecast.select": PLANNER,
    "override.create": PLANNER,
    "planning.run": PLANNER,
    "capacity.adjust": PLANNER,
    "user.manage": ADMIN,  # CR v3.7 — User Management
}

WRITE_ENDPOINTS: dict[tuple[str, str], str] = {
    ("POST", "/api/v1/products"): "master.write",
    ("PUT", "/api/v1/products/{product_id}"): "master.write",
    ("DELETE", "/api/v1/products/{product_id}"): "master.write",
    ("POST", "/api/v1/products/import"): "master.write",
    ("POST", "/api/v1/materials"): "master.write",
    ("PUT", "/api/v1/materials/{material_id}"): "master.write",
    ("DELETE", "/api/v1/materials/{material_id}"): "master.write",
    ("POST", "/api/v1/materials/import"): "master.write",
    ("POST", "/api/v1/materials/{material_id}/components"): "master.write",
    ("DELETE", "/api/v1/material-components/{component_id}"): "master.write",
    ("POST", "/api/v1/boms"): "master.write",
    ("PUT", "/api/v1/boms/{bom_id}"): "master.write",
    ("DELETE", "/api/v1/boms/{bom_id}"): "master.write",
    ("POST", "/api/v1/boms/bulk"): "master.write",
    ("POST", "/api/v1/boms/import"): "master.write",
    ("POST", "/api/v1/warehouse/config"): "master.write",
    ("PUT", "/api/v1/warehouse/config/{config_id}"): "master.write",
    ("DELETE", "/api/v1/warehouse/config/{config_id}"): "master.write",
    ("POST", "/api/v1/cost-templates"): "master.write",
    ("PUT", "/api/v1/cost-templates/{template_id}"): "master.write",
    ("DELETE", "/api/v1/cost-templates/{template_id}"): "master.write",
    ("POST", "/api/v1/cost-templates/{template_id}/activate"): "master.write",
    ("POST", "/api/v1/cost-templates/{template_id}/deactivate"): "master.write",
    ("PUT", "/api/v1/forecast-settings"): "settings.write",
    ("POST", "/api/v1/external-variables"): "extvar.define",
    ("PUT", "/api/v1/external-variables/{variable_id}"): "extvar.define",
    ("DELETE", "/api/v1/external-variables/{variable_id}"): "extvar.define",
    ("DELETE", "/api/v1/external-variables/{variable_id}/values"): "extvar.define",
    ("POST", "/api/v1/external-variables/values/import"): "extvar.import",
    ("PUT", "/api/v1/external-variables/{variable_id}/values"): "extvar.import",
    ("POST", "/api/v1/uploads"): "data.upload",
    ("POST", "/api/v1/stock-snapshots/import"): "data.import_stock",
    ("POST", "/api/v1/material-usage/import"): "data.import_stock",
    ("POST", "/api/v1/forecast/runs"): "forecast.run",
    ("POST", "/api/v1/forecast/results/{result_id}/selection"): "forecast.select",
    ("POST", "/api/v1/forecast/runs/{run_id}/selection"): "forecast.select",
    ("POST", "/api/v1/overrides"): "override.create",
    ("POST", "/api/v1/reorder/recommendations"): "planning.run",
    ("POST", "/api/v1/forecast/runs/{run_id}/plan"): "planning.run",
    ("POST", "/api/v1/forecast/runs/{run_id}/stock-projection"): "planning.run",
    ("POST", "/api/v1/forecast/runs/{run_id}/capacity-adjustments"): "capacity.adjust",
    ("POST", "/api/v1/forecast/runs/{run_id}/capacity-adjustments/suggest"): "capacity.adjust",
    ("POST", "/api/v1/forecast/runs/{run_id}/capacity-adjustments/reset"): "capacity.adjust",
    ("POST", "/api/v1/users"): "user.manage",
    ("PUT", "/api/v1/users/{user_id}"): "user.manage",
}
PUBLIC_WRITE = {("POST", "/api/v1/auth/login")}


def _token_headers(role: str) -> dict:
    payload = {"sub": "00000000-0000-0000-0000-0000000000aa", "role": role,
               "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    token = jwt.encode(payload, get_settings().JWT_SECRET_KEY, algorithm=get_settings().JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def _concrete(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "00000000-0000-0000-0000-000000000000", path)


def test_peta_izin_sesuai_matriks_cr_v35():
    assert {k: tuple(v) for k, v in PERMISSIONS.items()} == EXPECTED_PERMISSIONS


def test_semua_endpoint_tulis_terpetakan_ke_action():
    # Endpoint tulis baru wajib didaftarkan di matriks — tidak boleh lolos tanpa RBAC.
    ops = {
        (method.upper(), path)
        for path, item in app.openapi()["paths"].items()
        for method in item
        if method != "get"
    }
    assert ops - PUBLIC_WRITE == set(WRITE_ENDPOINTS)


@pytest_asyncio.fixture
async def rbac_client():
    # DB palsu: role yang diizinkan boleh gagal di tahap berikutnya (422/500), yang
    # diuji hanya bahwa RBAC tidak memblokir. raise_app_exceptions=False → 500 envelope.
    async def fake_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = fake_db
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize(("method", "path"), sorted(WRITE_ENDPOINTS))
async def test_endpoint_tulis_x_role_sesuai_matriks(rbac_client, method, path, role):
    action = WRITE_ENDPOINTS[(method, path)]
    kwargs = {"json": {}} if method in ("POST", "PUT") else {}
    res = await rbac_client.request(method, _concrete(path), headers=_token_headers(role), **kwargs)

    if role in EXPECTED_PERMISSIONS[action]:
        assert res.status_code != 403, f"{role} seharusnya boleh {action} ({method} {path})"
    else:
        assert res.status_code == 403, f"{role} seharusnya ditolak {action} ({method} {path})"
        assert res.json()["error"]["code"] == "AUTH_FORBIDDEN"


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ROLES)
async def test_baca_dan_export_terbuka_untuk_semua_role(rbac_client, role):
    # CR v3.5 §3.2: semua role boleh lihat & export (Viewer boleh export).
    for path in (
        "/api/v1/forecast/runs",
        "/api/v1/forecast/runs/r1/export",
        "/api/v1/reorder/recommendations/export?run_id=r1&format=xlsx",
        "/api/v1/forecast/runs/r1/stock-projection/export?format=pdf",
        "/api/v1/forecast/runs/r1/inventory-metrics/export?format=xlsx",
    ):
        res = await rbac_client.get(path, headers=_token_headers(role))
        assert res.status_code != 403, path


FRONTEND_PERMISSIONS = Path(__file__).resolve().parents[3] / "frontend" / "src" / "lib" / "permissions.ts"


@pytest.mark.skipif(not FRONTEND_PERMISSIONS.exists(), reason="frontend tidak ada (image Docker backend-only)")
def test_peta_izin_backend_sama_dengan_frontend():
    # CR v3.5 §3.6 Sinkronisasi — parse `"action": ["role", ...]` dari lib/permissions.ts.
    source = FRONTEND_PERMISSIONS.read_text(encoding="utf-8")
    block = source.split("export const PERMISSIONS", 1)[1].split("} as const", 1)[0]
    frontend = {
        key: tuple(re.findall(r'"([a-z_]+)"', roles))
        for key, roles in re.findall(r'"([a-z_.]+)":\s*\[([^\]]*)\]', block)
    }
    assert frontend == {k: tuple(v) for k, v in PERMISSIONS.items()}


# CR v3.5 §5.1 — import master data tanpa UI: ditandai internal (seed/migrasi), tetap master.write.
INTERNAL_IMPORTS = ("/api/v1/products/import", "/api/v1/materials/import", "/api/v1/boms/import")


@pytest.mark.parametrize("path", INTERNAL_IMPORTS)
def test_import_master_data_ditandai_internal(path):
    op = app.openapi()["paths"][path]["post"]
    assert "internal" in op["tags"]
    assert op.get("x-internal") is True
    assert "seed" in op["description"].lower()
    assert WRITE_ENDPOINTS[("POST", path)] == "master.write"


def test_hanya_import_master_data_yang_internal():
    internal = {
        path
        for path, item in app.openapi()["paths"].items()
        for op in item.values()
        if op.get("x-internal")
    }
    assert internal == set(INTERNAL_IMPORTS)
