import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ReorderTable } from "@/components/dashboard/ReorderTable";
import type { ReorderRecommendation } from "@/types/reorder";

const RECS: ReorderRecommendation[] = [
  { material_id: "m1", safety_stock: "6.6", reorder_point: "46.6", recommended_order_qty: "87", status: "urgent" },
  { material_id: "m2", safety_stock: "3", reorder_point: "20", recommended_order_qty: "0", status: "safe" },
  { material_id: "m3", safety_stock: "2", reorder_point: "10", recommended_order_qty: "0", status: "overstock" },
];

describe("ReorderTable", () => {
  it("menampilkan semua rekomendasi awalnya", () => {
    render(<ReorderTable recommendations={RECS} />);

    expect(screen.getByText("m1")).toBeDefined();
    expect(screen.getByText("m2")).toBeDefined();
    expect(screen.getByText("m3")).toBeDefined();
  });

  it("filter status urgent hanya menampilkan yang urgent", async () => {
    render(<ReorderTable recommendations={RECS} />);

    await userEvent.click(screen.getByRole("button", { name: /Segera reorder/i }));

    expect(screen.getByText("m1")).toBeDefined();
    expect(screen.queryByText("m2")).toBeNull();
    expect(screen.queryByText("m3")).toBeNull();
  });

  it("menampilkan pesan kosong saat filter tanpa hasil", async () => {
    render(<ReorderTable recommendations={[RECS[0]]} />);

    await userEvent.click(screen.getByRole("button", { name: /Kelebihan stok/i }));

    expect(screen.getByText(/Tidak ada rekomendasi/i)).toBeDefined();
  });
});

describe("ReorderTable — Fase 11 (buffer, EOQ, status data)", () => {
  it("menampilkan buffer stock, EOQ + metode, dan peringatan data kurang", async () => {
    const { render, screen } = await import("@testing-library/react");
    const { ReorderTable } = await import("@/components/dashboard/ReorderTable");
    render(
      <ReorderTable
        recommendations={[
          {
            material_id: "m1", safety_stock: "47.8", reorder_point: "126.8", recommended_order_qty: "200",
            status: "urgent", buffer_stock: "9", waste_factor: "1.03", eoq_qty: "4473", eoq_method: "classic",
            item_status: "COMPLETED", stock_source: "snapshot", current_stock_used: "0",
          },
          {
            material_id: "m2", safety_stock: "1", reorder_point: "2", recommended_order_qty: "0",
            status: "safe", buffer_stock: "0", eoq_qty: "100", eoq_method: "dynamic",
            item_status: "MISSING_UNIT_PRICE", stock_source: "request", current_stock_used: "10",
          },
        ]}
      />,
    );
    // CR v3.6 §6 — Buffer & EOQ pindah ke Rincian (kolom bisa ditampilkan lewat menu Kolom)
    expect(screen.queryByRole("columnheader", { name: /buffer/i })).toBeNull();
    expect(screen.getByText(/harga material belum diisi/i)).toBeDefined(); // di kolom Status
    expect(screen.getAllByText(/stok erp/i).length).toBeGreaterThan(0);
    await userEvent.click(screen.getByRole("button", { name: "Rincian m1" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/1,03 \(3\.0%\)/)).toBeDefined();
    expect(within(dialog).getByText(/klasik/i)).toBeDefined();
  });
});

describe("ReorderTable — Fase 11.9 (sumber tunggal titik & qty pesan)", () => {
  it("satu kolom Qty pesan + label kebijakan; EOQ sebagai info; rumus ROP ditampilkan", () => {
    render(
      <ReorderTable
        recommendations={[
          {
            material_id: "m1", safety_stock: "20", reorder_point: "90", recommended_order_qty: "300",
            status: "urgent", eoq_qty: "300", eoq_method: "dynamic",
            rop_formula_used: "standard", order_qty_policy_used: "eoq", order_up_to_level: "160",
          },
          {
            material_id: "m2", safety_stock: "20", reorder_point: "95", recommended_order_qty: "165",
            status: "urgent", eoq_qty: "300", rop_formula_used: "with_buffer",
            order_qty_policy_used: "order_up_to", order_up_to_level: "165",
          },
        ]}
      />,
    );
    expect(screen.getByRole("columnheader", { name: /^qty pesan$/i })).toBeDefined();
    expect(screen.queryByRole("columnheader", { name: /^order qty$/i })).toBeNull();
    expect(screen.queryByRole("columnheader", { name: /eoq \(info\)/i })).toBeNull(); // tersembunyi default
    expect(screen.getByText(/^kelipatan eoq$/i)).toBeDefined();
    expect(screen.getByText(/order-up-to S = 165/i)).toBeDefined();
    expect(screen.getByText("μ·L + SS")).toBeDefined();
    expect(screen.getByText("μ·L + SS + B")).toBeDefined();
  });

  it("rekomendasi lama tanpa kolom kebijakan tetap tampil tanpa label", () => {
    render(<ReorderTable recommendations={[RECS[0]]} />);
    expect(screen.getByText("87")).toBeDefined();
    expect(screen.queryByText(/kelipatan eoq/i)).toBeNull();
  });
});

describe("ReorderTable — override planner", () => {
  const rec: ReorderRecommendation = {
    id: "rec-1", material_id: "m1", safety_stock: "6.6", reorder_point: "46.6",
    recommended_order_qty: "87", status: "urgent",
  };

  it("tanpa onOverride tidak ada kolom aksi", () => {
    render(<ReorderTable recommendations={[rec]} />);
    expect(screen.queryByRole("button", { name: /override/i })).toBeNull();
  });

  it("tombol Override per baris memanggil onOverride dengan rekomendasinya", async () => {
    const onOverride = vi.fn();
    render(<ReorderTable recommendations={[rec]} onOverride={onOverride} />);
    await userEvent.click(screen.getByRole("button", { name: /override m1/i }));
    expect(onOverride).toHaveBeenCalledWith(expect.objectContaining({ id: "rec-1" }), "m1");
  });

  it("rekomendasi tanpa id (respons lama) → tombol nonaktif", () => {
    render(<ReorderTable recommendations={[{ ...rec, id: null }]} onOverride={vi.fn()} />);
    expect((screen.getByRole("button", { name: /override m1/i }) as HTMLButtonElement).disabled).toBe(true);
  });
});

describe("ReorderTable — qty override yang berlaku", () => {
  it("menampilkan qty override + qty sistem sebagai pembanding", () => {
    render(
      <ReorderTable
        recommendations={[{
          id: "rec-1", material_id: "m1", safety_stock: "6.6", reorder_point: "46.6",
          recommended_order_qty: "87", status: "urgent", override_qty: "150", override_reason: "Kontrak supplier",
        }]}
      />,
    );
    expect(screen.getByText("150")).toBeDefined();
    const note = screen.getByText(/override · sistem 87/i);
    expect(note.getAttribute("title")).toMatch(/kontrak supplier/i);
  });
});

// CR v3.5 §5.4 — rincian biaya persediaan per material.
describe("ReorderTable — biaya per material", () => {
  const COSTED: ReorderRecommendation[] = [
    {
      ...RECS[0],
      ordering_cost: "120000", holding_cost: "30000", total_inventory_cost: "150000",
      unit_price_used: "2500", holding_rate_used: "20",
    },
    RECS[1],
  ];

  it("kolom TIC dengan rincian biaya pesan & simpan, plus C dan i yang dipakai", () => {
    render(<ReorderTable recommendations={COSTED} />);

    const row = screen.getByText("m1").closest("tr") as HTMLElement;
    expect(row.textContent).toMatch(/Rp\s?150\.000/);
    expect(row.textContent).toMatch(/Pesan Rp\s?120\.000/);
    expect(row.textContent).toMatch(/Simpan Rp\s?30\.000/);
    expect(row.textContent).toMatch(/C Rp\s?2\.500/);
    expect(row.textContent).toMatch(/i 20%/);
  });

  it("tanpa data biaya → tanda —", () => {
    render(<ReorderTable recommendations={COSTED} />);
    const row = screen.getByText("m2").closest("tr") as HTMLElement;
    expect(screen.getByRole("columnheader", { name: /biaya persediaan/i })).toBeDefined();
    expect(row.textContent).toContain("—");
  });
});


// CR v3.6 §6 — hasil adjust kapasitas & kebijakan reorder terlihat
describe("ReorderTable — adjust kapasitas & service level (CR v3.6 §6)", () => {
  const ADJ: ReorderRecommendation = {
    id: "rec-a", material_id: "m1", safety_stock: "30", reorder_point: "70", recommended_order_qty: "100",
    status: "urgent", safety_stock_system: "48", buffer_stock_system: "9", buffer_stock: "5",
    service_level_effective: "88.5", adjustment_source: "suggested", rop_formula_used: "with_buffer",
  };

  it("SS ter-adjust: nilai baru + nilai sistem tercoret + badge", () => {
    render(<ReorderTable recommendations={[ADJ, RECS[1]]} />);
    const row = screen.getByText("m1").closest("tr") as HTMLElement;
    expect(within(row).getByText("48").tagName).toBe("S");
    expect(within(row).getByText(/disesuaikan kapasitas \(usulan\)/i)).toBeDefined();
  });

  it("service level efektif di bawah target ditandai", () => {
    render(<ReorderTable recommendations={[ADJ]} targetServiceLevel={95} />);
    expect(screen.getByRole("columnheader", { name: /service level efektif/i })).toBeDefined();
    expect(screen.getByText("88,5%").className).toContain("text-destructive");
    expect(screen.getByText(/di bawah 95%/)).toBeDefined();
  });

  it("filter 'Hanya yang disesuaikan'", async () => {
    render(<ReorderTable recommendations={[ADJ, RECS[1]]} />);
    await userEvent.click(screen.getByRole("button", { name: /hanya yang disesuaikan \(1\)/i }));
    expect(screen.getByText("m1")).toBeDefined();
    expect(screen.queryByText("m2")).toBeNull();
  });

  it("tanpa material ter-adjust, filter tidak tampil", () => {
    render(<ReorderTable recommendations={RECS} />);
    expect(screen.queryByRole("button", { name: /hanya yang disesuaikan/i })).toBeNull();
  });

  it("satuan material ikut di qty (CR v3.6 §8.7)", () => {
    render(
      <ReorderTable
        recommendations={[ADJ]}
        materials={[{ id: "m1", code: "BTL", name: "Botol", category: null, unit: "pcs", lead_time_days: 7, moq: "0", manual_safety_stock: null }]}
      />,
    );
    expect(screen.getByText("30 pcs")).toBeDefined();
  });
});

describe("ReorderDetail — semua field ReorderRecommendation tampil (CR v3.6 §6)", () => {
  const FULL: Required<ReorderRecommendation> = {
    id: "rec-1", material_id: "m1", safety_stock: "30", reorder_point: "70", recommended_order_qty: "100",
    status: "urgent", buffer_stock: "5", waste_factor: "1.05", eoq_qty: "400", eoq_method: "classic",
    item_status: "MISSING_HOLDING_RATE", annual_demand: "1200", current_stock_used: "12", stock_source: "snapshot",
    rop_formula_used: "with_buffer", order_qty_policy_used: "order_up_to", order_up_to_level: "180", moq_used: "50",
    override_qty: "150", override_reason: "Kontrak supplier", override_at: "2026-11-20T08:00:00Z",
    safety_stock_system: "48", buffer_stock_system: "9", service_level_effective: "88.5",
    adjustment_source: "custom", ordering_cost: "120000", holding_cost: "30000", total_inventory_cost: "150000",
    unit_price_used: "2500", holding_rate_used: "20",
    mu_period: "310", sigma_period: "42.5", period_days: "31", lead_time_days_used: "7", z_value: "1.6449",
    service_level_pct_used: "95", eoq_raw_qty: "377.3", ordering_cost_per_order: "250000", holding_cost_per_unit: "15",
  };

  // Label/nilai yang mewakili tiap field — bila field baru ditambah ke tipe, tambahkan di sini.
  const EXPECTED: Record<keyof ReorderRecommendation, RegExp> = {
    id: /override planner/i, // id = target override → bagian override
    material_id: /stok dipakai/i, // judul Sheet memakai label material
    safety_stock: /^30$/,
    reorder_point: /^70$/,
    recommended_order_qty: /^100$/,
    status: /^urgent$/,
    buffer_stock: /^5$/,
    waste_factor: /1,05 \(5\.0%\)/,
    eoq_qty: /^400$/,
    eoq_method: /klasik/i,
    item_status: /i \(%\) template biaya belum diisi/i,
    annual_demand: /1\.200/,
    current_stock_used: /^12$/,
    stock_source: /stok erp/i,
    rop_formula_used: /μ·L \+ SS \+ B/,
    order_qty_policy_used: /order-up-to$/i,
    order_up_to_level: /^180$/,
    moq_used: /^50$/,
    override_qty: /^150$/,
    override_reason: /kontrak supplier/i,
    override_at: /2026/,
    safety_stock_system: /^48$/,
    buffer_stock_system: /^9$/,
    service_level_effective: /88,5%/,
    adjustment_source: /kustom planner/i,
    ordering_cost: /120\.000/,
    holding_cost: /30\.000/,
    total_inventory_cost: /150\.000/,
    unit_price_used: /2\.500/,
    holding_rate_used: /^20%$/,
    mu_period: /^310$/,
    sigma_period: /^42,5$/,
    period_days: /^31 hari$/,
    lead_time_days_used: /^7 hari$/,
    z_value: /^1,6449$/,
    service_level_pct_used: /^95%$/,
    eoq_raw_qty: /^377,3$/,
    ordering_cost_per_order: /250\.000/,
    holding_cost_per_unit: /^Rp 15$/,
  };

  it.each(Object.entries(EXPECTED))("%s", async (_field, pattern) => {
    const { ReorderDetail } = await import("@/components/dashboard/ReorderDetail");
    const { container } = render(<ReorderDetail rec={FULL} />);
    const nodes = [...container.querySelectorAll("dd, dt, s, span, div")];
    const texts = nodes.flatMap((e) => [
      e.textContent?.trim() ?? "",
      // nilai utama berdampingan dengan subteks di elemen yang sama → cek tiap text node
      ...[...e.childNodes].filter((n) => n.nodeType === Node.TEXT_NODE).map((n) => n.textContent?.trim() ?? ""),
    ]);
    expect(texts.some((t) => pattern.test(t))).toBe(true);
  });
});
