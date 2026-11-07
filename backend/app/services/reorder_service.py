"""
ReorderService — safety stock & reorder point (Fase 5), docs/ARCHITECTURE.md §4.

`compute_reorder` adalah FUNGSI MURNI (mudah diverifikasi manual, AGENTS.md §3):

  SS  = manual_safety_stock jika diisi, else Z · σ_harian · sqrt(lead_time)
  B   = buffer stock = max(0, faktor waste − 1) × kebutuhan periode (Fase 11.1)
  ROP = μ_harian · lead_time + SS (+ B)      ← `compute_rop`, rumus dari master data
  S   = order-up-to = ROP + μ_harian · lead_time
  current ≤ ROP      → urgent   (qty = `compute_order_qty`, kebijakan dari master data)
  ROP < current ≤ S  → safe     (qty = 0)
  current > S        → overstock (qty = 0)

Fase 11.9 (v3.3) — SUMBER TUNGGAL titik pesan & qty pesan. Tabel Reorder dan Proyeksi
Stok (`stock_projection_service`) sama-sama memakai `compute_rop` / `compute_order_qty`
(via `OrderPolicy`), dikonfigurasi lewat Pengaturan Forecast:
  rop_formula       standard (μ·L + SS) | with_buffer (μ·L + SS + B, default)
  order_qty_policy  order_up_to (max(MOQ, ceil(S − current)), default)
                    | eoq (n × EOQ, n ≥ 1 terkecil s.d. current + n·EOQ ≥ ROP;
                           EOQ ≤ 0 → fallback order_up_to)
Default = perilaku Reorder sebelum v3.3. Rumus final thesis menunggu docx (TODO-v3 ⛔).

Orkestrasi (`ReorderService`) menghitung μ/σ dari deret kebutuhan material
hasil breakdown BOM atas forecast produk, dan mengambil lead_time/MOQ/manual SS
dari master data material.

Fase 11.0 (REVISI_V2 §3.7): deret forecast berskala PERIODE (bulanan di data
thesis), sedangkan lead time dalam HARI. μ/σ dikonversi ke harian dulu:
  μ_d = μ_p / days_in_period,  σ_d = σ_p / √days_in_period  (asumsi demand
  harian independen). Z = Φ⁻¹(service level / 100); service level dari master data
  Pengaturan Forecast (Fase 11.4, default 95).
"""
import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import NormalDist, median

import numpy as np

from app.config import get_settings
from app.models.reorder_recommendation import ReorderRecommendation
from app.services.bom_service import BomLine, breakdown_requirements_series, compute_buffer_qty
from app.services.cost_template_service import load_cost_params
from app.utils.exceptions import ForbiddenRoleError, ForecastRunNotFoundError


def _dec(value) -> Decimal:
    return Decimal(str(round(float(value), 4)))


def period_to_daily(mu: float, sigma: float, days: float) -> tuple[float, float]:
    """μ/σ per periode → per hari: μ/days, σ/√days (demand harian independen)."""
    days = float(days)
    if days <= 0:
        raise ValueError("days harus > 0")
    return float(mu) / days, float(sigma) / math.sqrt(days)


def days_in_period(dates) -> float:
    """Jumlah hari per periode = median selisih tanggal; < 2 tanggal valid → 1 (harian)."""
    parsed = sorted(date.fromisoformat(str(d)[:10]) for d in dates if d)
    if len(parsed) < 2:
        return 1
    return float(median((b - a).days for a, b in zip(parsed, parsed[1:])))


def z_from_service_level(pct: float) -> float:
    """Faktor Z dari target service level (%), mis. 95 → 1.6449, 99 → 2.3263."""
    pct = float(pct)
    if not 50 < pct < 100:
        raise ValueError("service level harus di antara 50 dan 100 (%)")
    return NormalDist().inv_cdf(pct / 100)


@dataclass
class ReorderComputation:
    safety_stock: Decimal
    reorder_point: Decimal
    recommended_order_qty: Decimal
    status: str
    order_up_to_level: Decimal | None = None


@dataclass
class EOQResult:
    n: int  # jumlah pemesanan optimal pada horizon
    eoq_qty: Decimal  # ukuran pesanan ekonomis (belum dibulatkan ke MOQ)
    total_cost: Decimal  # TC = n·S + Σ(Iₜ·H)


def _split_cycles(n_periods: int, n_orders: int) -> list[tuple[int, int]]:
    """Bagi `n_periods` jadi `n_orders` siklus kontigu sebanyak-mungkin merata."""
    base, extra = divmod(n_periods, n_orders)
    cycles, start = [], 0
    for i in range(n_orders):
        length = base + (1 if i < extra else 0)
        if length == 0:
            continue
        cycles.append((start, start + length))
        start += length
    return cycles


def compute_eoq(demands: list[float], ordering_cost: float, holding_cost: float) -> EOQResult:
    """
    EOQ dinamis (Bab III thesis): TC = n·S + Σ(Iₜ·H), Iₜ = persediaan akhir periode t.
    Simulasikan tiap kandidat jumlah pemesanan n (1..T): tiap order menutup demand
    siklusnya, hitung total biaya, pilih n dengan TC minimum. Fungsi murni,
    diverifikasi manual di test (AGENTS.md §3).
    """
    demands = [float(d) for d in demands]
    horizon = len(demands)
    total = sum(demands)
    if horizon == 0 or total <= 0:
        return EOQResult(n=1, eoq_qty=_dec(0), total_cost=_dec(ordering_cost))

    best_n, best_cost = 1, None
    for n in range(1, horizon + 1):
        inventory, holding = 0.0, 0.0
        for start, end in _split_cycles(horizon, n):
            inventory += sum(demands[start:end])  # order menutup demand siklus ini
            for t in range(start, end):
                inventory -= demands[t]
                holding += inventory * holding_cost  # biaya simpan persediaan akhir periode
        total_cost = n * ordering_cost + holding
        if best_cost is None or total_cost < best_cost:
            best_n, best_cost = n, total_cost

    return EOQResult(n=best_n, eoq_qty=_dec(total / best_n), total_cost=_dec(best_cost))


def round_to_moq(qty: float, moq: float) -> Decimal:
    """Bulatkan qty ke kelipatan MOQ ke atas (MOQ sebagai batas bawah)."""
    qty, moq = float(qty), float(moq)
    if moq <= 0:
        return _dec(qty)
    return _dec(math.ceil(round(qty / moq, 6)) * moq)


# ── EOQ klasik thesis (Fase 11.4, REVISI_V2 §3.5) ──

DEFAULT_SERVICE_LEVEL_PCT = 95.0
DEFAULT_EOQ_METHOD = "classic"


def periods_per_year(days: float) -> float:
    """Periode per tahun: bulanan (28–31 hari) → 12, selain itu 365 ÷ hari."""
    days = float(days)
    return 12.0 if 28 <= days <= 31 else 365.0 / days


def annual_demand(series, days: float) -> float:
    """A = rata-rata kebutuhan per periode horizon × periode per tahun (Σ ÷ n × 12)."""
    values = [float(v) for v in series]
    if not values:
        return 0.0
    return sum(values) / len(values) * periods_per_year(days)


@dataclass
class ClassicEOQ:
    eoq_qty: float
    n_orders: float
    ordering_cost: float  # (A/Q)·S per tahun
    holding_cost: float  # (Q/2)·i·C per tahun
    total_cost: float


def compute_eoq_classic(annual_demand: float, ordering_cost: float, holding_rate, unit_price) -> ClassicEOQ:
    """EOQ = √(2AS / iC); TC = (A/Q)S + (Q/2)iC. `holding_rate` pecahan (0,2 = 20%).
    i atau C kosong/≤ 0 → ValueError (EOQ klasik tak terdefinisi)."""
    if holding_rate is None or unit_price is None or float(holding_rate) <= 0 or float(unit_price) <= 0:
        raise ValueError("EOQ klasik butuh i (%) dan harga material > 0.")
    a, s, ic = float(annual_demand), float(ordering_cost), float(holding_rate) * float(unit_price)
    if a <= 0:
        return ClassicEOQ(0.0, 0.0, 0.0, 0.0, 0.0)
    q = math.sqrt(2 * a * s / ic)
    if q == 0:  # S = 0 → tak ada biaya pesan, EOQ teoritis 0
        return ClassicEOQ(0.0, 0.0, 0.0, 0.0, 0.0)
    ordering, holding = a / q * s, q / 2 * ic
    return ClassicEOQ(q, a / q, ordering, holding, ordering + holding)


def suggest_holding_rate(annual_holding_cost: float, avg_inventory_value: float) -> float | None:
    """Keputusan #5: i (%) = Σ biaya simpan tahunan ÷ rata-rata nilai persediaan (Rp) × 100."""
    if float(avg_inventory_value) <= 0:
        return None
    return float(annual_holding_cost) / float(avg_inventory_value) * 100


@dataclass
class EoqChoice:
    method: str  # classic | dynamic (yang benar-benar dipakai)
    status: str  # COMPLETED | MISSING_UNIT_PRICE | MISSING_HOLDING_RATE
    eoq_qty: float
    ordering_cost: float
    holding_cost: float
    total_cost: float
    annual_demand: float


def choose_eoq(series, days: float, method: str, unit_price, holding_rate_pct, cost) -> EoqChoice:
    """Pilih EOQ per material (dipakai reorder usulan & baseline supaya simetris).

    `classic` hanya bila harga & i (%) ada; selain itu jatuh ke EOQ dinamis dengan
    status per item (bukan menggagalkan run, REVISI_V2 §3.5).
    """
    a = annual_demand(series, days)
    status = "COMPLETED"
    if method == "classic":
        if unit_price is None or float(unit_price) <= 0:
            status = "MISSING_UNIT_PRICE"
        elif holding_rate_pct is None or float(holding_rate_pct) <= 0:
            status = "MISSING_HOLDING_RATE"
        else:
            r = compute_eoq_classic(a, cost.ordering_cost, float(holding_rate_pct) / 100, unit_price)
            return EoqChoice("classic", status, r.eoq_qty, r.ordering_cost, r.holding_cost, r.total_cost, a)
    dyn = compute_eoq(series, cost.ordering_cost, cost.holding_cost)
    ordering = dyn.n * cost.ordering_cost
    holding = float(dyn.total_cost) - ordering
    return EoqChoice("dynamic", status, float(dyn.eoq_qty), ordering, holding, float(dyn.total_cost), a)


def compute_tic(ordering_cost_total: float, holding_cost_total: float) -> Decimal:
    """Total Inventory Cost = Ordering Cost + Holding Cost."""
    return _dec(float(ordering_cost_total) + float(holding_cost_total))


def compute_savings_pct(tic_actual: float, tic_proposed: float) -> Decimal:
    """% penghematan = (TIC aktual − TIC usulan) / TIC aktual × 100."""
    tic_actual = float(tic_actual)
    if tic_actual == 0:
        return _dec(0)
    return _dec((tic_actual - float(tic_proposed)) / tic_actual * 100)


ROP_FORMULAS = ("standard", "with_buffer")
ORDER_QTY_POLICIES = ("eoq", "order_up_to")
DEFAULT_ROP_FORMULA = "with_buffer"
DEFAULT_ORDER_QTY_POLICY = "order_up_to"


def compute_rop(mu_daily: float, lead_time_days: float, ss: float, buffer: float, formula: str) -> float:
    """Titik pesan. standard = μ·L + SS; with_buffer = μ·L + SS + B."""
    if formula not in ROP_FORMULAS:
        raise ValueError(f"rop_formula tidak dikenal: {formula}")
    rop = float(mu_daily) * float(lead_time_days) + float(ss)
    return rop + float(buffer) if formula == "with_buffer" else rop


def compute_order_qty(
    policy: str, current: float, rop: float, order_up_to: float, eoq_qty: float, moq: float
) -> float:
    """Qty pesan saat stok `current` (0 bila current > ROP). Dipakai Reorder & Proyeksi Stok."""
    if policy not in ORDER_QTY_POLICIES:
        raise ValueError(f"order_qty_policy tidak dikenal: {policy}")
    current, rop, eoq = float(current), float(rop), float(eoq_qty or 0)
    if current > rop:
        return 0.0
    if policy == "eoq" and eoq > 0:
        # round sebelum ceil supaya galat float tidak menambah satu kelipatan
        n = max(1, math.ceil(round((rop - current) / eoq, 9)))
        return float(n * eoq)
    need = round(float(order_up_to) - current, 6)
    return max(float(moq or 0), float(math.ceil(need)))


@dataclass(frozen=True)
class OrderPolicy:
    """Kebijakan pesan satu material — dibangun sekali, dipakai Reorder & Proyeksi Stok."""

    policy: str
    reorder_point: float
    order_up_to: float
    eoq_qty: float
    moq: float

    def order_qty(self, current: float) -> float:
        return compute_order_qty(self.policy, current, self.reorder_point, self.order_up_to, self.eoq_qty, self.moq)


def order_policy_from_rec(rec) -> OrderPolicy:
    """OrderPolicy dari baris `reorder_recommendations`. Baris sebelum v3.3 (kolom NULL) →
    order_up_to, S = 2·ROP − SS − B (rumus lama with_buffer), MOQ 0."""
    rop = float(rec.reorder_point or 0)
    s_level = getattr(rec, "order_up_to_level", None)
    if s_level is None:
        ss, buffer = float(rec.safety_stock or 0), float(getattr(rec, "buffer_stock", 0) or 0)
        s_level = 2 * rop - ss - buffer
    return OrderPolicy(
        policy=getattr(rec, "order_qty_policy_used", None) or DEFAULT_ORDER_QTY_POLICY,
        reorder_point=rop,
        order_up_to=float(s_level),
        eoq_qty=float(rec.eoq_qty or 0),
        moq=float(getattr(rec, "moq_used", None) or 0),
    )


def compute_reorder(
    mu: float,
    sigma: float,
    lead_time_days: float,
    moq: float,
    z: float,
    manual_ss: float | None,
    current_stock: float,
    buffer: float = 0.0,
    formula: str = DEFAULT_ROP_FORMULA,
    policy: str = DEFAULT_ORDER_QTY_POLICY,
    eoq_qty: float = 0.0,
) -> ReorderComputation:
    mu, sigma = float(mu), float(sigma)
    lt, moq, current = float(lead_time_days), float(moq), float(current_stock)

    ss = float(manual_ss) if manual_ss is not None else z * sigma * math.sqrt(lt)
    demand_over_lt = mu * lt
    # Buffer stock (antisipasi waste, Fase 11.1) disimpan di atas safety stock (with_buffer).
    rop = compute_rop(mu, lt, ss, buffer, formula)
    order_up_to = rop + demand_over_lt

    if current <= rop:
        status = "urgent"
    elif current <= order_up_to:
        status = "safe"
    else:
        status = "overstock"
    qty = compute_order_qty(policy, current, rop, order_up_to, eoq_qty, moq)

    return ReorderComputation(_dec(ss), _dec(rop), _dec(qty), status, _dec(order_up_to))



class ReorderService:
    """
    v3.0: reorder dihitung PER MATERIAL dari hasil breakdown BOM atas forecast
    produk jadi (bukan lagi dari consumption_history material). Deret kebutuhan
    material per periode = Σ_produk (forecast_produk[t] × qty_per_unit) → μ/σ untuk
    safety stock, dan sebagai demand EOQ.
    """

    def __init__(
        self,
        reorder_repo,
        forecast_repo,
        boms,
        materials,
        cost_templates=None,
        usage=None,
        settings=None,
        stock=None,
    ):
        self._repo = reorder_repo
        self._forecast = forecast_repo
        self._boms = boms
        self._materials = materials
        # Fase 10: S & H dari template biaya aktif; None/tanpa template aktif → env.
        self._cost_templates = cost_templates
        # Fase 11.1: MaterialUsageService → faktor waste per material untuk buffer stock.
        self._usage = usage
        # Fase 11.4: ForecastSettingsService → service level & metode EOQ (master data, bukan env).
        self._settings = settings
        # Fase 11.5: StockSnapshotService → stok terakhir dari ERP; `current_stock` request = fallback.
        self._stock = stock

    async def generate_for_run(self, user_id: str, run_id: str, current_stock: dict | None = None):
        run = await self._require_run(user_id, run_id)
        current_stock = current_stock or {}
        settings = get_settings()
        service_level = await self._settings.service_level_pct() if self._settings else DEFAULT_SERVICE_LEVEL_PCT
        eoq_method = await self._settings.eoq_method() if self._settings else DEFAULT_EOQ_METHOD
        rop_formula = await self._settings.rop_formula() if self._settings else DEFAULT_ROP_FORMULA
        qty_policy = await self._settings.order_qty_policy() if self._settings else DEFAULT_ORDER_QTY_POLICY
        z = z_from_service_level(service_level)
        cost = await load_cost_params(self._cost_templates, settings)

        # Deret forecast per produk (hanya yang COMPLETED & punya data).
        product_series: dict[str, list[float]] = {}
        forecast_dates: list = []
        for result in await self._forecast.list_results(run_id):
            if result.status != "COMPLETED":
                continue
            fdata = getattr(result, "forecast_data", None) or []
            if fdata:
                product_series[str(result.product_id)] = [float(p.get("value", 0)) for p in fdata]
                if not forecast_dates:
                    forecast_dates = [p.get("date") for p in fdata]
        # Satu run = satu granularitas periode; semua produk berbagi tanggal horizon.
        period_days = days_in_period(forecast_dates)

        # Breakdown BOM → deret kebutuhan per material.
        bom_lines: list[BomLine] = []
        for pid in product_series:
            for bom in await self._boms.list(pid):
                bom_lines.append(BomLine(str(bom.product_id), str(bom.material_id), float(bom.qty_per_unit)))
        material_series = breakdown_requirements_series(product_series, bom_lines)

        waste = await self._usage.waste_factors(list(material_series)) if self._usage else {}
        snapshots = await self._stock.latest_stock() if self._stock else {}

        recommendations = []
        for material_id, series in material_series.items():
            material = await self._materials.get_by_id(material_id)
            if material is None:
                continue
            arr = np.asarray(series, dtype=float)
            mu_p = float(np.mean(arr)) if len(arr) else 0.0
            sigma_p = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
            mu, sigma = period_to_daily(mu_p, sigma_p, period_days)
            if str(material_id) in snapshots:
                stock_qty, stock_source = snapshots[str(material_id)][1], "snapshot"
            else:
                stock_qty, stock_source = float(current_stock.get(material_id, 0)), "request"
            waste_factor = waste.get(str(material_id))
            buffer = compute_buffer_qty(waste_factor, mu_p)
            # EOQ dihitung DULU — kebijakan `eoq` memakainya sebagai qty pesan (Fase 11.9).
            price = getattr(material, "unit_price", None)
            eoq = choose_eoq(series, period_days, eoq_method, price, cost.holding_rate_pct, cost)
            raw_qty = math.ceil(round(eoq.eoq_qty, 6)) if eoq.method == "classic" else eoq.eoq_qty
            eoq_qty = round_to_moq(raw_qty, float(material.moq))
            ordering_total, holding_total = eoq.ordering_cost, eoq.holding_cost

            comp = compute_reorder(
                mu=mu,
                sigma=sigma,
                lead_time_days=material.lead_time_days,
                moq=float(material.moq),
                z=z,
                manual_ss=float(material.manual_safety_stock)
                if material.manual_safety_stock is not None
                else None,
                current_stock=stock_qty,
                buffer=buffer,
                formula=rop_formula,
                policy=qty_policy,
                eoq_qty=float(eoq_qty),
            )

            recommendations.append(
                ReorderRecommendation(
                    run_id=run.id,
                    material_id=material.id,
                    safety_stock=comp.safety_stock,
                    buffer_stock=_dec(buffer),
                    waste_factor=_dec(waste_factor) if waste_factor is not None else None,
                    reorder_point=comp.reorder_point,
                    recommended_order_qty=comp.recommended_order_qty,
                    status=comp.status,
                    eoq_qty=eoq_qty,
                    ordering_cost=_dec(ordering_total),
                    holding_cost=_dec(holding_total),
                    total_inventory_cost=compute_tic(ordering_total, holding_total),
                    eoq_method=eoq.method,
                    item_status=eoq.status,
                    annual_demand=_dec(eoq.annual_demand),
                    unit_price_used=price,
                    holding_rate_used=cost.holding_rate_pct if eoq.method == "classic" else None,
                    current_stock_used=_dec(stock_qty),
                    stock_source=stock_source,
                    rop_formula_used=rop_formula,
                    order_qty_policy_used=qty_policy,
                    order_up_to_level=comp.order_up_to_level,
                    moq_used=_dec(material.moq),
                )
            )

        await self._repo.replace_for_run(str(run_id), recommendations)
        return recommendations

    async def list_for_run(self, user_id: str, run_id: str, status: str | None = None):
        await self._require_run(user_id, run_id)
        recs = await self._repo.list_by_run(run_id)
        if status:
            recs = [r for r in recs if r.status == status]
        return recs

    async def _require_run(self, user_id: str, run_id: str):
        run = await self._forecast.get_run(run_id)
        if run is None:
            raise ForecastRunNotFoundError("Forecast run tidak ditemukan.")
        if str(run.user_id) != str(user_id):
            raise ForbiddenRoleError("Anda tidak berhak mengakses run ini.")
        return run
