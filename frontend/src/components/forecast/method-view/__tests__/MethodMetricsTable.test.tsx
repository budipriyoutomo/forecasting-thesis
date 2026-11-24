import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MethodMetricsTable } from "@/components/forecast/method-view/MethodMetricsTable";

import { COMPARISON, variantLabel } from "./fixture";

const [RF, LSTM] = COMPARISON.methods;

describe("MethodMetricsTable (CR v3.7 §4.2)", () => {
  it("urutan kolom Varian · MAD · MAPE · MFE (dari criteria backend)", () => {
    render(<MethodMetricsTable method={RF} criteria={COMPARISON.criteria} variantLabel={variantLabel} />);
    const headers = screen.getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual(["Varian", "MAD", "MAPE", "MFE"]);
  });

  it("nilai per varian + baris Average dari backend", () => {
    render(<MethodMetricsTable method={RF} criteria={COMPARISON.criteria} variantLabel={variantLabel} />);
    const pl = screen.getAllByRole("row").find((r) => r.textContent?.startsWith("PL"))!;
    expect(within(pl).getAllByRole("cell")[1].textContent).toBe("10.00");
    expect(within(pl).getAllByRole("cell")[3].textContent).toBe("-1.00");
    const avg = screen.getAllByRole("row").find((r) => r.textContent?.startsWith("Average"))!;
    expect(within(avg).getAllByRole("cell")[1].textContent).toBe("5.00");
    expect(within(avg).getAllByRole("cell")[3].textContent).toBe("0.00");
    expect(screen.queryByText(/n = /)).toBeNull(); // semua varian berhasil
  });

  it("varian gagal → — dan catatan n = x dari y varian", () => {
    render(<MethodMetricsTable method={LSTM} criteria={COMPARISON.criteria} variantLabel={variantLabel} />);
    expect(screen.getByText("n = 2 dari 3 varian")).toBeDefined();
    const sb = screen.getAllByRole("row").find((r) => r.textContent?.startsWith("SB"))!;
    expect(within(sb).getAllByLabelText("Metode gagal untuk varian ini")).toHaveLength(3); // satu per metrik
  });

  it("varian gagal dengan alasan dari backend → tooltip memakai alasan itu", () => {
    const reason = "TensorFlow belum terpasang di server.";
    const method = { ...LSTM, rows: LSTM.rows.map((r) => (r.status === "FAILED" ? { ...r, reason } : r)) };
    render(<MethodMetricsTable method={method} criteria={COMPARISON.criteria} variantLabel={variantLabel} />);
    const sb = screen.getAllByRole("row").find((r) => r.textContent?.startsWith("SB"))!;
    expect(within(sb).getAllByLabelText(reason)).toHaveLength(3);
  });

  it("kolom mengikuti criteria (metrik tidak dicentang tidak tampil)", () => {
    render(<MethodMetricsTable method={RF} criteria={["mad", "mfe"]} variantLabel={variantLabel} />);
    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Varian", "MAD", "MFE"]);
  });
});
