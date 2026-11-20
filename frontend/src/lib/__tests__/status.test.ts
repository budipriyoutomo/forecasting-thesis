import { describe, expect, it } from "vitest";

import { resultStatus, runStatus } from "@/lib/status";

describe("lib/status (CR v3.6 §8.6 — satu peta label status)", () => {
  it("status run dalam Bahasa Indonesia", () => {
    expect(runStatus("COMPLETED")).toEqual({ label: "Selesai", variant: "success" });
    expect(runStatus("PROCESSING").label).toBe("Diproses");
    expect(runStatus("FAILED").variant).toBe("destructive");
  });

  it("status hasil per produk, termasuk menunggu pemilihan", () => {
    expect(resultStatus({ status: "COMPLETED", selection_status: "SELECTED" }).label).toBe("Selesai");
    expect(resultStatus({ status: "COMPLETED", selection_status: "PENDING_SELECTION" })).toEqual({
      label: "Belum dipilih",
      variant: "warning",
    });
    expect(resultStatus({ status: "INSUFFICIENT_DATA" }).label).toBe("Data kurang");
    expect(resultStatus({ status: "MODEL_SELECTION_FAILED" }).label).toBe("Semua metode gagal");
  });

  it("status tak dikenal tampil apa adanya", () => {
    expect(runStatus("WEIRD")).toEqual({ label: "WEIRD", variant: "outline" });
  });
});
