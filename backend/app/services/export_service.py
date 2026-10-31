"""
ExportService — export hasil forecast & reorder ke Excel/PDF (Fase 8).

Fungsi builder MURNI (bytes, mudah dites): `build_forecast_xlsx`,
`build_reorder_xlsx`, `build_reorder_pdf`, serta (Fase 11.6/11.7) proyeksi stok &
metrik inventory `build_stock_projection_{xlsx,pdf}`, `build_metrics_{xlsx,pdf}` —
kolom target pakai KODE material/produk (fallback id) untuk lampiran thesis. `ExportService` mengorkestrasi:
ambil data dari repo (cek kepemilikan run), bangun file, simpan ke object storage
`permanent/exports/...` (best-effort — kegagalan storage tidak menggagalkan download),
lalu kembalikan bytes untuk diunduh.
"""
import io
from datetime import datetime, timezone

from fpdf import FPDF
from openpyxl import Workbook

from app.utils.exceptions import ForbiddenRoleError, ForecastRunNotFoundError

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF_MIME = "application/pdf"


def _num(value):
    return float(value) if value is not None else None


def build_forecast_xlsx(results) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Forecast"
    ws.append(["product_id", "status", "method_used", "selection_mode", "mape", "mase", "explanation"])
    for r in results:
        ws.append(
            [
                str(r.product_id),
                r.status,
                r.method_used,
                r.selection_mode,
                _num(r.mape),
                _num(r.mase),
                r.explanation,
            ]
        )
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def build_reorder_xlsx(recommendations) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Reorder"
    # Kolom EOQ/biaya (Fase 9) ditambah SETELAH `status` → kolom lama tidak bergeser
    # (backward compat, larangan regresi). rec lama tanpa field baru → sel kosong.
    ws.append(
        [
            "material_id", "safety_stock", "reorder_point", "recommended_order_qty", "status",
            "buffer_stock", "eoq_qty", "ordering_cost", "holding_cost", "total_inventory_cost",
        ]
    )
    for rec in recommendations:
        ws.append(
            [
                str(rec.material_id),
                _num(rec.safety_stock),
                _num(rec.reorder_point),
                _num(rec.recommended_order_qty),
                rec.status,
                _num(getattr(rec, "buffer_stock", None)),
                _num(getattr(rec, "eoq_qty", None)),
                _num(getattr(rec, "ordering_cost", None)),
                _num(getattr(rec, "holding_cost", None)),
                _num(getattr(rec, "total_inventory_cost", None)),
            ]
        )
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def build_reorder_pdf(run, recommendations) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Laporan Rekomendasi Reorder", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Run: {run.id}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0, 6, f"Dibuat: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(2)

    headers = ["Material", "Safety", "ROP", "Order qty", "Status"]
    widths = [70, 25, 25, 30, 30]
    pdf.set_font("Helvetica", "B", 9)
    for h, w in zip(headers, widths):
        pdf.cell(w, 7, h, border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for rec in recommendations:
        row = [
            str(rec.material_id)[:32],
            f"{_num(rec.safety_stock):.2f}",
            f"{_num(rec.reorder_point):.2f}",
            f"{_num(rec.recommended_order_qty):.2f}",
            rec.status,
        ]
        for value, w in zip(row, widths):
            pdf.cell(w, 7, value, border=1)
        pdf.ln()

    out = pdf.output()
    return bytes(out)


def _label(labels: dict, target_id) -> str:
    return labels.get(str(target_id), str(target_id))


def _xlsx(title: str, headers: list[str], rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = title
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _fmt(value, digits: int = 2) -> str:
    return "-" if value is None else f"{float(value):,.{digits}f}"


def _pdf_table(title: str, run, headers: list[str], widths: list[int], rows: list[list[str]]) -> bytes:
    pdf = FPDF(orientation="L")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Run: {run.id}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0, 6, f"Dibuat: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 8)
    for h, w in zip(headers, widths):
        pdf.cell(w, 7, h, border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for row in rows:
        for value, w in zip(row, widths):
            pdf.cell(w, 6, value, border=1)
        pdf.ln()
    return bytes(pdf.output())


_PROJECTION_COLS = [
    "opening_qty", "receipt_qty", "usage_qty", "order_qty", "ending_qty", "shortage_qty",
    "capacity_qty", "utilization_opening_pct", "utilization_ending_pct",
]


def build_stock_projection_xlsx(rows, labels: dict) -> bytes:
    headers = ["material", "scenario", "period", *_PROJECTION_COLS, "is_within_capacity"]
    data = [
        [_label(labels, r.material_id), r.scenario, str(r.period)]
        + [_num(getattr(r, c)) for c in _PROJECTION_COLS]
        + [r.is_within_capacity]
        for r in rows
    ]
    return _xlsx("Proyeksi Stok", headers, data)


def build_stock_projection_pdf(run, rows, labels: dict) -> bytes:
    headers = ["Material", "Skenario", "Periode", "Awal", "Terima", "Pakai", "Order", "Akhir",
               "Kurang", "Kapasitas", "Util. akhir %", "Muat"]
    widths = [42, 20, 22, 22, 20, 20, 20, 22, 20, 24, 24, 14]
    data = [
        [
            _label(labels, r.material_id)[:24], r.scenario, str(r.period),
            _fmt(r.opening_qty), _fmt(r.receipt_qty), _fmt(r.usage_qty), _fmt(r.order_qty),
            _fmt(r.ending_qty), _fmt(r.shortage_qty), _fmt(r.capacity_qty),
            _fmt(r.utilization_ending_pct, 1),
            "-" if r.is_within_capacity is None else ("Ya" if r.is_within_capacity else "Tidak"),
        ]
        for r in rows
    ]
    return _pdf_table("Proyeksi Stok Material", run, headers, widths, data)


_METRIC_COLS = [
    "service_level", "fill_rate", "stock_out_rate", "inventory_turnover", "inventory_days", "shortage_cost",
]


def build_metrics_xlsx(rows, labels: dict) -> bytes:
    headers = ["target_type", "target", "scope", *_METRIC_COLS]
    data = [
        [r.target_type, _label(labels, r.target_id), r.scope]
        + [_num(getattr(r, c, None)) for c in _METRIC_COLS]
        for r in rows
    ]
    return _xlsx("Metrik Inventory", headers, data)


def build_metrics_pdf(run, rows, labels: dict) -> bytes:
    headers = ["Tipe", "Target", "Skenario", "Service level", "Fill rate", "Stockout", "Turnover",
               "Inv. days", "Shortage cost"]
    widths = [22, 50, 24, 26, 24, 24, 24, 24, 40]
    data = [
        [
            r.target_type, _label(labels, r.target_id)[:28], r.scope,
            _fmt(r.service_level, 4), _fmt(r.fill_rate, 4), _fmt(r.stock_out_rate, 4),
            _fmt(r.inventory_turnover), _fmt(getattr(r, "inventory_days", None)),
            _fmt(getattr(r, "shortage_cost", None)),
        ]
        for r in rows
    ]
    return _pdf_table("Evaluasi Kinerja Inventory", run, headers, widths, data)


class ExportService:
    def __init__(
        self, forecast_repo, reorder_repo, storage=None,
        projections=None, metrics_repo=None, materials=None, products=None,
    ):
        self._forecast = forecast_repo
        self._reorder = reorder_repo
        self._storage = storage
        self._projections = projections
        self._metrics = metrics_repo
        self._materials = materials
        self._products = products

    async def export_forecast(self, user_id: str, run_id: str):
        run = await self._require_run(user_id, run_id)
        results = await self._forecast.list_results(run_id)
        content = build_forecast_xlsx(results)
        filename = f"forecast_{run_id}.xlsx"
        self._archive(user_id, run_id, filename, content)
        return content, filename, XLSX_MIME

    async def export_reorder(self, user_id: str, run_id: str, fmt: str):
        run = await self._require_run(user_id, run_id)
        recs = await self._reorder.list_by_run(run_id)
        if fmt == "pdf":
            content = build_reorder_pdf(run, recs)
            filename, mime = f"reorder_{run_id}.pdf", PDF_MIME
        else:
            content = build_reorder_xlsx(recs)
            filename, mime = f"reorder_{run_id}.xlsx", XLSX_MIME
        self._archive(user_id, run_id, filename, content)
        return content, filename, mime

    async def export_stock_projection(self, user_id: str, run_id: str, fmt: str, scenario: str | None = None):
        run = await self._require_run(user_id, run_id)
        rows = [r for r in await self._projections.list_by_run(run_id) if scenario is None or r.scenario == scenario]
        labels = await self._labels()
        return self._finish(
            user_id, run_id, f"stock_projection_{run_id}", fmt,
            lambda: build_stock_projection_pdf(run, rows, labels),
            lambda: build_stock_projection_xlsx(rows, labels),
        )

    async def export_metrics(self, user_id: str, run_id: str, fmt: str, target_type: str | None = None):
        run = await self._require_run(user_id, run_id)
        rows = [r for r in await self._metrics.list_by_run(run_id) if target_type is None or r.target_type == target_type]
        labels = await self._labels()
        return self._finish(
            user_id, run_id, f"inventory_metrics_{run_id}", fmt,
            lambda: build_metrics_pdf(run, rows, labels),
            lambda: build_metrics_xlsx(rows, labels),
        )

    def _finish(self, user_id, run_id, stem, fmt, build_pdf, build_xlsx):
        if fmt == "pdf":
            content, filename, mime = build_pdf(), f"{stem}.pdf", PDF_MIME
        else:
            content, filename, mime = build_xlsx(), f"{stem}.xlsx", XLSX_MIME
        self._archive(user_id, run_id, filename, content)
        return content, filename, mime

    async def _labels(self) -> dict:
        labels = {}
        for repo in (self._materials, self._products):
            if repo is not None:
                labels.update({str(item.id): item.code for item in await repo.list()})
        return labels

    def _archive(self, user_id: str, run_id: str, filename: str, content: bytes) -> None:
        # Simpan ke permanent/exports (best-effort). Kegagalan penyimpanan
        # arsip tidak boleh menggagalkan download file oleh user.
        if self._storage is None:
            return
        try:
            self._storage.upload_export(user_id, run_id, filename, content)
        except Exception:
            pass

    async def _require_run(self, user_id: str, run_id: str):
        run = await self._forecast.get_run(run_id)
        if run is None:
            raise ForecastRunNotFoundError("Forecast run tidak ditemukan.")
        if str(run.user_id) != str(user_id):
            raise ForbiddenRoleError("Anda tidak berhak mengekspor run ini.")
        return run
