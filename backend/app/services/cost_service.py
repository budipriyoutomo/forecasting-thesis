"""
CostService (v3.0 Fase 7) — ringkasan total biaya persediaan & % penghematan,
docs/ARCHITECTURE.md §6.8 + RECONCILIATION §Fase 7.

Rumus TIC/EOQ/savings TIDAK diduplikasi: `compute_eoq` & `compute_savings_pct`
di-reuse dari `reorder_service.py` (satu sumber kebenaran rumus). Service ini
hanya mengorkestrasi:
  - TIC usulan (ForecastIQ) = Σ total_inventory_cost dari reorder_recommendations tersimpan.
  - TIC baseline (existing) = seri planning perusahaan → BOM breakdown → EOQ per material
    (simetris dgn jalur forecast di ReorderService).
  - savings_pct = (TIC_baseline − TIC_usulan) / TIC_baseline × 100.

Fase 10 (2 Oktober 2026): S & H baseline dari template biaya aktif (fallback env /
argumen konstruktor), plus `purchase_cost` = Σ kebutuhan material forecast × harga
beli — INFORMASI saja, tidak masuk TIC (RECONCILIATION §"Konsolidasi Master Data").

28 Nov 2026 (keputusan user) — basis PROYEKSI STOK untuk evaluasi inventory (cost_basis
"projection", bila run sudah punya proyeksi stok & repo proyeksi di-inject):
  biaya pesan  = Σ qty pembelian (order_qty proyeksi) × harga material per unit
  biaya simpan = Σ stok akhir per periode (dus) × tarif H × bulan/periode
                 tarif H = total biaya gudang per bulan (overhead + perawatan + depresiasi aset)
                 ÷ kapasitas gudang (dus) = "Saran H" ringkasan template biaya aktif.
Dihitung per skenario (proposed = usulan, baseline = existing). EOQ/reorder TIDAK berubah —
tetap memakai S/H/i manual template. Tanpa proyeksi → basis lama "eoq" (di atas).
"""
from dataclasses import dataclass, field
from decimal import Decimal
from types import SimpleNamespace

from app.config import get_settings
from app.services.bom_service import BomLine, breakdown_requirements_series
from app.services.cost_template_service import load_cost_params, summarize_template
from app.services.reorder_service import (
    DEFAULT_EOQ_METHOD,
    choose_eoq,
    compute_savings_pct,
    days_in_period,
    eoq_requirement_series,
)
from app.services.warehouse_service import capacity_dus_of, is_dus_like, material_group_key
from app.utils.exceptions import ForecastRunNotFoundError

_MONTH_DAYS = 365 / 12


def _dec(value) -> Decimal:
    return Decimal(str(round(float(value), 4)))


def months_per_period(days: float) -> float:
    """Bulan per periode proyeksi: bulanan (28–31 hari) → 1, selain itu hari ÷ (365/12)."""
    days = float(days)
    return 1.0 if 28 <= days <= 31 else days / _MONTH_DAYS


def ordering_cost_from_orders(order_qtys, unit_price) -> float | None:
    """Biaya pesan = Σ qty pembelian × harga material per unit; harga kosong/≤ 0 → None."""
    if unit_price is None or float(unit_price) <= 0:
        return None
    return sum(float(q or 0) for q in order_qtys) * float(unit_price)


def holding_cost_from_stock(ending_qtys, pcs_per_dus, rate_per_dus_month, months: float) -> float | None:
    """Biaya simpan = Σ (stok akhir ÷ pcs per dus) × tarif H (Rp/dus/bulan) × bulan per periode.
    Konversi/tarif tidak tersedia → None."""
    if rate_per_dus_month is None or pcs_per_dus is None or float(pcs_per_dus) <= 0:
        return None
    dus = sum(float(q or 0) for q in ending_qtys) / float(pcs_per_dus)
    return dus * float(rate_per_dus_month) * float(months)


@dataclass
class MaterialCost:
    """Rincian biaya per material (basis proyeksi); None = data tidak cukup (harga/kapasitas)."""

    material_id: str
    ordering_cost: Decimal | None = None
    holding_cost: Decimal | None = None
    baseline_ordering_cost: Decimal | None = None
    baseline_holding_cost: Decimal | None = None


@dataclass
class CostSummary:
    total_ordering_cost: Decimal
    total_holding_cost: Decimal
    total_inventory_cost: Decimal  # usulan ForecastIQ
    baseline_inventory_cost: Decimal  # existing (planning perusahaan)
    savings_pct: Decimal
    # Fase 10 — additive
    purchase_cost: Decimal = Decimal(0)  # informasi, tidak masuk TIC
    n_materials_without_price: int = 0
    cost_source: str = "env"  # "template" | "env" — sumber S & H baseline
    cost_template_name: str | None = None
    eoq_method: str = DEFAULT_EOQ_METHOD  # Fase 11.4 — metode yang diminta master data
    shortage_cost: Decimal | None = None  # Fase 11.7 — dari inventory_metrics material (None = belum dihitung)
    baseline_shortage_cost: Decimal | None = None
    # 23 Nov 2026 — rincian TIC baseline (pesan + simpan) untuk tab Evaluasi usulan inventory
    baseline_ordering_cost: Decimal = Decimal(0)
    baseline_holding_cost: Decimal = Decimal(0)
    # 28 Nov 2026 — basis biaya: "projection" (qty pembelian × harga, stok akhir × tarif H) | "eoq"
    cost_basis: str = "eoq"
    holding_rate_per_dus: Decimal | None = None
    n_materials_without_order_price: int = 0
    n_materials_without_capacity: int = 0
    materials: list = field(default_factory=list)


def _system_stock_levels(rec) -> tuple[float, float]:
    """(SS, B) sistem sebelum adjust kapasitas (Fase 11.17); kolom kosong → nilai berlaku / 0."""
    ss = getattr(rec, "safety_stock_system", None)
    if ss is None:
        ss = getattr(rec, "safety_stock", None)
    buffer = getattr(rec, "buffer_stock_system", None)
    if buffer is None:
        buffer = getattr(rec, "buffer_stock", None)
    return float(ss or 0), float(buffer or 0)


def aggregate_proposed(recs) -> tuple[Decimal, Decimal, Decimal]:
    """Jumlahkan ordering/holding/TIC dari reorder_recommendations tersimpan."""
    ordering = sum(float(r.ordering_cost or 0) for r in recs)
    holding = sum(float(r.holding_cost or 0) for r in recs)
    tic = sum(float(r.total_inventory_cost or 0) for r in recs)
    return _dec(ordering), _dec(holding), _dec(tic)


class CostService:
    def __init__(
        self,
        forecast_repo,
        reorder_repo,
        demand_repo,
        boms,
        products,
        ordering_cost=None,
        holding_cost=None,
        cost_templates=None,
        materials=None,
        settings=None,
        metrics_repo=None,
        projections=None,
        warehouse_configs=None,
    ):
        app_settings = get_settings()
        self._forecast = forecast_repo
        self._reorder = reorder_repo
        self._demand = demand_repo
        self._boms = boms
        self._products = products
        self._cost_templates = cost_templates
        self._materials = materials
        self._settings = settings  # Fase 11.4 — metode EOQ (master data)
        self._metrics = metrics_repo  # Fase 11.7 — shortage cost material
        self._projections = projections  # 28 Nov 2026 — basis proyeksi stok
        self._warehouse = warehouse_configs
        # Fallback bila tak ada template aktif: argumen eksplisit (test) atau env.
        self._fallback = SimpleNamespace(
            DEFAULT_ORDERING_COST=app_settings.DEFAULT_ORDERING_COST if ordering_cost is None else ordering_cost,
            DEFAULT_HOLDING_COST_RATE=app_settings.DEFAULT_HOLDING_COST_RATE if holding_cost is None else holding_cost,
        )

    async def get_cost_summary(self, user_id: str, run_id: str) -> CostSummary:
        await self._require_run(user_id, run_id)
        cost = await load_cost_params(self._cost_templates, self._fallback)

        method = await self._settings.eoq_method() if self._settings else DEFAULT_EOQ_METHOD
        purchase_cost, n_without_price = await self._purchase_cost(run_id)

        projected = await self._projection_costs(run_id)
        if projected is not None:
            return CostSummary(
                **projected,
                savings_pct=compute_savings_pct(
                    float(projected["baseline_inventory_cost"]), float(projected["total_inventory_cost"])
                ),
                purchase_cost=purchase_cost,
                n_materials_without_price=n_without_price,
                cost_source=cost.source,
                cost_template_name=cost.template_name,
                eoq_method=method,
                cost_basis="projection",
                **await self._shortage(run_id),
            )

        recs = await self._reorder.list_by_run(run_id)
        ordering, holding, proposed_tic = aggregate_proposed(recs)
        baseline_ordering, baseline_holding = await self._baseline_costs(run_id, cost, method, recs)
        baseline_tic = _dec(float(baseline_ordering) + float(baseline_holding))
        savings = compute_savings_pct(float(baseline_tic), float(proposed_tic))
        return CostSummary(
            total_ordering_cost=ordering,
            total_holding_cost=holding,
            total_inventory_cost=proposed_tic,
            baseline_inventory_cost=baseline_tic,
            baseline_ordering_cost=baseline_ordering,
            baseline_holding_cost=baseline_holding,
            savings_pct=savings,
            purchase_cost=purchase_cost,
            n_materials_without_price=n_without_price,
            cost_source=cost.source,
            cost_template_name=cost.template_name,
            eoq_method=method,
            **await self._shortage(run_id),
        )

    async def _holding_rate(self) -> Decimal | None:
        """Tarif H (Rp/dus/bulan) = "Saran H" template aktif; tanpa template/kapasitas → None."""
        template = await self._cost_templates.get_active() if self._cost_templates is not None else None
        if template is None:
            return None
        configs = await self._warehouse.list() if self._warehouse is not None else []
        total_dus = sum((Decimal(str(capacity_dus_of(c))) for c in configs), Decimal(0))
        return summarize_template(getattr(template, "items", None) or [], total_dus).suggested_holding_cost

    async def _pcs_per_dus_by_group(self) -> dict:
        """{kunci grup material: pcs per dus | None (unit dus)} dari kapasitas grup material."""
        out = {}
        for c in await self._warehouse.list() if self._warehouse is not None else []:
            if getattr(c, "item_type", None) == "material_group":
                out[material_group_key(c.material_group)] = getattr(c, "pcs_per_dus", None)
        return out

    async def _projection_costs(self, run_id: str) -> dict | None:
        """Biaya pesan & simpan per skenario dari proyeksi stok tersimpan; None bila belum ada."""
        rows = await self._projections.list_by_run(run_id) if self._projections is not None else []
        if not rows:
            return None
        rate = await self._holding_rate()
        months = months_per_period(days_in_period(sorted({str(r.period) for r in rows})))
        pcs_by_group = await self._pcs_per_dus_by_group()

        series: dict[str, dict[str, list]] = {}
        for r in rows:
            series.setdefault(str(r.material_id), {}).setdefault(r.scenario, []).append(r)

        totals = {k: 0.0 for k in ("po", "ph", "bo", "bh")}
        no_price, no_capacity, details = 0, 0, []
        for mid in sorted(series):
            material = await self._materials.get_by_id(mid) if self._materials else None
            price = getattr(material, "unit_price", None)
            unit = getattr(material, "unit", None) or ""
            group = material_group_key(getattr(material, "category", None))
            if group in pcs_by_group:
                pcs = pcs_by_group[group]
                pcs = 1 if pcs is None and is_dus_like(unit) else pcs
            else:
                pcs = None
            no_price += 1 if price is None or float(price) <= 0 else 0
            no_capacity += 1 if pcs is None else 0

            cost = MaterialCost(material_id=mid)
            for scenario, (o_key, h_key), (o_attr, h_attr) in (
                ("proposed", ("po", "ph"), ("ordering_cost", "holding_cost")),
                ("baseline", ("bo", "bh"), ("baseline_ordering_cost", "baseline_holding_cost")),
            ):
                srows = series[mid].get(scenario)
                if not srows:
                    continue
                o = ordering_cost_from_orders([r.order_qty for r in srows], price)
                h = holding_cost_from_stock([r.ending_qty for r in srows], pcs, rate, months)
                totals[o_key] += o or 0.0
                totals[h_key] += h or 0.0
                setattr(cost, o_attr, _dec(o) if o is not None else None)
                setattr(cost, h_attr, _dec(h) if h is not None else None)
            details.append(cost)

        return {
            "total_ordering_cost": _dec(totals["po"]),
            "total_holding_cost": _dec(totals["ph"]),
            "total_inventory_cost": _dec(totals["po"] + totals["ph"]),
            "baseline_ordering_cost": _dec(totals["bo"]),
            "baseline_holding_cost": _dec(totals["bh"]),
            "baseline_inventory_cost": _dec(totals["bo"] + totals["bh"]),
            "holding_rate_per_dus": rate,
            "n_materials_without_order_price": no_price,
            "n_materials_without_capacity": no_capacity,
            "materials": details,
        }

    async def _shortage(self, run_id: str) -> dict:
        rows = [
            r for r in (await self._metrics.list_by_run(run_id) if self._metrics else [])
            if r.target_type == "material" and getattr(r, "shortage_cost", None) is not None
        ]
        if not rows:
            return {}
        total = {s: sum(float(r.shortage_cost) for r in rows if r.scope == s) for s in ("forecastiq", "baseline")}
        return {"shortage_cost": _dec(total["forecastiq"]), "baseline_shortage_cost": _dec(total["baseline"])}

    async def _purchase_cost(self, run_id: str) -> tuple[Decimal, int]:
        """Σ kebutuhan material sepanjang horizon forecast × harga beli; material tanpa harga dilewati."""
        product_series: dict[str, list[float]] = {}
        bom_lines: list[BomLine] = []
        for result in await self._forecast.list_results(run_id):
            fdata = getattr(result, "forecast_data", None) or []
            if result.status != "COMPLETED" or result.product_id is None or not fdata:
                continue
            pid = str(result.product_id)
            product_series[pid] = [float(p.get("value", 0)) for p in fdata]
            for bom in await self._boms.list(pid):
                bom_lines.append(BomLine(str(bom.product_id), str(bom.material_id), float(bom.qty_per_unit)))

        total, missing = Decimal(0), 0
        for material_id, series in breakdown_requirements_series(product_series, bom_lines).items():
            material = await self._materials.get_by_id(material_id) if self._materials else None
            price = getattr(material, "unit_price", None) if material is not None else None
            if price is None:
                missing += 1
                continue
            total += Decimal(str(sum(series))) * Decimal(str(price))
        return _dec(total), missing

    async def _baseline_costs(self, run_id: str, cost, method: str, recs=()) -> tuple[Decimal, Decimal]:
        """(biaya pesan, biaya simpan) baseline — TIC = jumlah keduanya. TIC bila perusahaan pakai seri planning existing (planning → BOM → EOQ per material).

        Fase 11.4: metode EOQ per material dipilih dengan aturan yang SAMA seperti usulan
        (`choose_eoq`: klasik bila harga & i ada), supaya basis biaya (tahunan vs horizon)
        kedua sisi setara.
        23 Nov 2026: kebutuhan EOQ = MRP + SS + B (`eoq_requirement_series`), sama dengan usulan.
        Baseline memakai SS & B SISTEM (sebelum adjust kapasitas) dari rekomendasi run ini.
        """
        product_planning: dict[str, list[float]] = {}
        bom_lines: list[BomLine] = []
        planning_dates: list = []

        for result in await self._forecast.list_results(run_id):
            if result.status != "COMPLETED" or result.product_id is None:
                continue
            pid = str(result.product_id)
            product = await self._products.get_by_id(pid)
            code = product.code if product else None
            drows = sorted(
                await self._demand.list_for_product(pid, code), key=lambda r: str(r.period)
            )
            series = [float(r.planning) for r in drows if r.planning is not None]
            if series:
                product_planning[pid] = series
                if not planning_dates:
                    planning_dates = [str(r.period) for r in drows if r.planning is not None]
            for bom in await self._boms.list(pid):
                bom_lines.append(BomLine(str(bom.product_id), str(bom.material_id), float(bom.qty_per_unit)))

        material_series = breakdown_requirements_series(product_planning, bom_lines)
        days = days_in_period(planning_dates)
        levels = {str(r.material_id): _system_stock_levels(r) for r in recs}
        ordering, holding = 0.0, 0.0
        for material_id, series in material_series.items():
            material = await self._materials.get_by_id(material_id) if self._materials else None
            price = getattr(material, "unit_price", None) if material is not None else None
            ss, buffer = levels.get(str(material_id), (0.0, 0.0))
            demand = eoq_requirement_series(series, ss, buffer)
            eoq = choose_eoq(demand, days, method, price, cost.holding_rate_pct, cost)
            ordering += eoq.ordering_cost
            holding += eoq.holding_cost
        return _dec(ordering), _dec(holding)

    async def _require_run(self, user_id: str, run_id: str):
        # CR v3.5 §3.4 Opsi A: run terlihat semua role (single-tenant) — tidak ada cek
        # pemilik; pembatasan tulis lewat RBAC endpoint (app/utils/permissions.py).
        run = await self._forecast.get_run(run_id)
        if run is None:
            raise ForecastRunNotFoundError("Forecast run tidak ditemukan.")
        return run
