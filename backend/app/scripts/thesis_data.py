"""
Data riil thesis untuk seed & golden test (Fase 11.11, v3.3) — konstanta murni, tanpa I/O.

Sumber: `Simulasi Thesis.xlsx` versi 7 Nov 2026 (Noviana Asmoro):
  - "Bab I Plan vs Forecast": demand 2024 (baris 11–17) & 2025 (baris 34–40), blok
    7 kolom per bulan → diambil (Forecast existing, Planning, Actual).
  - "Pengumpulan Data": BOM 3 level, kapasitas gudang per material group, lead time
    pemesanan, elemen biaya penyimpanan.

Asumsi / data yang BELUM ada di Excel (⛔ docs/TODO-v3.md Fase 11.11/11.12):
  - "Yoghurt SB" di BOM ambigu (KBYST Strawberry / KBYSR Slimberries) → keputusan user
    7 Nov 2026: KEDUANYA memakai Cap Red + Bottle White (Cap Red jadi material bersama).
  - Kapasitas Cap = SATU angka untuk 6 warna (group); sistem menyimpan kapasitas per
    material → hanya dicatat sebagai referensi (`CAP_GROUP_CAPACITY`), tidak di-seed.
  - Lead time Bottle White tidak tercantum; dipakai 7 hari (= Preform, bahan bakunya).
  - Harga material, MOQ, biaya pesan (S), stok awal, kedatangan, pemakaian aktual
    belum ada → harga NULL (EOQ jatuh ke dinamis), MOQ 0, template biaya TIDAK aktif.
  - Juni 2025 bernilai 0 untuk 6 dari 7 SKU — keputusan user 7 Nov 2026: dipakai apa
    adanya (dianggap memang tidak produksi).
"""
from dataclasses import dataclass
from decimal import Decimal

THESIS_PRODUCT_CODES: tuple[str, ...] = (
    "KBYPL 200", "KBYST 200", "KBYBB 200", "KBYLY 200", "KBYBF 200", "KBYSR 200", "KBYMG 200",
)

# 12 bulan × (forecast_existing, planning, actual) per SKU.
THESIS_DEMAND_2024: dict[str, tuple[tuple[int | None, int | None, int], ...]] = {
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

THESIS_DEMAND_2025: dict[str, tuple[tuple[int, int, int], ...]] = {
    "KBYPL 200": (
        (141300, 188400, 186696), (471000, 94200, 91512), (235500, 235512, 233232),
        (235500, 235512, 233568), (423900, 329712, 325344), (0, 188400, 186840),
        (376800, 471024, 464544), (376800, 565200, 558408), (423900, 423912, 418272),
        (188400, 47112, 44376), (329700, 141312, 138192), (235500, 235512, 215376),
    ),
    "KBYST 200": (
        (141372, 164928, 164520), (376992, 47136, 45336), (141372, 141384, 140784),
        (141372, 141384, 140976), (329868, 282744, 280368), (0, 0, 0),
        (282744, 424128, 414816), (282744, 329880, 327792), (282744, 188496, 185496),
        (188496, 113088, 110160), (235620, 141384, 138864), (141372, 141384, 139392),
    ),
    "KBYBB 200": (
        (188592, 235752, 232080), (471480, 70728, 69264), (330036, 330048, 328152),
        (330036, 282888, 276456), (377184, 235752, 234648), (0, 0, 0),
        (377184, 518640, 508560), (330036, 471480, 466992), (377184, 282888, 275784),
        (235740, 66000, 63480), (235740, 141456, 139104), (188592, 188592, 185064),
    ),
    "KBYLY 200": (
        (47124, 47124, 41880), (47124, 47136, 36912), (0, 0, 0),
        (0, 47136, 44352), (47124, 47136, 45192), (0, 47136, 45744),
        (47124, 47136, 45408), (47124, 94248, 92136), (47124, 47136, 44448),
        (47124, 47136, 44856), (65973, 47136, 44856), (47124, 47136, 45504),
    ),
    "KBYBF 200": (
        (300024, 300024, 298536), (450036, 150024, 148224), (400032, 400032, 392736),
        (400032, 200016, 192576), (400032, 250032, 244368), (0, 0, 0),
        (400032, 550056, 539640), (400032, 500040, 491448), (400032, 250032, 243408),
        (300024, 200016, 197184), (250020, 100008, 88320), (200016, 150024, 145728),
    ),
    "KBYSR 200": (
        (47136, 94272, 93072), (141408, 47136, 42432), (0, 0, 0),
        (0, 47136, 44496), (94272, 70704, 69864), (0, 0, 0),
        (94272, 141408, 139608), (94272, 94272, 91008), (94272, 141408, 136032),
        (94272, 47136, 45456), (65990, 47136, 45072), (47136, 0, 0),
    ),
    "KBYMG 200": (
        (142164, 189552, 186984), (379104, 94776, 91488), (165858, 165864, 163872),
        (165858, 94776, 93120), (189552, 47400, 44928), (0, 0, 0),
        (189552, 284328, 277608), (236940, 284328, 276912), (236940, 236952, 229488),
        (75820, 47400, 44760), (142164, 75816, 70608), (142164, 66336, 64272),
    ),
}


@dataclass(frozen=True)
class ThesisMaterial:
    code: str
    name: str
    category: str
    unit: str
    lead_time_days: int
    moq: int = 0


THESIS_MATERIALS: tuple[ThesisMaterial, ...] = (
    ThesisMaterial("CAP-BLUE", "Cap Blue", "cap", "PCS", 7),
    ThesisMaterial("CAP-RED", "Cap Red", "cap", "PCS", 7),
    ThesisMaterial("CAP-PURPLE", "Cap Purple", "cap", "PCS", 7),
    ThesisMaterial("CAP-WHITE", "Cap White", "cap", "PCS", 7),
    ThesisMaterial("CAP-GREY", "Cap Grey", "cap", "PCS", 7),
    ThesisMaterial("CAP-YELLOW", "Cap Yellow", "cap", "PCS", 7),
    ThesisMaterial("BTL-WHITE", "Bottle White", "bottle", "PCS", 7),
    ThesisMaterial("PRF-WHITE", "Preform White", "preform", "PCS", 7),
)


@dataclass(frozen=True)
class ThesisBomLine:
    product_code: str
    material_code: str
    qty_per_unit: float


_CAP_BY_PRODUCT = {
    "KBYPL 200": "CAP-BLUE",  # Yoghurt PL
    "KBYST 200": "CAP-RED",  # Yoghurt SB — keputusan user: KBYST & KBYSR
    "KBYSR 200": "CAP-RED",  # sama-sama Cap Red
    "KBYBB 200": "CAP-PURPLE",  # Yoghurt BB
    "KBYLY 200": "CAP-WHITE",  # Yoghurt LY
    "KBYBF 200": "CAP-GREY",  # Yoghurt BF
    "KBYMG 200": "CAP-YELLOW",  # Yoghurt MG
}

# BOM level 1 (tabel `boms`): 1 PCS produk = 1 Cap warna + 1 Bottle White (7 SKU, 14 baris).
THESIS_BOM: tuple[ThesisBomLine, ...] = tuple(
    line
    for product, cap in _CAP_BY_PRODUCT.items()
    for line in (ThesisBomLine(product, cap, 1), ThesisBomLine(product, "BTL-WHITE", 1))
)


@dataclass(frozen=True)
class ThesisComponent:
    parent_code: str
    component_code: str
    qty_per_unit: float


# BOM level 2 (`material_components`, informasi — Keputusan #4): 1 Bottle = 1 Preform.
THESIS_COMPONENTS: tuple[ThesisComponent, ...] = (ThesisComponent("BTL-WHITE", "PRF-WHITE", 1),)


@dataclass(frozen=True)
class ThesisMaterialCapacity:
    material_code: str
    capacity_mode: str
    pallet_qty: float
    dus_per_pallet: float
    pcs_per_dus: float


# Kapasitas gudang Preform: 346 pallet = 346 CTN = 5.555.376 pcs (1 CTN/pallet, 16.056 pcs/CTN).
THESIS_MATERIAL_CAPACITY: tuple[ThesisMaterialCapacity, ...] = (
    ThesisMaterialCapacity("PRF-WHITE", "PALLET", pallet_qty=346, dus_per_pallet=1, pcs_per_dus=16_056),
)

# Kapasitas group Cap (6 warna berbagi): 171 pallet × 25 CTN × 3.000 pcs = 12.825.000 pcs.
# Keputusan user 7 Nov 2026: TIDAK di-seed sampai penulis memberi angka per warna (utilisasi
# Cap tampil "—"); tidak ada angka karangan.
CAP_GROUP_CAPACITY = {"pallet": 171, "ctn_per_pallet": 25, "pcs_per_ctn": 3000, "pcs": 12_825_000}


@dataclass
class ThesisCostItem:
    item_type: str  # OVERHEAD | STORAGE_ASSET
    name: str
    qty: Decimal
    monthly_amount: Decimal | None = None
    purchase_price: Decimal | None = None
    useful_life_months: int | None = None
    salvage_value: Decimal = Decimal(0)
    period_basis: str = "monthly"


THESIS_COST_TEMPLATE_NAME = "Thesis 2026 — Biaya Penyimpanan Material"

# Elemen biaya penyimpanan (Excel "Pengumpulan Data" L:Q). Aset: lifetime tahun × 12.
THESIS_COST_ITEMS: tuple[ThesisCostItem, ...] = (
    ThesisCostItem("OVERHEAD", "Tenaga Kerja Langsung (Operator)", Decimal(2), monthly_amount=Decimal("3972202")),
    ThesisCostItem("OVERHEAD", "Listrik (1.392 kWh/bulan)", Decimal(1), monthly_amount=Decimal("1619870.4")),
    ThesisCostItem("STORAGE_ASSET", "Lampu", Decimal(50), purchase_price=Decimal("1000000"), useful_life_months=36),
    ThesisCostItem("STORAGE_ASSET", "Forklift", Decimal(1), purchase_price=Decimal("400000000"), useful_life_months=180),
    ThesisCostItem("STORAGE_ASSET", "Handpallet", Decimal(2), purchase_price=Decimal("2500000"), useful_life_months=60),
    ThesisCostItem("STORAGE_ASSET", "Pallet Plastik", Decimal(517), purchase_price=Decimal("500000"), useful_life_months=60),
)
