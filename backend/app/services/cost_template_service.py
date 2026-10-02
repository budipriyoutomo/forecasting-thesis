"""
CostTemplateService (Fase 10, 2 Oktober 2026) — master template biaya,
docs/ARCHITECTURE.md §6.8, RECONCILIATION §"Konsolidasi Master Data".

Template menyimpan S (`ordering_cost`) & H (`holding_cost`, isian manual planner)
yang dipakai EOQ/TIC bila template itu aktif. Overhead bulanan & depresiasi aset
penyimpanan (pallet, rak, alat handling) hanya REFERENSI: dirangkum jadi *saran H*
= (Σ depresiasi + Σ overhead) ÷ total kapasitas gudang (dus) — tidak dipakai EOQ.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Callable

from app.models.cost_template import CostTemplate, CostTemplateItem
from app.schemas.cost_template import CostTemplateCreate
from app.services.warehouse_service import capacity_dus_of
from app.utils.exceptions import CostTemplateNameExistsError, CostTemplateNotFoundError

_Q = Decimal("0.0001")


def _q(value: Decimal) -> Decimal:
    return value.quantize(_Q, rounding=ROUND_HALF_UP)


def _d(value) -> Decimal:
    return Decimal(str(value or 0))


# ── Fungsi murni ──


def monthly_depreciation(purchase_price, salvage_value, useful_life_months: int, qty) -> Decimal:
    """Depresiasi garis lurus per bulan: (harga beli − nilai sisa) ÷ umur (bulan) × qty."""
    return _q((_d(purchase_price) - _d(salvage_value)) / Decimal(useful_life_months) * _d(qty))


def item_monthly_cost(item) -> Decimal:
    """Biaya per bulan satu item: overhead × qty, atau depresiasi aset."""
    if item.item_type == "OVERHEAD":
        return _q(_d(item.monthly_amount) * _d(item.qty))
    return monthly_depreciation(item.purchase_price, item.salvage_value, item.useful_life_months, item.qty)


@dataclass
class TemplateSummary:
    total_depreciation_monthly: Decimal
    total_overhead_monthly: Decimal
    total_monthly: Decimal
    total_capacity_dus: Decimal
    suggested_holding_cost: Decimal | None


def summarize_template(items, total_capacity_dus) -> TemplateSummary:
    depreciation = sum(
        (item_monthly_cost(i) for i in items if i.item_type == "STORAGE_ASSET"), Decimal(0)
    )
    overhead = sum((item_monthly_cost(i) for i in items if i.item_type == "OVERHEAD"), Decimal(0))
    total = depreciation + overhead
    capacity = _d(total_capacity_dus)
    return TemplateSummary(
        total_depreciation_monthly=_q(depreciation),
        total_overhead_monthly=_q(overhead),
        total_monthly=_q(total),
        total_capacity_dus=_q(capacity),
        suggested_holding_cost=_q(total / capacity) if capacity > 0 else None,
    )


@dataclass
class CostParams:
    """S & H yang dipakai EOQ/TIC beserta sumbernya (template aktif / env)."""

    ordering_cost: float
    holding_cost: float
    source: str  # "template" | "env"
    template_name: str | None = None


def resolve_cost_params(active_template, settings) -> CostParams:
    """Template aktif menang; tanpa template aktif → DEFAULT_* env (perilaku sebelum Fase 10)."""
    if active_template is not None:
        return CostParams(
            ordering_cost=float(active_template.ordering_cost),
            holding_cost=float(active_template.holding_cost),
            source="template",
            template_name=active_template.name,
        )
    return CostParams(
        ordering_cost=float(settings.DEFAULT_ORDERING_COST),
        holding_cost=float(settings.DEFAULT_HOLDING_COST_RATE),
        source="env",
    )


async def load_cost_params(cost_templates, settings) -> CostParams:
    """Ambil template aktif dari repo (boleh None → langsung env)."""
    active = await cost_templates.get_active() if cost_templates is not None else None
    return resolve_cost_params(active, settings)


# ── Orkestrasi ──


class CostTemplateService:
    def __init__(
        self,
        repo,
        warehouse_configs,
        template_factory: Callable[..., object] = CostTemplate,
        item_factory: Callable[..., object] = CostTemplateItem,
    ):
        self._repo = repo
        self._warehouse = warehouse_configs
        self._template = template_factory
        self._item = item_factory

    async def list(self):
        return await self._repo.list()

    async def get(self, template_id: str):
        template = await self._repo.get_by_id(template_id)
        if template is None:
            raise CostTemplateNotFoundError("Template biaya tidak ditemukan.")
        return template

    async def find_active(self):
        """Template aktif atau None — dipakai EOQ/TIC untuk fallback ke env."""
        return await self._repo.get_active()

    async def get_active(self):
        template = await self.find_active()
        if template is None:
            raise CostTemplateNotFoundError("Belum ada template biaya yang aktif.")
        return template

    async def create(self, payload: CostTemplateCreate):
        await self._require_unique_name(payload.name)
        template = self._template(
            name=payload.name,
            description=payload.description,
            ordering_cost=payload.ordering_cost,
            holding_cost=payload.holding_cost,
            items=self._build_items(payload),
        )
        template.is_active = False  # aktivasi selalu eksplisit lewat activate()
        return await self._repo.add(template)

    async def update(self, template_id: str, payload: CostTemplateCreate):
        template = await self.get(template_id)
        await self._require_unique_name(payload.name, exclude_id=template.id)
        template.name = payload.name
        template.description = payload.description
        template.ordering_cost = payload.ordering_cost
        template.holding_cost = payload.holding_cost
        template.items = self._build_items(payload)
        return await self._repo.save(template)

    async def activate(self, template_id: str):
        template = await self.get(template_id)
        await self._repo.set_active(template.id)
        return await self.get(template_id)

    async def delete(self, template_id: str) -> None:
        template = await self.get(template_id)
        await self._repo.delete(template)

    async def summary(self, template_id: str) -> TemplateSummary:
        template = await self.get(template_id)
        configs = await self._warehouse.list()
        total_dus = sum((Decimal(str(capacity_dus_of(c))) for c in configs), Decimal(0))
        return summarize_template(template.items, total_dus)

    async def _require_unique_name(self, name: str, exclude_id=None) -> None:
        existing = await self._repo.get_by_name(name)
        if existing is not None and str(existing.id) != str(exclude_id):
            raise CostTemplateNameExistsError(f"Nama template '{name}' sudah dipakai.")

    def _build_items(self, payload: CostTemplateCreate) -> list:
        return [
            self._item(
                position=i,
                item_type=item.item_type,
                name=item.name,
                monthly_amount=item.monthly_amount if item.item_type == "OVERHEAD" else None,
                purchase_price=item.purchase_price if item.item_type == "STORAGE_ASSET" else None,
                salvage_value=(item.salvage_value or Decimal(0)) if item.item_type == "STORAGE_ASSET" else None,
                useful_life_months=item.useful_life_months if item.item_type == "STORAGE_ASSET" else None,
                qty=item.qty,
            )
            for i, item in enumerate(payload.items)
        ]
