import { describe, expect, it } from "vitest";

import { defaultStep, deriveRunSteps } from "@/lib/runSteps";

const run = (over: Partial<Parameters<typeof deriveRunSteps>[0]["run"]> = {}) => ({
  status: "COMPLETED" as const,
  n_products: 5,
  n_completed: 5,
  n_failed: 0,
  n_pending_selection: 0,
  ...over,
});

describe("deriveRunSteps (CR v3.6 §4 — status dari data run, bukan state lokal)", () => {
  it("run selesai, semua metode dipilih, belum perencanaan → langkah 3 aktif", () => {
    const steps = deriveRunSteps({ run: run(), hasPlanning: false });
    expect(steps.map((s) => s.status)).toEqual(["done", "done", "todo", "locked", "locked"]);
    expect(steps[3].key).toBe("evaluation");
    expect(steps[3].lockedReason).toMatch(/jalankan perencanaan/i);
    expect(steps[4].lockedReason).toMatch(/jalankan perencanaan/i);
    expect(defaultStep(steps)).toBe("planning");
  });

  it("masih ada produk belum dipilih → langkah 2 todo dengan jumlahnya", () => {
    const steps = deriveRunSteps({ run: run({ n_pending_selection: 3 }), hasPlanning: false });
    expect(steps[1].status).toBe("todo");
    expect(steps[1].hint).toMatch(/3 produk/);
    // sebagian sudah dipilih → perencanaan boleh, produk belum dipilih dilewati
    expect(steps[2].status).toBe("todo");
    expect(defaultStep(steps)).toBe("select");
  });

  it("belum ada satu pun metode dipilih → perencanaan terkunci dengan alasan", () => {
    const steps = deriveRunSteps({ run: run({ n_pending_selection: 5 }), hasPlanning: false });
    expect(steps[2].status).toBe("locked");
    expect(steps[2].lockedReason).toBe("Pilih metode untuk 5 produk dulu.");
  });

  it("semua produk gagal → pilih metode terkunci", () => {
    const steps = deriveRunSteps({ run: run({ n_completed: 0, n_failed: 5 }), hasPlanning: false });
    expect(steps[1].status).toBe("locked");
    expect(steps[1].lockedReason).toMatch(/tidak ada produk/i);
    expect(steps[2].status).toBe("locked");
  });

  it("sudah perencanaan → semua selesai, evaluasi setelah perencanaan, default ke Reorder & gudang", () => {
    const steps = deriveRunSteps({ run: run(), hasPlanning: true });
    expect(steps.map((s) => s.key)).toEqual(["forecast", "select", "planning", "evaluation", "reorder"]);
    expect(steps.map((s) => s.status)).toEqual(["done", "done", "done", "done", "done"]);
    expect(defaultStep(steps)).toBe("reorder");
  });

  it("run belum selesai → hanya langkah 1", () => {
    const steps = deriveRunSteps({ run: run({ status: "PROCESSING" }), hasPlanning: false });
    expect(steps.map((s) => s.status)).toEqual(["todo", "locked", "locked", "locked", "locked"]);
  });
});
