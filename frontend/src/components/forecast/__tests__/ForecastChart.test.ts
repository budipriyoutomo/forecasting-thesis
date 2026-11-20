import { describe, expect, it } from "vitest";

import { buildChartData } from "@/components/forecast/ForecastChart";

describe("buildChartData (CR v3.6 §7.1 — histori → forecast)", () => {
  const forecast = [
    { date: "2026-11-01", value: 110, lower: 100, upper: 120 },
    { date: "2026-12-01", value: 115, lower: 101, upper: 129 },
  ];
  const history = [
    { date: "2026-09-01", value: 95 },
    { date: "2026-10-01", value: 102 },
  ];

  it("histori dulu, lalu forecast, terurut tanggal; titik histori tanpa band", () => {
    const { data, forecastStart } = buildChartData(forecast, history);
    expect(data.map((d) => d.date)).toEqual(["2026-09-01", "2026-10-01", "2026-11-01", "2026-12-01"]);
    expect(data[0]).toMatchObject({ actual: 95, value: null, range: null });
    expect(data[2]).toMatchObject({ actual: null, value: 110, range: [100, 120] });
    expect(forecastStart).toBe("2026-11-01");
  });

  it("garis forecast tersambung ke titik histori terakhir (tidak putus)", () => {
    const { data } = buildChartData(forecast, history);
    expect(data[1].value).toBeNull();
    expect(data[1].bridge).toBe(102);
    expect(data[2].bridge).toBe(110);
  });

  it("tanpa histori (run lama) → hanya forecast", () => {
    const { data, forecastStart } = buildChartData(forecast, []);
    expect(data).toHaveLength(2);
    expect(forecastStart).toBeNull();
  });
});
