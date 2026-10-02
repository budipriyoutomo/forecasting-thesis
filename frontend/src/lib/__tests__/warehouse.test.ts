import { describe, expect, it } from "vitest";

import { computeEffectiveCapacity, isDusLike } from "@/lib/warehouse";

// Cermin warehouse_service.compute_effective_capacity (backend) — angka sama
// dengan test backend, diverifikasi manual.
describe("isDusLike", () => {
  it("mengenali DUS/KARTON/BOX/CTN tanpa peduli huruf & spasi", () => {
    expect(isDusLike("dus")).toBe(true);
    expect(isDusLike(" Karton ")).toBe(true);
    expect(isDusLike("box")).toBe(true);
    expect(isDusLike("CTN")).toBe(true);
    expect(isDusLike("PCS")).toBe(false);
  });
});

describe("computeEffectiveCapacity", () => {
  it("mode DUS, unit dus → dus = unit produk", () => {
    expect(
      computeEffectiveCapacity({ capacity_mode: "DUS", pallet_qty: 9, dus_qty: 500, dus_per_pallet: 60, pcs_per_dus: null }, "DUS"),
    ).toEqual({ dus: 500, qty: 500 });
  });

  it("mode PALLET mengabaikan dus lepas", () => {
    expect(
      computeEffectiveCapacity({ capacity_mode: "PALLET", pallet_qty: 10, dus_qty: 99, dus_per_pallet: 60, pcs_per_dus: null }, "Karton"),
    ).toEqual({ dus: 600, qty: 600 });
  });

  it("mode kombinasi, unit PCS: (10 × 60 + 25) × 24 = 15.000", () => {
    expect(
      computeEffectiveCapacity({ capacity_mode: "COMBINED", pallet_qty: 10, dus_qty: 25, dus_per_pallet: 60, pcs_per_dus: 24 }, "PCS"),
    ).toEqual({ dus: 625, qty: 15000 });
  });

  it("null bila input belum lengkap (dus/pallet atau pcs/dus kosong)", () => {
    expect(
      computeEffectiveCapacity({ capacity_mode: "PALLET", pallet_qty: 10, dus_qty: 0, dus_per_pallet: null, pcs_per_dus: null }, "DUS"),
    ).toBeNull();
    expect(
      computeEffectiveCapacity({ capacity_mode: "DUS", pallet_qty: 0, dus_qty: 10, dus_per_pallet: null, pcs_per_dus: null }, "PCS"),
    ).toBeNull();
  });
});
