import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CopyTableButton, toTsv } from "@/components/forecast/method-view/CopyTableButton";
import { MethodForecastMatrix } from "@/components/forecast/method-view/MethodForecastMatrix";
import { MethodMetricsTable } from "@/components/forecast/method-view/MethodMetricsTable";
import { BestMethodAnalysis } from "@/components/forecast/method-view/BestMethodAnalysis";

import { COMPARISON, variantLabel } from "./fixture";

const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));
vi.mock("sonner", () => ({ toast }));

let writeText: ReturnType<typeof vi.fn>;
beforeEach(() => {
  toast.success.mockReset();
  toast.error.mockReset();
  writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
});

describe("toTsv (CR v3.7 D1)", () => {
  it("tab antar kolom, newline antar baris; tab/newline di sel jadi spasi", () => {
    expect(toTsv([["Varian", "Jan-26"], ["PL", "1.000"], ["a\tb", "c\nd"]])).toBe("Varian\tJan-26\nPL\t1.000\na b\tc d");
  });
});

describe("CopyTableButton", () => {
  it("salin TSV ke clipboard + toast sukses", async () => {
    render(<CopyTableButton label="hasil ramalan" rows={() => [["A", "B"], ["1", "2"]]} />);
    await userEvent.click(screen.getByRole("button", { name: /salin hasil ramalan/i }));
    expect(writeText).toHaveBeenCalledWith("A\tB\n1\t2");
    expect(toast.success).toHaveBeenCalled();
  });

  it("clipboard gagal → toast error", async () => {
    writeText.mockRejectedValue(new Error("ditolak"));
    render(<CopyTableButton label="x" rows={() => [["A"]]} />);
    await userEvent.click(screen.getByRole("button", { name: /salin x/i }));
    expect(toast.error).toHaveBeenCalled();
  });

  it("matriks hasil ramalan: header periode, qty bulat, — untuk gagal", async () => {
    const [, LSTM] = COMPARISON.methods;
    render(<MethodForecastMatrix method={LSTM} periods={COMPARISON.periods} variantLabel={variantLabel} />);
    await userEvent.click(screen.getByRole("button", { name: /salin hasil ramalan lstm/i }));
    const lines = (writeText.mock.calls[0][0] as string).split("\n");
    expect(lines[0].split("\t").slice(0, 2)).toEqual(["Varian", "Jan-26"]);
    expect(lines[0].split("\t").at(-1)).toBe("Total");
    expect(lines[1].split("\t")[1]).toBe("1.000");
    expect(lines[2].split("\t")[1]).toBe("—");
  });

  it("tabel pengujian: metrik tanpa label Lewis + baris Average", async () => {
    const [RF] = COMPARISON.methods;
    render(<MethodMetricsTable method={RF} criteria={COMPARISON.criteria} variantLabel={variantLabel} />);
    await userEvent.click(screen.getByRole("button", { name: /salin pengujian peramalan random forest/i }));
    const lines = (writeText.mock.calls[0][0] as string).split("\n");
    expect(lines[0]).toBe("Varian\tMAD\tMAPE\tMFE");
    expect(lines[1]).toBe("PL\t10.00\t5.00%\t-1.00");
    expect(lines.at(-1)).toBe("Average\t5.00\t5.33%\t0.00");
  });

  it("tabel peringkat analisis bisa disalin", async () => {
    render(
      <BestMethodAnalysis
        selection={COMPARISON.run_selection}
        criteria={COMPARISON.criteria}
        productMethods={COMPARISON.product_methods}
        variantLabel={variantLabel}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /salin peringkat metode/i }));
    const lines = (writeText.mock.calls[0][0] as string).split("\n");
    expect(lines[0]).toBe("Peringkat\tMetode\tAvg MAD\tAvg MAPE\tAvg MFE\tVarian");
    expect(lines[1]).toBe("1\tRandom Forest\t5.00\t5.33%\t0.00\t3");
  });
});
