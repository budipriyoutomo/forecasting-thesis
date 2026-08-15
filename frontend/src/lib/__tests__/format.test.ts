import { describe, expect, it } from "vitest";

import { formatDate, formatMoney, formatNumber, formatPercent } from "@/lib/format";

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
