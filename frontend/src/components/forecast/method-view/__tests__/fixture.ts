import type { MethodComparison, MethodComparisonRow } from "@/types/forecast";
import type { Product } from "@/types/product";

export const PERIODS = Array.from({ length: 12 }, (_, i) => `2026-${String(i + 1).padStart(2, "0")}-01`);

export const PRODUCTS: Product[] = ["PL", "SB", "BB"].map((code, i) => ({
  id: `p${i + 1}`, code, name: `Varian ${code}`, category: null, unit: "BTL",
}));

function ok(pid: string, base: number, mad: number, mape: number, mfe: number): MethodComparisonRow {
  const forecast = Object.fromEntries(PERIODS.map((d, i) => [d, base + i + 0.4]));
  return {
    product_id: pid, status: "OK", forecast,
    total: Object.values(forecast).reduce((a, b) => a + b, 0), mad, mape, mfe,
  };
}

const failed = (pid: string): MethodComparisonRow => ({
  product_id: pid, status: "FAILED", forecast: {}, total: null, mad: null, mape: null, mfe: null,
});

export const COMPARISON: MethodComparison = {
  run_id: "run1",
  periods: PERIODS,
  criteria: ["mad", "mape", "mfe"],
  methods: [
    {
      method: "random_forest", label: "Random Forest",
      rows: [ok("p1", 1000, 10, 5, -1), ok("p2", 200, 4, 8, 2), ok("p3", 50, 1, 3, -1)],
      average: { mad: 5, mape: 5.33, mfe: 0, n: 3, n_total: 3 },
    },
    {
      method: "lstm", label: "LSTM",
      rows: [ok("p1", 1000, 9, 4, 1), failed("p2"), { ...ok("p3", 50, 2, 2, 0), status: "NO_SERIES", forecast: {}, total: null }],
      average: { mad: 5.5, mape: 3, mfe: 0.5, n: 2, n_total: 3 },
    },
    {
      method: "moving_average", label: "Moving Average",
      rows: [ok("p1", 900, 12, 6, 3), ok("p2", 210, 5, 9, 1), ok("p3", 55, 2, 4, 0)],
      average: { mad: 6.33, mape: 6.33, mfe: 1.33, n: 3, n_total: 3 },
    },
  ],
  run_selection: {
    best_method: "random_forest",
    criteria: ["mad", "mape", "mfe"],
    ranking_basis: "common",
    n_common: 3,
    n_completed: 3,
    excluded_methods: ["lstm"],
    ranking: [
      { method: "random_forest", rank: 1, rank_mad: 1, rank_mape: 1, rank_mfe: 1, mad: 5, mape: 5.33, mfe: 0, n_products: 3 },
      { method: "moving_average", rank: 2, rank_mad: 2, rank_mape: 2, rank_mfe: 2, mad: 6.33, mape: 6.33, mfe: 1.33, n_products: 3 },
    ],
    decided_by: "mad",
    summary: "Random Forest dipilih sebagai metode terbaik untuk seluruh 3 produk.",
    reasons: ["Rata-rata MAD terkecil.", "Pembanding terdekat (peringkat 2): Moving Average."],
  },
  product_methods: [
    { product_id: "p1", status: "COMPLETED", system_method: "random_forest", method_used: "random_forest", is_overridden: false },
    { product_id: "p2", status: "COMPLETED", system_method: "random_forest", method_used: "moving_average", is_overridden: true },
    { product_id: "p3", status: "COMPLETED", system_method: "random_forest", method_used: "random_forest", is_overridden: false },
  ],
};

export const variantLabel = (pid: string) => PRODUCTS.find((p) => p.id === pid)?.code ?? pid.slice(0, 8);
