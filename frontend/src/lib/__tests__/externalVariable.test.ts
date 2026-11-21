import { describe, expect, it } from "vitest";

import { exogUsage, importSummary, valueChanges } from "@/lib/externalVariable";

// CR v3.4 §4.1 — planner harus tahu bila periode dinormalisasi / baris ganda ditimpa.
describe("importSummary", () => {
  it("hanya jumlah diimpor bila tidak ada normalisasi", () => {
    expect(importSummary({ imported: 3, normalized: 0, overwritten: 0 })).toBe("3 nilai diimpor");
  });

  it("menyebut periode yang dinormalisasi dan baris yang ditimpa", () => {
    expect(importSummary({ imported: 2, normalized: 3, overwritten: 2 })).toBe(
      "2 nilai diimpor · 3 periode digeser ke awal bulan · 2 baris ganda (bulan sama) ditimpa baris terakhir",
    );
  });

  it("menyebut sel yang dilewati per variabel (CR v3.4 §4.3)", () => {
    expect(importSummary({ imported: 5, normalized: 0, overwritten: 0, skipped: { suhu: 2, inflasi: 1 } })).toBe(
      "5 nilai diimpor · 3 sel kosong dilewati (suhu 2, inflasi 1)",
    );
  });

  it("menerima respons lama tanpa field normalisasi", () => {
    expect(importSummary({ imported: 1 })).toBe("1 nilai diimpor");
  });
});

// CR v3.4 §4.2 — variabel eksternal yang dipakai / di-drop engine ML.
describe("exogUsage", () => {
  it("null bila hyperparameters tidak punya info exog (metode non-ML)", () => {
    expect(exogUsage(null)).toBeNull();
    expect(exogUsage({ window: 3 })).toBeNull();
  });

  it("null bila tidak ada variabel eksternal sama sekali", () => {
    expect(exogUsage({ exog_used: [], exog_dropped: {} })).toBeNull();
  });

  it("format baru: dict kode → alasan", () => {
    expect(
      exogUsage({ exog_used: ["suhu"], exog_dropped: { promo: "missing_horizon", natal: "constant" } }),
    ).toEqual({
      used: ["suhu"],
      dropped: [
        { code: "promo", reason: "Nilai horizon belum lengkap" },
        { code: "natal", reason: "Nilai tidak bervariasi di histori" },
      ],
      total: 3,
    });
  });

  it("format lama: list kode tanpa alasan", () => {
    expect(exogUsage({ exog_used: [], exog_dropped: ["suhu"] })).toEqual({
      used: [],
      dropped: [{ code: "suhu", reason: "Alasan tidak tercatat (forecast lama)" }],
      total: 1,
    });
  });
});

// 21 Nov 2026 — ubah nilai per periode dari dialog "Ubah".
describe("valueChanges", () => {
  const base = { product_id: null, original: null as string | null };

  it("hanya mengirim baris yang berubah atau baru; koma desimal diterima", () => {
    const r = valueChanges(
      [
        { ...base, period: "2026-01-01", value: "30", original: "30" },
        { ...base, period: "2026-02-01", value: "31,5", original: "30" },
        { ...base, period: "2026-03", value: "29" },
      ],
      { value_type: "numeric", scope: "global" },
    );
    expect(r.errors).toEqual([]);
    expect(r.items).toEqual([
      { period: "2026-02-01", value: 31.5, product_id: null },
      { period: "2026-03-01", value: 29, product_id: null },
    ]);
  });

  it("melaporkan nilai kosong/bukan angka, flag selain 0/1, periode & produk kosong", () => {
    const r = valueChanges(
      [
        { ...base, period: "2026-01-01", value: "abc", product_id: "p1" },
        { ...base, period: "2026-02-01", value: "2", product_id: "p1" },
        { ...base, period: "", value: "1", product_id: "p1" },
        { ...base, period: "2026-04-01", value: "" },
      ],
      { value_type: "flag", scope: "product" },
    );
    expect(r.items).toEqual([]);
    expect(r.errors).toHaveLength(4);
    expect(r.errors.join(" ")).toMatch(/bukan angka/);
    expect(r.errors.join(" ")).toMatch(/0 atau 1/);
    expect(r.errors.join(" ")).toMatch(/Periode wajib/);
    expect(r.errors.join(" ")).toMatch(/Produk wajib/);
  });

  it("baris kosong yang belum disentuh diabaikan", () => {
    const r = valueChanges([{ ...base, period: "", value: "" }], { value_type: "numeric", scope: "global" });
    expect(r).toEqual({ items: [], errors: [] });
  });
});
