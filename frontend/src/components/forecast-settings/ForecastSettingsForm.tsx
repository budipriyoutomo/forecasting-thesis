"use client";

import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { methodLabel } from "@/lib/methods";
import type {
  AlphaMetric,
  EoqMethod,
  ForecastSettingsInput,
  OrderQtyPolicy,
  RankingMetric,
  RopFormula,
} from "@/types/forecastSettings";

export const RANKING_OPTIONS: { value: RankingMetric; label: string; description: string }[] = [
  {
    value: "mad",
    label: "MAD",
    description: "Rata-rata selisih absolut (unit). Konsisten dengan pemilihan α Exponential Smoothing.",
  },
  {
    value: "mfe_abs",
    label: "|MFE|",
    description: "Bias forecast terkecil. MFE positif = under-estimate, negatif = over-estimate.",
  },
  {
    value: "mape",
    label: "MAPE",
    description: "Galat relatif (%) — mudah dibandingkan antar-SKU dengan volume berbeda.",
  },
];

// Fase 11.9 — satu setting untuk tabel Reorder DAN Proyeksi Stok (sumber tunggal).
export const ROP_FORMULA_OPTIONS: { value: RopFormula; label: string; description: string }[] = [
  {
    value: "with_buffer",
    label: "Dengan buffer: μ·L + SS + B",
    description: "Buffer stock (antisipasi waste) ikut menaikkan titik pesan.",
  },
  {
    value: "standard",
    label: "Standar: μ·L + SS",
    description: "Rumus ROP buku teks; buffer tetap dihitung tapi tidak masuk titik pesan.",
  },
];

export const ORDER_QTY_POLICY_OPTIONS: { value: OrderQtyPolicy; label: string; description: string }[] = [
  {
    value: "order_up_to",
    label: "Order-up-to: max(MOQ, S − stok)",
    description: "Isi stok sampai level S = ROP + μ·L.",
  },
  {
    value: "eoq",
    label: "Kelipatan EOQ: n × EOQ",
    description: "Pesan EOQ (n terkecil sampai stok ≥ ROP). EOQ belum tersedia → order-up-to.",
  },
];

// Grid α thesis (docx): stabil 0,01/0,05/0,15/0,2 · bergejolak 0,8/0,95/0,99.
export const THESIS_ALPHA_GRID = [0.01, 0.05, 0.15, 0.2, 0.8, 0.95, 0.99];

// Pemisah antar-α: titik koma, spasi, atau koma+spasi — koma tanpa spasi dibaca sebagai
// desimal Indonesia ("0,95" = 0.95).
export function parseAlphaGrid(text: string): number[] | null {
  const parts = text.trim().split(/\s*;\s*|,\s+|\s+/).filter(Boolean);
  if (parts.length === 0) return null;
  const values = parts.map((p) => Number(p.replace(",", ".")));
  if (values.some((v) => !Number.isFinite(v) || v <= 0 || v >= 1)) return null;
  return [...new Set(values)].sort((a, b) => a - b);
}

// Ketiga peringkat selalu ditampilkan di hasil forecast sebagai acuan; pilihan metrik di
// sini hanya menentukan metode PEMENANG otomatis untuk run berikutnya. Metode aktif =
// kandidat mode otomatis sekaligus pilihan mode manual.
export function ForecastSettingsForm({
  initial,
  available,
  onSubmit,
  pending = false,
  error = null,
}: {
  initial: ForecastSettingsInput;
  available: string[];
  onSubmit: (input: ForecastSettingsInput) => void;
  pending?: boolean;
  error?: string | null;
}) {
  const [metric, setMetric] = useState<RankingMetric>(initial.ranking_metric);
  const [enabled, setEnabled] = useState<Set<string>>(
    () => new Set(initial.enabled_methods ?? available),
  );
  const noneEnabled = enabled.size === 0;
  const [alphaText, setAlphaText] = useState((initial.es_alpha_grid ?? THESIS_ALPHA_GRID).join(", "));
  const alphaGrid = parseAlphaGrid(alphaText);
  const [alphaMetric, setAlphaMetric] = useState<AlphaMetric>(initial.es_alpha_metric ?? "mad");
  const [gridSearch, setGridSearch] = useState(Boolean(initial.ml_grid_search));
  const [winsorize, setWinsorize] = useState(Boolean(initial.ml_winsorize));
  const [serviceLevel, setServiceLevel] = useState(initial.service_level_pct ?? 95);
  const [eoqMethod, setEoqMethod] = useState<EoqMethod>(initial.eoq_method ?? "classic");
  const [ropFormula, setRopFormula] = useState<RopFormula>(initial.rop_formula ?? "with_buffer");
  const [qtyPolicy, setQtyPolicy] = useState<OrderQtyPolicy>(initial.order_qty_policy ?? "order_up_to");

  const toggle = (method: string) =>
    setEnabled((prev) => {
      const next = new Set(prev);
      if (next.has(method)) next.delete(method);
      else next.add(method);
      return next;
    });

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          ranking_metric: metric,
          enabled_methods: available.filter((m) => enabled.has(m)),
          es_alpha_grid: alphaGrid ?? undefined,
          es_alpha_metric: alphaMetric,
          ml_grid_search: gridSearch,
          ml_winsorize: winsorize,
          service_level_pct: serviceLevel,
          eoq_method: eoqMethod,
          rop_formula: ropFormula,
          order_qty_policy: qtyPolicy,
        });
      }}
    >
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">Metrik penentu metode pemenang</legend>
        {RANKING_OPTIONS.map((opt) => (
          <label
            key={opt.value}
            className="flex cursor-pointer items-start gap-3 rounded-lg border p-3 has-[:checked]:border-primary has-[:checked]:bg-muted/50"
          >
            <input
              type="radio"
              name="ranking_metric"
              value={opt.value}
              checked={metric === opt.value}
              onChange={() => setMetric(opt.value)}
              aria-describedby={`ranking-${opt.value}-desc`}
              className="mt-1"
            />
            <span className="flex flex-col gap-0.5">
              <span className="text-sm font-medium">{opt.label}</span>
              <span id={`ranking-${opt.value}-desc`} className="text-sm text-muted-foreground">
                {opt.description}
              </span>
            </span>
          </label>
        ))}
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">Metode aktif</legend>
        <p className="text-sm text-muted-foreground">
          Dibandingkan di mode otomatis dan bisa dipilih di mode manual.
        </p>
        <div className="grid gap-2 sm:grid-cols-2">
          {available.map((m) => (
            <label key={m} className="flex cursor-pointer items-center gap-3 rounded-lg border p-3">
              <input type="checkbox" checked={enabled.has(m)} onChange={() => toggle(m)} />
              <span className="text-sm">{methodLabel(m)}</span>
            </label>
          ))}
        </div>
        {noneEnabled && (
          <p className="text-sm text-destructive">Pilih minimal satu metode.</p>
        )}
      </fieldset>

      <fieldset className="flex flex-col gap-3">
        <legend className="mb-1 text-sm font-medium">Exponential Smoothing</legend>
        <label className="flex flex-col gap-1 text-sm">
          <span>Grid α (dicoba satu per satu)</span>
          <input
            aria-label="Grid α"
            className="h-9 rounded-md border bg-transparent px-3 text-sm"
            value={alphaText}
            onChange={(e) => setAlphaText(e.target.value)}
          />
          <span className="text-xs text-muted-foreground">
            Default thesis: {THESIS_ALPHA_GRID.join(", ")}. Pisahkan dengan koma + spasi atau titik koma.
          </span>
        </label>
        {!alphaGrid && <p className="text-sm text-destructive">Setiap α harus angka antara 0 dan 1.</p>}
        <div className="flex flex-wrap gap-4 text-sm">
          {(["mad", "mape"] as const).map((m) => (
            <label key={m} className="flex items-center gap-2">
              <input type="radio" name="es_alpha_metric" checked={alphaMetric === m} onChange={() => setAlphaMetric(m)} />
              {m.toUpperCase()} (α)
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-2 text-sm">
        <legend className="mb-1 text-sm font-medium">Random Forest & XGBoost</legend>
        <label className="flex items-start gap-2">
          <input type="checkbox" className="mt-1" checked={gridSearch} onChange={(e) => setGridSearch(e.target.checked)} />
          <span>
            Grid search hyperparameter (GridSearchCV + TimeSeriesSplit)
            <span className="block text-xs text-muted-foreground">
              Sesuai thesis; run lebih lama. Data train yang terlalu pendek otomatis memakai parameter tetap.
            </span>
          </span>
        </label>
        <label className="flex items-start gap-2">
          <input type="checkbox" className="mt-1" checked={winsorize} onChange={(e) => setWinsorize(e.target.checked)} />
          <span>
            Cap outlier (IQR) sebelum training
            <span className="block text-xs text-muted-foreground">Nilai di luar Q1 − 1,5·IQR … Q3 + 1,5·IQR dipotong ke batasnya.</span>
          </span>
        </label>
      </fieldset>

      <fieldset className="flex flex-col gap-3 text-sm">
        <legend className="mb-1 text-sm font-medium">Perencanaan persediaan</legend>
        <div className="flex flex-col gap-1">
          <span>Target service level (Z safety stock)</span>
          <div className="flex flex-wrap gap-4">
            {[
              { v: 95, z: "1,645" },
              { v: 99, z: "2,326" },
            ].map((o) => (
              <label key={o.v} className="flex items-center gap-2">
                <input
                  type="radio"
                  name="service_level_pct"
                  checked={serviceLevel === o.v}
                  onChange={() => setServiceLevel(o.v)}
                />
                {o.v}% (Z ≈ {o.z})
              </label>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <span>Metode EOQ</span>
          <label className="flex items-start gap-2">
            <input type="radio" name="eoq_method" className="mt-1" checked={eoqMethod === "classic"} onChange={() => setEoqMethod("classic")} />
            <span>
              EOQ klasik √(2AS / iC) — thesis
              <span className="block text-xs text-muted-foreground">
                Butuh harga material & i (%) di template biaya; material tanpa data memakai EOQ dinamis.
              </span>
            </span>
          </label>
          <label className="flex items-start gap-2">
            <input type="radio" name="eoq_method" className="mt-1" checked={eoqMethod === "dynamic"} onChange={() => setEoqMethod("dynamic")} />
            <span>EOQ dinamis (simulasi jumlah pesanan pada horizon)</span>
          </label>
        </div>
        {(
          [
            { title: "Rumus titik pesan (ROP)", name: "rop_formula", options: ROP_FORMULA_OPTIONS, value: ropFormula, set: setRopFormula },
            { title: "Kebijakan qty pesan", name: "order_qty_policy", options: ORDER_QTY_POLICY_OPTIONS, value: qtyPolicy, set: setQtyPolicy },
          ] as const
        ).map((group) => (
          <div key={group.name} className="flex flex-col gap-1">
            <span>{group.title}</span>
            {group.options.map((opt) => (
              <label key={opt.value} className="flex items-start gap-2">
                <input
                  type="radio"
                  name={group.name}
                  className="mt-1"
                  checked={group.value === opt.value}
                  onChange={() => (group.set as (v: string) => void)(opt.value)}
                />
                <span>
                  {opt.label}
                  <span className="block text-xs text-muted-foreground">{opt.description}</span>
                </span>
              </label>
            ))}
          </div>
        ))}
        <p className="text-xs text-muted-foreground">
          Berlaku untuk tabel Reorder dan Proyeksi Stok. μ = kebutuhan harian, L = lead time (hari).
        </p>
      </fieldset>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div>
        <Button type="submit" disabled={pending || noneEnabled || !alphaGrid}>
          {pending ? "Menyimpan…" : "Simpan pengaturan"}
        </Button>
      </div>
    </form>
  );
}
