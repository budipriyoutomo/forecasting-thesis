"""
Seed data demo (produk, material, BOM, histori demand, konfigurasi gudang).

    python -m app.scripts.seed_demo_data                   # profil demo (UI/dev)
    python -m app.scripts.seed_demo_data --profile thesis  # profil thesis (bab hasil)

Dipakai untuk mencoba aplikasi end-to-end tanpa upload CSV manual: setelah seed,
planner bisa langsung menjalankan forecast run, breakdown material, reorder/EOQ,
validasi kapasitas gudang, cost summary, dan metrik inventory dari UI.

Sumber angka:
  - Produk & demand 2024–2025 = data riil thesis (`app/scripts/thesis_data.py`, dari
    `Simulasi Thesis.xlsx` 7 Nov 2026) — 7 SKU, 3 seri per bulan (forecast existing /
    planning / actual).

Profil `demo` (default): 2023 & Jan–Jun 2026 diturunkan DETERMINISTIK dari pola 2024
  (faktor tahunan × variasi bulanan tetap, tanpa RNG) → 42 periode. Material/BOM/gudang
  = data ilustratif packaging cup 200 ml (bukan angka thesis).
Profil `thesis` (Fase 11.11): HANYA data riil 2024–2025 (24 periode = LSTM_MIN_PERIODS),
  material/BOM 2 level/kapasitas Preform/template biaya penyimpanan dari sheet
  "Pengumpulan Data". Template biaya di-seed TIDAK aktif (biaya pesan S belum ada).
  Jalankan di database kosong: BOM produk yang sudah ada (mis. dari profil demo) tidak
  ditimpa.

Idempoten: produk/material/BOM/histori/konfigurasi yang sudah ada dilewati, tidak
ditimpa — aman dijalankan berulang. Menolak jalan di luar ENVIRONMENT=development
supaya data demo tidak menyelinap ke staging/production.
"""
import asyncio
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.config import get_settings
from app.db.session import get_sessionmaker
from app.models.bom import Bom
from app.models.demand_history import DemandHistory
from app.models.cost_template import CostTemplate, CostTemplateItem
from app.models.material import Material
from app.models.material_component import MaterialComponent
from app.models.product import Product
from app.models.upload_session import UploadSession
from app.models.warehouse import WarehouseConfig
from app.repositories.bom_repository import SqlBomRepository
from app.repositories.cost_template_repository import SqlCostTemplateRepository
from app.repositories.material_component_repository import SqlMaterialComponentRepository
from app.repositories.demand_history_repository import SqlDemandHistoryRepository
from app.repositories.material_repository import SqlMaterialRepository
from app.repositories.product_repository import SqlProductRepository
from app.repositories.upload_session_repository import SqlUploadSessionRepository
from app.repositories.user_repository import SqlUserRepository
from app.repositories.warehouse_repository import SqlWarehouseConfigRepository
from app.services.warehouse_service import CapacityInput, apply_capacity
from app.scripts.seed_dev_users import DEMO_USERS
from app.scripts.thesis_data import (
    THESIS_BOM,
    THESIS_COMPONENTS,
    THESIS_COST_ITEMS,
    THESIS_COST_TEMPLATE_NAME,
    THESIS_DEMAND_2024,
    THESIS_DEMAND_2025,
    THESIS_MATERIAL_CAPACITY,
    THESIS_MATERIALS,
)
from app.services.dev_auth import DEV_ENVIRONMENT

__all__ = [
    "DEMAND_2024",
    "DEMO_BOM",
    "DEMO_MATERIALS",
    "DEMO_PRODUCTS",
    "DEMO_WAREHOUSE_CAPACITY",
    "DemandPoint",
    "SeedSummary",
    "DEMO_PROFILE",
    "THESIS_PROFILE",
    "build_demand_series",
    "seed_demo_data",
    "run",
]


# ── Spesifikasi data demo ────────────────────────────────────────────────


@dataclass(frozen=True)
class DemoProduct:
    code: str
    name: str
    category: str
    unit: str


@dataclass(frozen=True)
class DemoMaterial:
    code: str
    name: str
    category: str
    unit: str
    lead_time_days: int
    moq: int
    dimension: dict  # meter — {length, width, height}


@dataclass(frozen=True)
class DemoBomLine:
    product_code: str
    material_code: str
    qty_per_unit: float


@dataclass(frozen=True)
class DemoWarehouseCapacity:
    """Input pallet/dus (Fase 10) — capacity_qty (PCS) dihitung `apply_capacity`."""

    product_code: str
    capacity_mode: str
    pallet_qty: float = 0
    dus_qty: float = 0
    dus_per_pallet: float | None = None
    pcs_per_dus: float | None = None


DEMO_PRODUCTS: tuple[DemoProduct, ...] = (
    DemoProduct("KBYPL 200", "KIN Yogurt Original 200ml", "RTD Yogurt", "PCS"),
    DemoProduct("KBYST 200", "KIN Yogurt Strawberry 200ml", "RTD Yogurt", "PCS"),
    DemoProduct("KBYBB 200", "KIN Yogurt Blueberry 200ml", "RTD Yogurt", "PCS"),
    DemoProduct("KBYLY 200", "KIN Yogurt Lychee 200ml", "RTD Yogurt", "PCS"),
    DemoProduct("KBYBF 200", "KIN Yogurt Black Fruit 200g", "RTD Yogurt", "PCS"),
    DemoProduct("KBYSR 200", "KIN Yoghurt Slimberries 200ml", "RTD Yogurt", "PCS"),
    DemoProduct("KBYMG 200", "KIN Yogurt Mangga 200ml", "RTD Yogurt", "PCS"),
)

# Material packaging bersama seluruh varian + label per varian (label beda desain
# per SKU → jadi contoh material yang kebutuhannya TIDAK teragregasi lintas produk).
_SHARED_MATERIALS: tuple[DemoMaterial, ...] = (
    DemoMaterial(
        "CUP-PP-200", "Cup PP 200ml", "packaging", "PCS",
        lead_time_days=21, moq=200_000,
        dimension={"length": 0.07, "width": 0.07, "height": 0.10},
    ),
    DemoMaterial(
        "LID-FOIL-200", "Lid Foil Sealing 200ml", "packaging", "PCS",
        lead_time_days=30, moq=500_000,
        dimension={"length": 0.07, "width": 0.07, "height": 0.0002},
    ),
    DemoMaterial(
        "STRAW-6MM", "Sedotan Bend 6mm (wrapped)", "packaging", "PCS",
        lead_time_days=14, moq=300_000,
        dimension={"length": 0.21, "width": 0.006, "height": 0.006},
    ),
    DemoMaterial(
        "CTN-12", "Karton Isi 12 Cup", "packaging", "PCS",
        lead_time_days=10, moq=20_000,
        dimension={"length": 0.30, "width": 0.22, "height": 0.12},
    ),
    DemoMaterial(
        "FILM-LDPE", "Shrink Film LDPE", "packaging", "KG",
        lead_time_days=21, moq=500,
        dimension={"length": 0.40, "width": 0.30, "height": 0.30},
    ),
)

_LABEL_MATERIALS: tuple[DemoMaterial, ...] = tuple(
    DemoMaterial(
        f"LBL-{product.code.split()[0]}",
        f"Label Sleeve {product.name}",
        "packaging",
        "PCS",
        lead_time_days=25,
        moq=250_000,
        dimension={"length": 0.08, "width": 0.06, "height": 0.0001},
    )
    for product in DEMO_PRODUCTS
)

DEMO_MATERIALS: tuple[DemoMaterial, ...] = _SHARED_MATERIALS + _LABEL_MATERIALS

# Pemakaian per 1 PCS produk jadi: 1 cup + 1 lid + 1 sedotan + 1 label,
# 1/12 karton (isi 12 cup), dan 0,0004 kg shrink film.
_SHARED_BOM: tuple[tuple[str, float], ...] = (
    ("CUP-PP-200", 1),
    ("LID-FOIL-200", 1),
    ("STRAW-6MM", 1),
    ("CTN-12", 1 / 12),
    ("FILM-LDPE", 0.0004),
)

DEMO_BOM: tuple[DemoBomLine, ...] = tuple(
    DemoBomLine(product.code, material_code, round(qty, 6))
    for product in DEMO_PRODUCTS
    for material_code, qty in (
        *_SHARED_BOM,
        (f"LBL-{product.code.split()[0]}", 1),
    )
)

# Kapasitas gudang per SKU — input pallet/dus/kombinasi (Fase 10), total PCS sama
# dengan angka sebelum Fase 10.
# Angka cukup longgar untuk 6 SKU pertama; KBYMG sengaja diisi longgar-pas supaya
# ada contoh yang gampang didorong ke "melebihi kapasitas" saat horizon dinaikkan.
DEMO_WAREHOUSE_CAPACITY: tuple[DemoWarehouseCapacity, ...] = (
    # (416 × 60 + 40) dus × 24 = 600.000 PCS
    DemoWarehouseCapacity("KBYPL 200", "COMBINED", pallet_qty=416, dus_qty=40, dus_per_pallet=60, pcs_per_dus=24),
    # 500 × 50 dus × 24 = 600.000 PCS
    DemoWarehouseCapacity("KBYST 200", "PALLET", pallet_qty=500, dus_per_pallet=50, pcs_per_dus=24),
    # 25.000 dus × 20 = 500.000 PCS
    DemoWarehouseCapacity("KBYBB 200", "DUS", dus_qty=25_000, pcs_per_dus=20),
    # sisanya mode DUS, 20 PCS/dus: 500.000 / 400.000 / 400.000 / 350.000 PCS
    DemoWarehouseCapacity("KBYLY 200", "DUS", dus_qty=25_000, pcs_per_dus=20),
    DemoWarehouseCapacity("KBYBF 200", "DUS", dus_qty=20_000, pcs_per_dus=20),
    DemoWarehouseCapacity("KBYSR 200", "DUS", dus_qty=20_000, pcs_per_dus=20),
    DemoWarehouseCapacity("KBYMG 200", "DUS", dus_qty=17_500, pcs_per_dus=20),
)


# ── Histori demand ───────────────────────────────────────────────────────

# Data riil 2024 per SKU: lihat `thesis_data.THESIS_DEMAND_2024` (sumber tunggal).
DEMAND_2024 = THESIS_DEMAND_2024

_WOBBLE_A = (1.05, 0.94, 1.02, 0.97, 1.08, 0.91, 1.03, 0.96, 1.06, 0.93, 1.01, 0.99)
_DERIVED_YEARS: tuple[tuple[int, float, tuple[float, ...], int], ...] = (
    (2023, 0.88, _WOBBLE_A, 12),
    (2026, 1.20, _WOBBLE_A, 6),
)


@dataclass(frozen=True)
class DemandPoint:
    period: date
    forecast_existing: int | None
    planning: int | None
    actual: int


def _scale(value: int | None, factor: float) -> int | None:
    """Skalakan satu angka; None tetap None dan 0 tetap 0 (bulan tanpa permintaan
    tidak boleh 'dihidupkan' oleh faktor pertumbuhan)."""
    if value is None:
        return None
    return int(round(value * factor))


DEMO_PROFILE = "demo"
THESIS_PROFILE = "thesis"
PROFILES = (DEMO_PROFILE, THESIS_PROFILE)


def build_demand_series(product_code: str, profile: str = DEMO_PROFILE) -> list[DemandPoint]:
    """Histori satu produk, terurut per periode.

    demo  : 42 bulan (Jan 2023 – Jun 2026); 2024–2025 riil, 2023 & 2026 turunan 2024.
    thesis: 24 bulan (Jan 2024 – Des 2025), riil saja.
    """
    real = DEMAND_2024[product_code]
    by_year: dict[int, tuple[tuple[int | None, int | None, int], ...]] = {
        2024: real,
        2025: THESIS_DEMAND_2025[product_code],
    }
    derived = _DERIVED_YEARS if profile == DEMO_PROFILE else ()
    for year, growth, wobble, n_months in derived:
        by_year[year] = tuple(
            (
                _scale(forecast_existing, growth * wobble[month]),
                _scale(planning, growth * wobble[month]),
                _scale(actual, growth * wobble[month]) or 0,
            )
            for month, (forecast_existing, planning, actual) in enumerate(real[:n_months])
        )

    return [
        DemandPoint(
            period=date(year, month + 1, 1),
            forecast_existing=values[0],
            planning=values[1],
            actual=values[2],
        )
        for year in sorted(by_year)
        for month, values in enumerate(by_year[year])
    ]


# ── Seeding ──────────────────────────────────────────────────────────────


@dataclass
class SeedSummary:
    products_created: int = 0
    materials_created: int = 0
    boms_created: int = 0
    demand_rows: int = 0
    warehouse_created: int = 0
    components_created: int = 0
    cost_templates_created: int = 0


def _dec(value) -> Decimal:
    return Decimal(str(value))


async def seed_demo_data(
    *,
    products,
    materials,
    boms,
    demand,
    warehouse,
    uploads,
    user_id: str,
    profile: str = DEMO_PROFILE,
    components=None,
    cost_templates=None,
) -> SeedSummary:
    """Buat master data + histori yang belum ada untuk `profile`. Idempoten."""
    if profile not in PROFILES:
        raise ValueError(f"Profil seed tidak dikenal: {profile!r} (pilih {', '.join(PROFILES)})")
    thesis = profile == THESIS_PROFILE
    summary = SeedSummary()
    material_specs = THESIS_MATERIALS if thesis else DEMO_MATERIALS
    bom_specs = THESIS_BOM if thesis else DEMO_BOM

    product_by_code = {}
    for spec in DEMO_PRODUCTS:
        existing = await products.get_by_code(spec.code)
        if existing is None:
            existing = await products.add(
                Product(code=spec.code, name=spec.name, category=spec.category, unit=spec.unit)
            )
            summary.products_created += 1
        product_by_code[spec.code] = existing

    material_by_code = {}
    for spec in material_specs:
        existing = await materials.get_by_code(spec.code)
        if existing is None:
            existing = await materials.add(
                Material(
                    code=spec.code,
                    name=spec.name,
                    category=spec.category,
                    unit=spec.unit,
                    lead_time_days=spec.lead_time_days,
                    moq=_dec(spec.moq),
                    dimension=getattr(spec, "dimension", None),
                )
            )
            summary.materials_created += 1
        material_by_code[spec.code] = existing

    # BOM: lewati produk yang sudah punya baris BOM (jangan tambah baris ganda).
    for spec in DEMO_PRODUCTS:
        product = product_by_code[spec.code]
        if await boms.list(str(product.id)):
            continue
        for line in (line for line in bom_specs if line.product_code == spec.code):
            await boms.add(
                Bom(
                    product_id=product.id,
                    material_id=material_by_code[line.material_code].id,
                    qty_per_unit=_dec(line.qty_per_unit),
                )
            )
            summary.boms_created += 1

    # Histori demand: butuh satu upload session sintetis sebagai induk (FK NOT NULL).
    # Sesi baru dibuat hanya kalau memang ada baris yang perlu ditulis.
    pending: list[tuple[object, list[DemandPoint]]] = []
    for spec in DEMO_PRODUCTS:
        product = product_by_code[spec.code]
        if await demand.list_for_product(str(product.id), spec.code):
            continue
        pending.append((product, build_demand_series(spec.code, profile)))

    if pending:
        n_rows = sum(len(series) for _, series in pending)
        now = datetime.now(timezone.utc)
        upload = await uploads.add(
            UploadSession(
                user_id=user_id,
                file_name=f"seed_{profile}_data.csv",
                file_url=f"seed://{profile}/seed_{profile}_data.csv",
                file_size_kb=0,
                n_rows=n_rows,
                n_products_detected=len(pending),
                preview_data=None,
                warnings=None,
                status="validated",  # sudah tervalidasi → tidak disapu cron cleanup
                expires_at=now + timedelta(days=3650),
            )
        )
        rows = [
            DemandHistory(
                product_code=product.code,
                product_id=product.id,
                period=point.period,
                forecast_existing=None
                if point.forecast_existing is None
                else _dec(point.forecast_existing),
                planning=None if point.planning is None else _dec(point.planning),
                actual=_dec(point.actual),
                upload_session_id=upload.id,
            )
            for product, series in pending
            for point in series
        ]
        summary.demand_rows = await demand.bulk_add(rows)

    if thesis:
        await _seed_thesis_extras(summary, material_by_code, warehouse, components, cost_templates)
        return summary

    for spec in DEMO_WAREHOUSE_CAPACITY:
        product = product_by_code[spec.product_code]
        if await warehouse.get_by_product(str(product.id)) is not None:
            continue
        config = WarehouseConfig(product_id=product.id)
        apply_capacity(
            config,
            CapacityInput(
                capacity_mode=spec.capacity_mode,
                pallet_qty=spec.pallet_qty,
                dus_qty=spec.dus_qty,
                dus_per_pallet=spec.dus_per_pallet,
                pcs_per_dus=spec.pcs_per_dus,
            ),
            product.unit,
        )
        await warehouse.add(config)
        summary.warehouse_created += 1

    return summary


async def _seed_thesis_extras(summary, material_by_code, warehouse, components, cost_templates) -> None:
    """BOM level 2, kapasitas material & template biaya penyimpanan (profil thesis)."""
    if components is not None:
        for spec in THESIS_COMPONENTS:
            parent = material_by_code[spec.parent_code]
            if await components.list(str(parent.id)):
                continue
            await components.add(
                MaterialComponent(
                    parent_material_id=parent.id,
                    component_material_id=material_by_code[spec.component_code].id,
                    qty_per_unit=_dec(spec.qty_per_unit),
                )
            )
            summary.components_created += 1

    for spec in THESIS_MATERIAL_CAPACITY:
        material = material_by_code[spec.material_code]
        if await warehouse.get_by_material(str(material.id)) is not None:
            continue
        config = WarehouseConfig(item_type="material", product_id=None, material_id=material.id)
        apply_capacity(
            config,
            CapacityInput(
                capacity_mode=spec.capacity_mode,
                pallet_qty=spec.pallet_qty,
                dus_per_pallet=spec.dus_per_pallet,
                pcs_per_dus=spec.pcs_per_dus,
            ),
            material.unit,
        )
        await warehouse.add(config)
        summary.warehouse_created += 1

    if cost_templates is not None and await cost_templates.get_by_name(THESIS_COST_TEMPLATE_NAME) is None:
        template = CostTemplate(
            name=THESIS_COST_TEMPLATE_NAME,
            description=(
                "Elemen biaya penyimpanan dari Simulasi Thesis (7 Nov 2026). Isi biaya pesan (S), "
                "H & i (%) lalu aktifkan — belum tersedia di data thesis."
            ),
            ordering_cost=Decimal(0),
            holding_cost=Decimal(0),
            is_active=False,
        )
        template.items = [
            CostTemplateItem(
                position=pos,
                item_type=item.item_type,
                name=item.name,
                monthly_amount=item.monthly_amount,
                period_basis=item.period_basis,
                purchase_price=item.purchase_price,
                salvage_value=item.salvage_value if item.item_type == "STORAGE_ASSET" else None,
                useful_life_months=item.useful_life_months,
                qty=item.qty,
            )
            for pos, item in enumerate(THESIS_COST_ITEMS)
        ]
        await cost_templates.add(template)
        summary.cost_templates_created += 1


def _parse_profile(argv: list[str]) -> str:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m app.scripts.seed_demo_data")
    parser.add_argument("--profile", choices=PROFILES, default=DEMO_PROFILE)
    return parser.parse_args(argv).profile


async def run(profile: str = DEMO_PROFILE) -> int:
    settings = get_settings()
    if settings.ENVIRONMENT != DEV_ENVIRONMENT:
        print(
            f"Dibatalkan: ENVIRONMENT={settings.ENVIRONMENT!r}, data demo hanya untuk "
            f"{DEV_ENVIRONMENT!r}.",
            file=sys.stderr,
        )
        return 1

    async with get_sessionmaker()() as session:
        owner = await SqlUserRepository(session).get_by_email(DEMO_USERS[1].email)  # PPIC
        if owner is None:
            print(
                "Dibatalkan: user demo belum ada. Jalankan dulu:\n"
                "  python -m app.scripts.seed_dev_users",
                file=sys.stderr,
            )
            return 1

        summary = await seed_demo_data(
            products=SqlProductRepository(session),
            materials=SqlMaterialRepository(session),
            boms=SqlBomRepository(session),
            demand=SqlDemandHistoryRepository(session),
            warehouse=SqlWarehouseConfigRepository(session),
            uploads=SqlUploadSessionRepository(session),
            user_id=str(owner.id),
            profile=profile,
            components=SqlMaterialComponentRepository(session),
            cost_templates=SqlCostTemplateRepository(session),
        )
        await session.commit()

    print(f"  produk        {summary.products_created} dibuat")
    print(f"  material      {summary.materials_created} dibuat")
    print(f"  BOM           {summary.boms_created} baris dibuat")
    print(f"  demand        {summary.demand_rows} baris dibuat")
    print(f"  gudang        {summary.warehouse_created} konfigurasi dibuat")
    if profile == THESIS_PROFILE:
        print(f"  komponen BOM  {summary.components_created} baris dibuat")
        print(f"  template biaya {summary.cost_templates_created} dibuat (belum aktif — isi S lalu aktifkan)")
    print(
        "\nLangkah berikut: login sebagai "
        f"{DEMO_USERS[1].email} lalu jalankan forecast run dari halaman Forecast."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(_parse_profile(sys.argv[1:]))))
