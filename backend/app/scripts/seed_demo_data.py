"""
Seed data demo (produk, material, BOM, histori demand, konfigurasi gudang).

    python -m app.scripts.seed_demo_data

Dipakai untuk mencoba aplikasi end-to-end tanpa upload CSV manual: setelah seed,
planner bisa langsung menjalankan forecast run, breakdown material, reorder/EOQ,
validasi kapasitas gudang, cost summary, dan metrik inventory dari UI.

Sumber angka:
  - Produk & demand 2024 = data riil thesis (`Simulasi Thesis.xlsx`, sheet
    "Bab I Plan vs Forecast") — 7 SKU minuman RTD, 3 seri paralel per bulan
    (forecast existing / planning / actual).
  - 2023 & 2025 diturunkan DETERMINISTIK dari pola 2024 (faktor tahunan × variasi
    bulanan tetap, tanpa RNG) supaya histori jadi 36 periode — cukup panjang untuk
    seluruh engine termasuk LSTM (`LSTM_MIN_PERIODS`, default 24).
  - Material/BOM/gudang = data ilustratif packaging cup 200 ml yang konsisten
    secara fisik (dimensi & qty per palet), bukan angka dari thesis.

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
from app.models.material import Material
from app.models.product import Product
from app.models.upload_session import UploadSession
from app.models.warehouse import WarehouseConfig
from app.repositories.bom_repository import SqlBomRepository
from app.repositories.demand_history_repository import SqlDemandHistoryRepository
from app.repositories.material_repository import SqlMaterialRepository
from app.repositories.product_repository import SqlProductRepository
from app.repositories.upload_session_repository import SqlUploadSessionRepository
from app.repositories.user_repository import SqlUserRepository
from app.repositories.warehouse_repository import SqlWarehouseConfigRepository
from app.scripts.seed_dev_users import DEMO_USERS
from app.services.dev_auth import DEV_ENVIRONMENT

__all__ = [
    "DEMAND_2024",
    "DEMO_BOM",
    "DEMO_MATERIALS",
    "DEMO_PRODUCTS",
    "DEMO_WAREHOUSE",
    "DemandPoint",
    "SeedSummary",
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
    qty_per_pallet: int
    dimension: dict  # meter — {length, width, height}


@dataclass(frozen=True)
class DemoBomLine:
    product_code: str
    material_code: str
    qty_per_unit: float


@dataclass(frozen=True)
class DemoWarehouse:
    category: str
    warehouse_area_m2: float
    pallet_dimension: dict  # meter


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
        lead_time_days=21, moq=200_000, qty_per_pallet=24_000,
        dimension={"length": 0.07, "width": 0.07, "height": 0.10},
    ),
    DemoMaterial(
        "LID-FOIL-200", "Lid Foil Sealing 200ml", "packaging", "PCS",
        lead_time_days=30, moq=500_000, qty_per_pallet=120_000,
        dimension={"length": 0.07, "width": 0.07, "height": 0.0002},
    ),
    DemoMaterial(
        "STRAW-6MM", "Sedotan Bend 6mm (wrapped)", "packaging", "PCS",
        lead_time_days=14, moq=300_000, qty_per_pallet=200_000,
        dimension={"length": 0.21, "width": 0.006, "height": 0.006},
    ),
    DemoMaterial(
        "CTN-12", "Karton Isi 12 Cup", "packaging", "PCS",
        lead_time_days=10, moq=20_000, qty_per_pallet=800,
        dimension={"length": 0.30, "width": 0.22, "height": 0.12},
    ),
    DemoMaterial(
        "FILM-LDPE", "Shrink Film LDPE", "packaging", "KG",
        lead_time_days=21, moq=500, qty_per_pallet=600,
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
        qty_per_pallet=150_000,
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

# Gudang packaging: palet standar 1,2 × 1,0 m (tanpa racking, sesuai batasan thesis)
# → kapasitas = 4000 ÷ 1,2 = 3333 palet. Cukup untuk horizon 6 bulan seluruh SKU;
# turunkan luasnya dari halaman Warehouse untuk melihat flag melebihi kapasitas.
DEMO_WAREHOUSE = DemoWarehouse(
    category="packaging",
    warehouse_area_m2=4000,
    pallet_dimension={"length": 1.2, "width": 1.0, "height": 1.5},
)


# ── Histori demand ───────────────────────────────────────────────────────

# Data riil 2024 per SKU: 12 bulan × (forecast_existing, planning, actual).
DEMAND_2024: dict[str, tuple[tuple[int | None, int | None, int], ...]] = {
    "KBYPL 200": (
        (423900, 423912, 408768), (376800, 376800, 366888), (329700, 329712, 319392),
        (329700, 235512, 227208), (376800, 282600, 274296), (376800, 847800, 822168),
        (518100, 518112, 493608), (471000, 188400, 178032), (282600, 235512, 228888),
        (282600, 376800, 371376), (423900, 565200, 566064), (329700, 518112, 516576),
    ),
    "KBYST 200": (
        (376992, 376992, 364728), (282744, 188496, 182376), (306306, 306312, 299400),
        (329868, 235632, 229176), (329868, 188496, 181992), (518364, 801120, 779304),
        (518364, 494808, 483048), (188496, 282744, 275544), (376992, 376992, 374400),
        (94248, 188496, 182376), (282744, 282744, 278928), (329868, 329880, 329088),
    ),
    "KBYBB 200": (
        (471480, 424344, 412992), (330036, 330048, 324048), (330036, 330048, 321048),
        (377184, 330048, 369672), (282888, 188592, 182160), (235740, 518640, 504888),
        (660072, 377208, 369720), (565776, 471480, 456696), (565776, 612936, 601320),
        (188592, 282888, 274656), (424332, 471480, 467688), (377184, 282888, 279888),
    ),
    "KBYLY 200": (
        (70686, 70680, 68136), (47124, 47136, 44568), (70686, 94248, 73200),
        (47124, 47136, 45000), (47124, 70680, 69192), (0, 47136, 45648),
        (47124, 47136, 45024), (47124, 47136, 45216), (70686, 70680, 68088),
        (0, 70680, 66216), (70686, 70680, 64896), (70686, 0, 0),
    ),
    "KBYBF 200": (
        (275022, 275016, 267216), (300024, 300048, 288120), (300024, 300048, 291360),
        (300024, 250032, 287496), (350028, 300024, 288960), (250020, 600072, 564456),
        (400032, 200040, 191280), (600048, 400032, 388800), (700056, 750072, 728712),
        (200016, 300024, 286704), (500040, 500040, 488376), (350028, 200016, 198552),
    ),
    "KBYSR 200": (
        (0, 0, 0), (70704, 94272, 89832), (141408, 141408, 133752),
        (94272, 70704, 67224), (188544, 117840, 113040), (0, 70704, 59064),
        (94272, 94272, 90216), (235680, 235680, 228456), (188544, 188544, 182472),
        (0, 94272, 86976), (47136, 94272, 87456), (141408, 117840, 111912),
    ),
    "KBYMG 200": (
        (94776, 94776, 89712), (0, 0, 0), (94776, 47400, 43152),
        (47388, 71088, 67968), (94776, 47400, 45624), (0, 379104, 368184),
        (284328, 236952, 229392), (473880, 473904, 461976), (379104, 355440, 342696),
        (0, 94776, 88104), (568656, 568656, 560112), (189552, 355416, 351768),
    ),
}

# Tahun turunan: faktor pertumbuhan tahunan × variasi bulanan tetap (bukan RNG,
# supaya deret persis sama tiap kali di-seed dan hasil forecast bisa dibandingkan).
# Entri: (tahun, faktor pertumbuhan, variasi per bulan, jumlah bulan). 2026 sengaja
# setengah tahun — histori berhenti Juni 2026 supaya forecast run benar-benar
# meramal periode yang belum terjadi.
_WOBBLE_A = (1.05, 0.94, 1.02, 0.97, 1.08, 0.91, 1.03, 0.96, 1.06, 0.93, 1.01, 0.99)
_WOBBLE_B = (0.96, 1.07, 0.93, 1.05, 0.98, 1.09, 0.94, 1.02, 0.97, 1.06, 0.92, 1.04)

_DERIVED_YEARS: tuple[tuple[int, float, tuple[float, ...], int], ...] = (
    (2023, 0.88, _WOBBLE_A, 12),
    (2025, 1.12, _WOBBLE_B, 12),
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


def build_demand_series(product_code: str) -> list[DemandPoint]:
    """Histori 42 bulan (Jan 2023 – Jun 2026) satu produk, terurut per periode.

    2024 = angka riil thesis apa adanya; tahun lain diturunkan deterministik.
    """
    real = DEMAND_2024[product_code]
    by_year: dict[int, tuple[tuple[int | None, int | None, int], ...]] = {2024: real}
    for year, growth, wobble, n_months in _DERIVED_YEARS:
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
    warehouse_created: bool = False


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
) -> SeedSummary:
    """Buat master data + histori demo yang belum ada. Idempoten."""
    summary = SeedSummary()

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
    for spec in DEMO_MATERIALS:
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
                    dimension=spec.dimension,
                    qty_per_pallet=_dec(spec.qty_per_pallet),
                )
            )
            summary.materials_created += 1
        material_by_code[spec.code] = existing

    # BOM: lewati produk yang sudah punya baris BOM (jangan tambah baris ganda).
    for spec in DEMO_PRODUCTS:
        product = product_by_code[spec.code]
        if await boms.list(str(product.id)):
            continue
        for line in (line for line in DEMO_BOM if line.product_code == spec.code):
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
        pending.append((product, build_demand_series(spec.code)))

    if pending:
        n_rows = sum(len(series) for _, series in pending)
        now = datetime.now(timezone.utc)
        upload = await uploads.add(
            UploadSession(
                user_id=user_id,
                file_name="seed_demo_data.csv",
                file_url="seed://demo/seed_demo_data.csv",
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

    if await warehouse.get_by_category(DEMO_WAREHOUSE.category) is None:
        await warehouse.add(
            WarehouseConfig(
                category=DEMO_WAREHOUSE.category,
                warehouse_area_m2=_dec(DEMO_WAREHOUSE.warehouse_area_m2),
                pallet_dimension=DEMO_WAREHOUSE.pallet_dimension,
            )
        )
        summary.warehouse_created = True

    return summary


async def run() -> int:
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
        )
        await session.commit()

    print(f"  produk        {summary.products_created} dibuat")
    print(f"  material      {summary.materials_created} dibuat")
    print(f"  BOM           {summary.boms_created} baris dibuat")
    print(f"  demand        {summary.demand_rows} baris dibuat")
    print(f"  gudang        {'dibuat' if summary.warehouse_created else 'sudah ada'}")
    print(
        "\nLangkah berikut: login sebagai "
        f"{DEMO_USERS[1].email} lalu jalankan forecast run dari halaman Forecast."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
