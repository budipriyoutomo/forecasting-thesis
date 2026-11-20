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
  - Kapasitas Cap = SATU angka untuk 6 warna (group). Sejak 19 Nov 2026 sistem menyimpan
    kapasitas per GRUP material (`materials.category`) → di-seed sebagai grup "cap".
  - Lead time Bottle White tidak tercantum; dipakai 7 hari (= Preform, bahan bakunya).
  - Harga material, MOQ, biaya pesan (S), stok awal, kedatangan, pemakaian aktual
    belum ada → harga NULL (EOQ jatuh ke dinamis), MOQ 0, template biaya TIDAK aktif.
  - Juni 2025 bernilai 0 untuk 6 dari 7 SKU — keputusan user 7 Nov 2026: dipakai apa
    adanya (dianggap memang tidak produksi).
"""
from dataclasses import dataclass
from datetime import date
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
    material_group: str  # = ThesisMaterial.category
    capacity_mode: str
    pallet_qty: float
    dus_per_pallet: float
    pcs_per_dus: float


# Kapasitas group Cap (6 warna berbagi): 171 pallet × 25 CTN × 3.000 pcs = 12.825.000 pcs.
# Dulu (7 Nov 2026) tidak di-seed karena sistem hanya bisa per material; sejak 19 Nov 2026
# kapasitas per grup material, jadi angka Excel ini dipakai apa adanya.
CAP_GROUP_CAPACITY = {"pallet": 171, "ctn_per_pallet": 25, "pcs_per_ctn": 3000, "pcs": 12_825_000}

THESIS_MATERIAL_CAPACITY: tuple[ThesisMaterialCapacity, ...] = (
    # Preform: 346 pallet = 346 CTN = 5.555.376 pcs (1 CTN/pallet, 16.056 pcs/CTN).
    ThesisMaterialCapacity("preform", "PALLET", pallet_qty=346, dus_per_pallet=1, pcs_per_dus=16_056),
    ThesisMaterialCapacity(
        "cap", "PALLET",
        pallet_qty=CAP_GROUP_CAPACITY["pallet"],
        dus_per_pallet=CAP_GROUP_CAPACITY["ctn_per_pallet"],
        pcs_per_dus=CAP_GROUP_CAPACITY["pcs_per_ctn"],
    ),
)


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


# ── CR v3.4 §4.7 — variabel eksternal (sheet "Pengumpulan Data", tabel *Variabel Peramalan*
# kolom S–AV baris 5–40 = Jan 2024 – Des 2026). Diekstrak dari `Simulasi Thesis (2).xlsx`
# (19 Nov 2026) lewat `parse_decimal_id` lalu dibulatkan 4 desimal (= Numeric(18,4) di DB).
#
# Pembersihan:
#   - `harga_efektif` dihitung ulang = Harga Promo (U) bila > 0, else Harga normal (T) — sama
#     dengan rumus AN, tetapi Nov–Des 2026 jadi kosong (AN = 0 karena T kosong, bukan harga 0)
#   - Kode Cuaca/Musim (Y: 1 Hujan, 2 Kemarau, 3 Peralihan) → one-hot `musim_hujan`,
#     `musim_kemarau` (Peralihan = keduanya 0) supaya tidak ada urutan palsu
#   - sel `NA` / `-` / `#DIV/0!` → None (tidak di-seed)
#   - TIDAK di-seed: Harga Promo (U, terwakili `harga_efektif`), Harga Produk (AN = harga_efektif)
#   - Perubahan harga (AO) dihitung ulang dari harga_efektif (AO Excel Nov–Des 2026 rusak)
#
# Variabel aktif: 8 dari CR v3.4 §5 + seluruh kategori *Perilaku Konsumen* & *Ekonomi*
# (keputusan penulis 20 Nov 2026: tampilkan apa adanya), TERMASUK Permintaan (AM),
# Perubahan permintaan (AP) & Ep (AQ). ⚠️ LEAKAGE: AM = Σ planning bulan yang sama, korelasi
# 1,00 dengan Σ actual 7 SKU, dan planning baru ada setelah forecast dibuat — akurasi model
# dengan variabel ini tidak mencerminkan kondisi operasional. Wajib disebut di thesis.
# Sisanya nonaktif sebagai cadangan uji sensitivitas. Semua global.

THESIS_EXOG_START = date(2024, 1, 1)
THESIS_EXOG_SCENARIOS = ("asumsi", "realisasi")

# Aturan nilai horizon 2026 untuk skenario "asumsi" (CR v3.4 §5 no. 6–7):
#   known         — diketahui di muka (rencana harga/promo, kalender) → realisasi 2026;
#                   bila kosong di Excel → bulan yang sama 2025
#   seasonal_mean — rata-rata bulan yang sama 2024 & 2025 (cuaca, Google Trends)
#   same_month    — nilai bulan yang sama 2025 (flag musim; rata-rata flag bukan 0/1)
#   last_value    — nilai Des 2025 / naive (inflasi, harga & promo kompetitor — tidak
#                   diketahui perusahaan di muka)
#   zero_fill     — nilai Excel bila ada, selain itu 0 — SELURUH 36 bulan & kedua skenario.
#                   Keputusan penulis 20 Nov 2026: sel kosong/error (`-`, `#DIV/0!`) = 0 karena
#                   datanya memang tidak tersedia (TBI, pendapatan, Permintaan, Perubahan
#                   permintaan, Ep)
#   price_change  — dihitung dari `harga_efektif` skenario yang sama: (Hₜ − Hₜ₋₁)/((Hₜ + Hₜ₋₁)/2),
#                   rumus kolom AO; bulan pertama / harga kosong → 0
#   none          — hanya realisasi Excel, tidak diisi ke depan



@dataclass(frozen=True)
class ThesisExternalVariable:
    code: str
    name: str
    value_type: str  # numeric | flag
    unit: str | None
    is_active: bool
    horizon_rule: str  # known | seasonal_mean | same_month | last_value | none
    description: str
    scope: str = "global"


THESIS_EXTERNAL_VARIABLES: tuple[ThesisExternalVariable, ...] = (
    ThesisExternalVariable("harga_efektif", "Harga produk efektif", "numeric", "Rp", True, "known",
                           "Harga promo bila ada, else harga normal (kolom T/U). Mewakili promo & diskon."),
    ThesisExternalVariable("harga_normal", "Harga normal", "numeric", "Rp", False, "known", "Kolom T."),
    ThesisExternalVariable("harga_kompetitor", "Harga kompetitor (Cimory)", "numeric", "Rp", True, "last_value",
                           "Kolom V."),
    ThesisExternalVariable("suhu", "Temperatur", "numeric", "°C", True, "seasonal_mean", "BMKG, kolom W."),
    ThesisExternalVariable("musim_hujan", "Musim hujan", "flag", None, False, "same_month",
                           "Kode cuaca/musim (Y) = 1 Hujan."),
    ThesisExternalVariable("musim_kemarau", "Musim kemarau", "flag", None, False, "same_month",
                           "Kode cuaca/musim (Y) = 2 Kemarau. Peralihan = kedua flag 0."),
    ThesisExternalVariable("curah_hujan", "Kode curah hujan", "numeric", None, False, "seasonal_mean",
                           "Ordinal 1 Rendah – 4 Sangat tinggi, kolom AA (BMKG)."),
    ThesisExternalVariable("promo", "Promosi produk", "flag", None, False, "known",
                           "Kolom AB. Redundan dengan harga_efektif (r ≈ 0,99 dengan diskon)."),
    ThesisExternalVariable("hari_promo", "Hari promosi produk", "numeric", "hari", False, "known",
                           "Kolom AC. Ada NA (Jun 2024, Okt 2026)."),
    ThesisExternalVariable("diskon_produk", "Diskon produk", "numeric", "fraksi", False, "known",
                           "Kolom AD (0–1). Redundan dengan harga_efektif (r = −1,00)."),
    ThesisExternalVariable("hari_promo_kompetitor", "Hari promosi kompetitor", "numeric", "hari", False,
                           "last_value", "Kolom AE."),
    ThesisExternalVariable("diskon_kompetitor", "Diskon kompetitor", "numeric", "fraksi", True, "last_value",
                           "Kolom AF (0–1)."),
    ThesisExternalVariable("hari_libur_sekolah", "Hari libur sekolah", "numeric", "hari", True, "known",
                           "Kalender pendidikan, kolom AG."),
    ThesisExternalVariable("hari_prj", "Hari PRJ", "numeric", "hari", False, "known", "Kolom AH (Jun–Jul)."),
    ThesisExternalVariable("idul_fitri", "Idul Fitri", "flag", None, True, "known", "Kalender Kemenag, kolom AI."),
    ThesisExternalVariable("natal", "Natal", "flag", None, False, "known",
                           "Kolom AJ. Selalu Desember → sudah terwakili fitur month."),
    ThesisExternalVariable("tahun_baru", "Tahun Baru", "flag", None, False, "known",
                           "Kolom AK. Selalu Januari → sudah terwakili fitur month."),
    ThesisExternalVariable("tbi", "Preferensi merk (TBI)", "numeric", None, True, "zero_fill",
                           "Perilaku konsumen, kolom AL. Hanya 3 bulan berisi; kosong = 0 (data tidak tersedia)."),
    ThesisExternalVariable("permintaan", "Permintaan (Σ planning 7 SKU)", "numeric", "pcs", True, "zero_fill",
                           "Kolom AM. LEAKAGE: Σ planning bulan yang sama ≈ Σ actual (r = 1,00) dan belum ada "
                           "saat meramal. Diaktifkan atas keputusan penulis 20 Nov 2026; kosong = 0."),
    ThesisExternalVariable("perubahan_harga", "Perubahan harga", "numeric", "fraksi", True, "price_change",
                           "Perilaku konsumen, kolom AO: (Hₜ − Hₜ₋₁)/((Hₜ + Hₜ₋₁)/2) dari harga_efektif."),
    ThesisExternalVariable("perubahan_permintaan", "Perubahan permintaan", "numeric", "fraksi", True, "zero_fill",
                           "Kolom AP, turunan Permintaan (AM) → LEAKAGE. Diaktifkan atas keputusan penulis "
                           "20 Nov 2026; kosong = 0."),
    ThesisExternalVariable("ep", "Sensitivitas harga (Ep)", "numeric", None, True, "zero_fill",
                           "Kolom AQ = AP/AO, turunan Permintaan → LEAKAGE. #DIV/0! = 0. Diaktifkan atas "
                           "keputusan penulis 20 Nov 2026."),
    ThesisExternalVariable("gt_makanan_sehat", "Ketertarikan makanan sehat", "numeric", "indeks", True,
                           "seasonal_mean", "Google Trends 1–100, kolom AR."),
    ThesisExternalVariable("gt_yogurt", "Ketertarikan yogurt", "numeric", "indeks", True, "seasonal_mean",
                           "Google Trends 1–100, kolom AS."),
    ThesisExternalVariable("gt_probiotik", "Ketertarikan probiotik", "numeric", "indeks", True, "seasonal_mean",
                           "Google Trends 1–100, kolom AT."),
    ThesisExternalVariable("inflasi", "Inflasi bulanan", "numeric", "fraksi", True, "last_value", "BPS, kolom AU."),
    ThesisExternalVariable("pendapatan", "Pendapatan masyarakat", "numeric", "Rp", True, "zero_fill",
                           "Ekonomi, kolom AV. Hanya Feb & Agu berisi; bulan lain = 0 (data tidak tersedia)."),
)
THESIS_ACTIVE_EXOG: tuple[str, ...] = tuple(v.code for v in THESIS_EXTERNAL_VARIABLES if v.is_active)

# Realisasi per bulan, Jan 2024 – Des 2026 (36 nilai, 6 per baris). None = sel kosong / NA.
_EXOG_RAW: dict[str, tuple[str | None, ...]] = {
    "harga_efektif": (
        "9900", "9900", "9900", "9900", "9900", "8200",
        "9900", "10000", "7900", "10000", "10000", "10000",
        "10000", "10000", "10000", "10000", "10000", "7500",
        "7500", "7500", "10000", "10000", "10000", "10000",
        "10000", "10000", "7211", "8250", "7900", "7900",
        "10000", "10000", "10000", "6800", None, None,
    ),
    "harga_normal": (
        "9900", "9900", "9900", "9900", "9900", "9900",
        "9900", "10000", "10000", "10000", "10000", "10000",
        "10000", "10000", "10000", "10000", "10000", "10000",
        "10000", "10000", "10000", "10000", "10000", "10000",
        "10000", "10000", "10000", "10000", "10000", "10000",
        "10000", "10000", "10000", "10000", None, None,
    ),
    "harga_kompetitor": (
        "7900", "8000", "7500", "8100", "8500", "6900",
        "6500", "7900", "7000", "8500", "6900", "6900",
        "6900", "6900", "6900", "6450", "7900", "7290",
        "7900", "7500", "7500", "8000", "6900", "6900",
        "6900", "6900", "6900", "5000", "7900", "6900",
        "6400", "6290", "6627", "7100", None, None,
    ),
    "suhu": (
        "27.2", "27.3", "27.4", "27.7", "27.7", "27",
        "26.4", "26.8", "27.4", "27.7", "27.5", "27",
        "26.62", "26.8", "27", "27", "27.3", "26.9",
        "26.7", "26.5", "26.91", "27.29", "27.15", "26.86",
        "26.7", "26.7", "27.1", "27.5", "27.5", "27.3",
        "27", "27.22", "27.58", "28.12", None, None,
    ),
    "musim_hujan": (
        "1", "1", "1", "0", "0", "0",
        "0", "0", "0", "0", "1", "1",
        "1", "1", "0", "0", "0", "0",
        "0", "0", "1", "1", "1", "1",
        "1", "1", "0", "0", "0", "0",
        "0", "0", "0", "0", None, None,
    ),
    "musim_kemarau": (
        "0", "0", "0", "0", "0", "1",
        "1", "1", "0", "0", "0", "0",
        "0", "0", "0", "0", "1", "1",
        "1", "0", "0", "0", "0", "0",
        "0", "0", "0", "0", "1", "1",
        "1", "1", "0", "0", None, None,
    ),
    "curah_hujan": (
        "2", "2", "2", "3", "3.5", "2",
        "2", "2", "2", "2", "3", "3",
        "3", "2", "3", "2", "2", "2",
        "2", "2", "2", "2", "2", "3",
        "2", "2", "2", "2", "2", "1.5",
        "1.5", "1.5", "1.5", "2.5", None, None,
    ),
    "promo": (
        "0", "0", "0", "0", "0", "1",
        "0", "0", "1", "0", "0", "0",
        "0", "0", "0", "0", "0", "1",
        "1", "1", "0", "0", "0", "0",
        "0", "0", "1", "1", "1", "1",
        "0", "0", "0", "1", None, None,
    ),
    "hari_promo": (
        "0", "0", "0", "0", "0", None,
        "0", "0", "14", "0", "0", "0",
        "0", "0", "0", "0", "0", "14",
        "8", "6", "0", "0", "0", "0",
        "0", "0", "6", "24", "4", "10",
        "0", "0", "0", None, None, None,
    ),
    "diskon_produk": (
        "0", "0", "0", "0", "0", "0.1717",
        "0", "0", "0.21", "0", "0", "0",
        "0", "0", "0", "0", "0", "0.25",
        "0.25", "0.25", "0", "0", "0", "0",
        "0", "0", "0.2789", "0.175", "0.21", "0.21",
        "0", "0", "0", "0.32", None, None,
    ),
    "hari_promo_kompetitor": (
        "0", "0", "0", "0", "0", "0",
        "0", "0", "14", "0", "0", "0",
        "0", "0", "0", "0", "6", "2",
        "2", "0", "5", "2", "0", "3",
        "6", "2", "0", "14", "0", "0",
        "0", "4", "0", "0", "0", "0",
    ),
    "diskon_kompetitor": (
        "0", "0", "0", "0", "0", "0",
        "0", "0", "0.2391", "0", "0", "0",
        "0", "0", "0", "0", "0", "0.15",
        "0.15", "0", "0", "0", "0", "0",
        "0.5037", "0.4952", "0", "0.4118", "0", "0.1967",
        "0.2258", "0.1967", "0.2474", "0.1852", "0", "0",
    ),
    "hari_libur_sekolah": (
        "7", "0", "3", "13", "0", "0",
        "13", "0", "0", "0", "0", "9",
        "4", "1", "10", "7", "0", "1",
        "12", "0", "0", "0", "0", "3",
        "10", "4", "15", "0", "0", "2",
        "10", "0", "0", "0", None, None,
    ),
    "hari_prj": (
        "0", "0", "0", "0", "0", "19",
        "14", "0", "0", "0", "0", "0",
        "0", "0", "0", "0", "0", "12",
        "13", "0", "0", "0", "0", "0",
        "0", "0", "0", "0", "0", "20",
        "12", "0", "0", "0", "0", "0",
    ),
    "idul_fitri": (
        "0", "0", "0", "1", "0", "0",
        "0", "0", "0", "0", "0", "0",
        "0", "0", "1", "1", "0", "0",
        "0", "0", "0", "0", "0", "0",
        "0", "0", "1", "0", "0", "0",
        "0", "0", "0", "0", "0", "0",
    ),
    "natal": (
        "0", "0", "0", "0", "0", "0",
        "0", "0", "0", "0", "0", "1",
        "0", "0", "0", "0", "0", "0",
        "0", "0", "0", "0", "0", "1",
        "0", "0", "0", "0", "0", "0",
        "0", "0", "0", "0", "0", "1",
    ),
    "tahun_baru": (
        "1", "0", "0", "0", "0", "0",
        "0", "0", "0", "0", "0", "0",
        "1", "0", "0", "0", "0", "0",
        "0", "0", "0", "0", "0", "0",
        "1", "0", "0", "0", "0", "0",
        "0", "0", "0", "0", "0", "0",
    ),
    "tbi": (
        "0", None, None, None, None, None,
        None, None, None, None, None, None,
        "0.016", None, None, None, None, None,
        None, None, None, None, None, None,
        "0.0385", None, None, None, None, None,
        None, None, None, None, None, None,
    ),
    "permintaan": (
        "1665720", "1336800", "1549176", "1240152", "1195632", "3264576",
        "1968528", "2099376", "2590176", "1407936", "2553072", "1804152",
        "1220052", "598296", "1414296", "1096008", "1357776", "235536",
        "2483880", "2471472", "1665120", "643320", "741408", "828984",
        "1413120", "380160", "532680", "260544", "1282824", "588480",
        "2091408", "1382856", "674376", "589536", None, None,
    ),
    "perubahan_permintaan": (
        None, "-0.2191", "0.1472", "-0.2216", "-0.0366", "0.9277",
        "-0.4953", "0.0643", "0.2093", "-0.5914", "0.5782", "-0.3438",
        "-0.3863", "-0.6839", "0.8109", "-0.2536", "0.2134", "-1.4087",
        "1.6535", "-0.005", "-0.3899", "-0.8853", "0.1417", "0.1115",
        "0.5211", "-1.152", "0.3342", "-0.6862", "1.3247", "-0.7421",
        "1.1216", "-0.4079", "-0.6888", "-0.1342", None, None,
    ),
    "ep": (
        None, None, None, None, None, "-4.9388",
        "-2.6369", "6.401", "-0.8921", "-2.5205", None, None,
        None, None, None, None, None, "4.9304",
        None, None, "-1.3645", None, None, None,
        None, None, "-1.0311", "-5.1052", "-30.5636", None,
        "4.7803", None, None, "0.3524", None, None,
    ),
    "gt_makanan_sehat": (
        "35.39", "31.34", "28.03", "22.23", "33.81", "25.57",
        "26.61", "35.35", "38.7", "42.19", "46.03", "29.97",
        "35.26", "38.71", "24.1", "28.97", "37.58", "28.5",
        "26.77", "31", "37.37", "40.48", "40.43", "25.94",
        "27.87", "27.25", "20.58", "29.63", "30.97", "25.1",
        "23.52", "27.13", "35.03", "30.87", None, None,
    ),
    "gt_yogurt": (
        "56.58", "59.38", "48.84", "40.33", "46.32", "43.57",
        "44.29", "49.61", "48.1", "49.9", "48.27", "45.87",
        "51.39", "58.68", "48.58", "53.7", "56.06", "51.7",
        "52.87", "53.74", "52.7", "56.52", "56.97", "50.42",
        "61.13", "88", "63.81", "72.37", "70.19", "63.07",
        "67.42", "77.61", "84.4", "69.13", None, None,
    ),
    "gt_probiotik": (
        "13.97", "14.03", "14.48", "12.77", "15.35", "14.1",
        "14.77", "13.45", "13.83", "14.84", "16.33", "18.68",
        "18.48", "20.64", "21.84", "22.23", "27.06", "28.63",
        "24.68", "22.58", "21.9", "25.87", "26.93", "24.81",
        "25.81", "23.75", "20.65", "22.93", "22.13", "18.9",
        "19.1", "18.19", "19.03", "19.1", None, None,
    ),
    "inflasi": (
        "0.0004", "0.0037", "0.0052", "0.0025", "-0.0003", "-0.0008",
        "-0.0018", "-0.0003", "-0.0012", "0.0008", "0.003", "0.0044",
        "-0.0076", "-0.0048", "0.0165", "0.0117", "-0.0037", "0.0019",
        "0.003", "-0.0008", "0.0021", "0.0028", "0.0017", "0.0064",
        "-0.0015", "0.0068", "0.0041", "0.0013", "0.0028", "0.0044",
        "-0.0014", "0.0021", "0.003", "0.0022", None, None,
    ),
    "pendapatan": (
        None, "3040000", None, None, None, None,
        None, "3270000", None, None, None, None,
        None, "3094818", None, None, None, None,
        None, "3330000", None, None, None, None,
        None, "3287675", None, None, None, None,
        None, "3420000", None, None, None, None,
    ),
}


def _month(i: int) -> date:
    return date(THESIS_EXOG_START.year + i // 12, i % 12 + 1, 1)


def _realisasi(code: str) -> dict[date, Decimal]:
    return {_month(i): Decimal(v) for i, v in enumerate(_EXOG_RAW[code]) if v is not None}


def _price_change(harga: dict[date, Decimal]) -> dict[date, Decimal]:
    """Rumus kolom AO (perubahan titik tengah); bulan pertama / harga kosong → 0."""
    out = {}
    for i in range(36):
        cur, prev = harga.get(_month(i)), harga.get(_month(i - 1)) if i else None
        if cur is None:
            continue
        change = (cur - prev) / ((cur + prev) / 2) if prev is not None else Decimal(0)
        out[_month(i)] = change.quantize(Decimal("0.0001")) if change else Decimal(0)
    return out


def thesis_exog_series(code: str, scenario: str = "asumsi") -> dict[date, Decimal]:
    """Nilai variabel per bulan. Histori 2024–2025 selalu realisasi Excel.

    - `realisasi`: 2026 = nilai Excel apa adanya (*perfect foresight*, skenario pembanding)
    - `asumsi` (default): 2026 Jan–Des diisi sesuai `horizon_rule` variabel — hanya variabel
      *known in advance* yang memakai realisasi 2026 (CR v3.4 §5 no. 6–7)
    """
    if scenario not in THESIS_EXOG_SCENARIOS:
        raise ValueError(f"Skenario exog tidak dikenal: {scenario!r} (pilih {', '.join(THESIS_EXOG_SCENARIOS)})")
    rule = next(v.horizon_rule for v in THESIS_EXTERNAL_VARIABLES if v.code == code)
    if rule == "zero_fill":
        return {_month(i): Decimal(v) if v is not None else Decimal(0) for i, v in enumerate(_EXOG_RAW[code])}
    if rule == "price_change":
        return _price_change(thesis_exog_series("harga_efektif", scenario))
    real = _realisasi(code)
    if scenario == "realisasi":
        return real
    out = {p: v for p, v in real.items() if p.year < 2026}
    last = out.get(date(2025, 12, 1))
    for month in range(1, 13):
        target, prev, prev2 = date(2026, month, 1), date(2025, month, 1), date(2024, month, 1)
        if rule == "known":
            value = real.get(target, out.get(prev))
        elif rule == "seasonal_mean":
            pair = [out[p] for p in (prev2, prev) if p in out]
            value = sum(pair) / len(pair) if pair else None
        elif rule == "same_month":
            value = out.get(prev)
        elif rule == "last_value":
            value = last
        else:
            value = None
        if value is not None:
            out[target] = value
    return out
