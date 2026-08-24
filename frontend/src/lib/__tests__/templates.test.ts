import { describe, expect, it } from "vitest";

import {
  DEMAND_TEMPLATE_COLUMNS,
  DEMAND_TEMPLATE_FILENAME,
  buildDemandTemplateCsv,
} from "@/lib/templates";

describe("buildDemandTemplateCsv", () => {
  const csv = buildDemandTemplateCsv();
  const lines = csv.trim().split("\n");

  it("header sama persis dengan kontrak backend (urutan & ejaan kolom)", () => {
    expect(lines[0]).toBe("product_code,period,forecast_existing,planning,actual");
  });

  it("berisi contoh cukup banyak supaya lolos UPLOAD_MIN_ROWS (10 baris)", () => {
    expect(lines.length - 1).toBeGreaterThanOrEqual(10);
  });

  it("period memakai format ISO YYYY-MM-DD dan angka tanpa pemisah ribuan", () => {
    const cells = lines[1].split(",");

    expect(cells[1]).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(cells[4]).toMatch(/^\d+(\.\d+)?$/);
  });

  it("berisi lebih dari satu product_code — satu file boleh banyak SKU", () => {
    const codes = new Set(lines.slice(1).map((l) => l.split(",")[0]));

    expect(codes.size).toBeGreaterThan(1);
  });

  it("mendokumentasikan kolom wajib & opsional sesuai data_ingestion_service", () => {
    const required = DEMAND_TEMPLATE_COLUMNS.filter((c) => c.required).map((c) => c.name);
    const optional = DEMAND_TEMPLATE_COLUMNS.filter((c) => !c.required).map((c) => c.name);

    expect(required).toEqual(["product_code", "period", "actual"]);
    expect(optional).toEqual(["forecast_existing", "planning"]);
  });

  it("nama file template berekstensi .csv", () => {
    expect(DEMAND_TEMPLATE_FILENAME).toMatch(/\.csv$/);
  });
});
