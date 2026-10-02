import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CostTemplateSummaryPanel } from "@/components/cost-templates/CostTemplateSummaryPanel";
import type { Material } from "@/types/material";

import { SUMMARY, TEMPLATE } from "./fixtures";

const MATERIALS: Material[] = [
  { id: "m1", code: "RM-1", name: "Gula", category: null, unit: "kg", lead_time_days: 5, moq: "0", manual_safety_stock: null, unit_price: "14500" },
  { id: "m2", code: "RM-2", name: "Botol", category: null, unit: "pcs", lead_time_days: 5, moq: "0", manual_safety_stock: null, unit_price: null },
];

describe("CostTemplateSummaryPanel", () => {
  it("menampilkan depresiasi, overhead, saran H, dan H yang dipakai EOQ", () => {
    render(<CostTemplateSummaryPanel template={TEMPLATE} summary={SUMMARY} materials={MATERIALS} />);
    expect(screen.getByText("Rp 7.500.000")).toBeDefined();
    expect(screen.getByText("Rp 3.000.000")).toBeDefined();
    expect(screen.getByText("Rp 525")).toBeDefined(); // saran H
    expect(screen.getByText(/rp 800 dipakai eoq/i)).toBeDefined();
  });

  it("saran H tidak tersedia bila kapasitas gudang belum diisi", () => {
    render(
      <CostTemplateSummaryPanel
        template={TEMPLATE}
        summary={{ ...SUMMARY, suggested_holding_cost: null, total_capacity_dus: "0.0000" }}
        materials={MATERIALS}
      />,
    );
    expect(screen.getByText(/isi kapasitas gudang/i)).toBeDefined();
  });

  it("biaya pembelian: harga beli dari master material + jumlah yang belum berharga", () => {
    render(<CostTemplateSummaryPanel template={TEMPLATE} summary={SUMMARY} materials={MATERIALS} />);
    expect(screen.getByText("RM-1 — Gula")).toBeDefined();
    expect(screen.getByText("Rp 14.500 / kg")).toBeDefined();
    expect(screen.getByText(/1 material belum punya harga/i)).toBeDefined();
  });
});
