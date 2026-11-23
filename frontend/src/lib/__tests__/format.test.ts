import { describe, expect, it } from "vitest";

import {
  formatDate,
  formatDateTime,
  formatMoney,
  formatNumber,
  formatPercent,
  formatPeriodLabel,
  formatQty,
} from "@/lib/format";

// Nilai Decimal datang dari backend sebagai string (AGENTS.md §4), jadi formatter
// wajib menerima string apa adanya tanpa pemanggil perlu mengonversi lebih dulu.
describe("formatNumber", () => {
  it("memformat string Decimal backend ke notasi id-ID", () => {
    expect(formatNumber("22400.0000")).toBe("22.400");
    expect(formatNumber("4910.4000")).toBe("4.910,4");
  });

  it("menerima number", () => {
    expect(formatNumber(148800)).toBe("148.800");
  });

  it("membatasi 2 angka di belakang koma", () => {
    expect(formatNumber("1234.56789")).toBe("1.234,57");
  });

  it("mengembalikan em dash untuk nilai kosong", () => {
    expect(formatNumber(null)).toBe("—");
    expect(formatNumber(undefined)).toBe("—");
    expect(formatNumber("")).toBe("—");
  });

  it("mengembalikan em dash untuk nilai bukan angka, bukan NaN", () => {
    expect(formatNumber("abc")).toBe("—");
  });

  it("nol tetap ditampilkan, bukan dianggap kosong", () => {
    expect(formatNumber(0)).toBe("0");
    expect(formatNumber("0.0000")).toBe("0");
  });
});

describe("formatPercent", () => {
  it("menambahkan tanda persen", () => {
    expect(formatPercent("5.00")).toBe("5%");
    expect(formatPercent("18.99")).toBe("18,99%");
  });

  it("mengembalikan em dash untuk nilai kosong", () => {
    expect(formatPercent(null)).toBe("—");
  });
});

describe("formatMoney", () => {
  it("memformat rupiah tanpa angka desimal", () => {
    expect(formatMoney("160730000.00")).toBe("Rp 160.730.000");
  });

  it("mengembalikan em dash untuk nilai kosong", () => {
    expect(formatMoney(null)).toBe("—");
  });

  it("bisa menampilkan desimal untuk biaya per unit kecil", () => {
    expect(formatMoney("181.2500", 2)).toBe("Rp 181,25");
  });
});

describe("formatDate", () => {
  it("memformat tanggal ISO ke format pendek id-ID", () => {
    expect(formatDate("2026-08-09T08:12:00Z")).toBe("9 Agu 2026");
  });

  it("mengembalikan em dash untuk nilai kosong atau tidak valid", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate("bukan tanggal")).toBe("—");
  });
});

// CR v3.6 §8.7 — qty selalu dengan satuan
describe("formatQty", () => {
  it("angka + UoM", () => {
    expect(formatQty("1200.5000", "kg")).toBe("1.200,5 kg");
    expect(formatQty(3, "PCS")).toBe("3 PCS");
  });

  it("tanpa UoM → angka saja; null → —", () => {
    expect(formatQty(3, null)).toBe("3");
    expect(formatQty(null, "kg")).toBe("—");
  });
});

describe("formatDateTime", () => {
  it("tanggal + jam id-ID; null → —", () => {
    expect(formatDateTime("2026-11-20T08:30:00Z")).toMatch(/2026/);
    expect(formatDateTime(null)).toBe("—");
  });
});

// CR v3.7 D5 — label kolom periode format thesis, locale id-ID
describe("formatPeriodLabel", () => {
  it("MMM-yy bahasa Indonesia", () => {
    expect(formatPeriodLabel("2026-01-01")).toBe("Jan-26");
    expect(formatPeriodLabel("2026-05-01")).toBe("Mei-26");
    expect(formatPeriodLabel("2026-08-01")).toBe("Agu-26");
    expect(formatPeriodLabel("2026-12-01")).toBe("Des-26");
  });

  it("tidak bergeser zona waktu & menerima datetime ISO", () => {
    expect(formatPeriodLabel("2027-01-01T00:00:00")).toBe("Jan-27");
  });

  it("nilai tidak valid → apa adanya; kosong → —", () => {
    expect(formatPeriodLabel("bukan tanggal")).toBe("bukan tanggal");
    expect(formatPeriodLabel("")).toBe("—");
  });
});
