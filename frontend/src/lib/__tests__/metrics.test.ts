import { describe, expect, it } from "vitest";

import { ALL_METRICS, METRIC_INFO, bestAccuracyMetric, formatMetric, metricColumns } from "@/lib/metrics";

// Keputusan user 21 Nov 2026 — pengujian peramalan hanya MAD, MFE, MAPE.
describe("METRIC_INFO — sumber tunggal metrik pengujian peramalan", () => {
  it("hanya MAD, MFE, MAPE (tanpa MSE & MASE)", () => {
    expect(ALL_METRICS).toEqual(["mad", "mfe", "mape"]);
    expect(Object.keys(METRIC_INFO).sort()).toEqual(["mad", "mape", "mfe"]);
  });

  it("punya label, definisi, dan arah lebih baik", () => {
    for (const key of ALL_METRICS) {
      expect(METRIC_INFO[key].label).toBeTruthy();
      expect(METRIC_INFO[key].definition.length).toBeGreaterThan(10);
    }
    expect(METRIC_INFO.mfe.definition.toLowerCase()).toContain("bias");
    expect(METRIC_INFO.mfe.better).toBe("zero");
    expect(METRIC_INFO.mape.interpret(15)).toBe("Baik");
  });
});

describe("metricColumns", () => {
  it("mengikuti checkbox, urutan baku", () => {
    expect(metricColumns(["mape", "mad"])).toEqual(["mad", "mape"]);
  });

  it("nilai lama (mse/mase) dari pengaturan tersimpan diabaikan", () => {
    expect(metricColumns(["mase", "mse", "mfe"] as never)).toEqual(["mfe"]);
  });

  it("tanpa pengaturan / kosong setelah disaring → semua metrik", () => {
    expect(metricColumns(undefined)).toEqual(["mad", "mfe", "mape"]);
    expect(metricColumns(["mse"] as never)).toEqual(["mad", "mfe", "mape"]);
  });
});

describe("bestAccuracyMetric — tile dashboard: rata-rata error paling kecil", () => {
  it("pilih nilai terkecil di antara MAD, |MFE|, MAPE", () => {
    expect(bestAccuracyMetric({ mad: 12, mfe: -3.5, mape: 8 })).toEqual({ key: "mfe", value: -3.5 });
    expect(bestAccuracyMetric({ mad: 12, mfe: 9, mape: 8 })).toEqual({ key: "mape", value: 8 });
    expect(bestAccuracyMetric({ mad: 2, mfe: 3, mape: 8 })).toEqual({ key: "mad", value: 2 });
  });

  it("abaikan yang null; semua null → null", () => {
    expect(bestAccuracyMetric({ mad: null, mfe: null, mape: 8 })).toEqual({ key: "mape", value: 8 });
    expect(bestAccuracyMetric({ mad: null, mfe: null, mape: null })).toBeNull();
  });
});

describe("formatMetric", () => {
  it("MAPE dengan persen, lainnya 2 desimal", () => {
    expect(formatMetric(11.424, "mape")).toBe("11.42%");
    expect(formatMetric(-2.1, "mfe")).toBe("-2.10");
    expect(formatMetric(null, "mad")).toBe("—");
  });
});
