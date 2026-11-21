import { describe, expect, it } from "vitest";

import {
  DEMAND_TEMPLATE,
  DEMAND_TEMPLATE_COLUMNS,
  DEMAND_TEMPLATE_FILENAME,
  MATERIAL_USAGE_TEMPLATE,
  STOCK_SNAPSHOT_TEMPLATE,
  buildDemandTemplateCsv,
  buildTemplateCsv,
  type ImportTemplateSpec,
} from "@/lib/templates";

const parse = (spec: ImportTemplateSpec) => buildTemplateCsv(spec).trim().split("\n").map((l) => l.split(","));

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

describe.each([
  ["demand", DEMAND_TEMPLATE],
  ["stok ERP", STOCK_SNAPSHOT_TEMPLATE],
  ["pemakaian material", MATERIAL_USAGE_TEMPLATE],
])("template %s", (_, spec) => {
  it("setiap baris contoh punya jumlah sel sama dengan header", () => {
    const [header, ...rows] = parse(spec);
    expect(rows.length).toBeGreaterThan(0);
    rows.forEach((r) => expect(r).toHaveLength(header.length));
  });

  it("header = nama kolom yang didokumentasikan, nama file .csv, ada catatan pengisian", () => {
    expect(parse(spec)[0]).toEqual(spec.columns.map((c) => c.name));
    expect(spec.filename).toMatch(/\.csv$/);
    expect(spec.notes.length).toBeGreaterThan(0);
  });
});

describe("STOCK_SNAPSHOT_TEMPLATE", () => {
  it("mengikuti kontrak StockSnapshotService (inventory_data_service.py)", () => {
    const required = STOCK_SNAPSHOT_TEMPLATE.columns.filter((c) => c.required).map((c) => c.name);

    expect(parse(STOCK_SNAPSHOT_TEMPLATE)[0]).toEqual(["material_code", "snapshot_date", "qty", "uom"]);
    expect(required).toEqual(["material_code", "snapshot_date", "qty"]);
  });

  it("snapshot_date ISO dan qty angka non-negatif tanpa pemisah ribuan", () => {
    for (const [, date, qty] of parse(STOCK_SNAPSHOT_TEMPLATE).slice(1)) {
      expect(date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(qty).toMatch(/^\d+(\.\d+)?$/);
    }
  });
});

describe("MATERIAL_USAGE_TEMPLATE", () => {
  const [header, ...rows] = parse(MATERIAL_USAGE_TEMPLATE);
  const col = (row: string[], name: string) => row[header.indexOf(name)];

  it("mengikuti kontrak MaterialUsageService (material_usage_service.py)", () => {
    const required = MATERIAL_USAGE_TEMPLATE.columns.filter((c) => c.required).map((c) => c.name);

    expect(header).toEqual([
      "material_code", "period", "actual_usage", "standard_usage", "product_code", "production_output",
    ]);
    expect(required).toEqual(["material_code", "period", "actual_usage"]);
  });

  it("kolom standar ditandai bersyarat (salah satu cara wajib diisi)", () => {
    const conditional = MATERIAL_USAGE_TEMPLATE.columns.filter((c) => c.conditional).map((c) => c.name);

    expect(conditional).toEqual(["standard_usage", "product_code", "production_output"]);
  });

  it("contoh memperlihatkan kedua cara: standard_usage langsung, atau product_code + production_output", () => {
    const direct = rows.filter((r) => col(r, "standard_usage") !== "");
    const viaBom = rows.filter((r) => col(r, "standard_usage") === "");

    expect(direct.length).toBeGreaterThan(0);
    expect(viaBom.length).toBeGreaterThan(0);
    viaBom.forEach((r) => {
      expect(col(r, "product_code")).not.toBe("");
      expect(col(r, "production_output")).not.toBe("");
    });
  });
});
