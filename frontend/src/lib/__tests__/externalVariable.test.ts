import { describe, expect, it } from "vitest";

import { exogUsage, importSummary } from "@/lib/externalVariable";

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
