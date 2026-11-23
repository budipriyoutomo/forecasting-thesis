import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MethodForecastMatrix } from "@/components/forecast/method-view/MethodForecastMatrix";

import { COMPARISON, variantLabel } from "./fixture";

const [RF, LSTM] = COMPARISON.methods;

describe("MethodForecastMatrix (CR v3.7 §4.2)", () => {
  it("header Varian + Jan-26 … Des-26 + Total", () => {
    render(<MethodForecastMatrix method={RF} periods={COMPARISON.periods} variantLabel={variantLabel} />);
    const headers = screen.getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers[0]).toBe("Varian");
    expect(headers[1]).toBe("Jan-26");
    expect(headers[12]).toBe("Des-26");
    expect(headers[13]).toBe("Total");
  });

  it("baris = kode varian, qty bilangan bulat rata kanan, Total dari backend", () => {
    render(<MethodForecastMatrix method={RF} periods={COMPARISON.periods} variantLabel={variantLabel} />);
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows.map((r) => within(r).getAllByRole("cell")[0].textContent)).toEqual(["PL", "SB", "BB"]);
    const cells = within(rows[0]).getAllByRole("cell");
    expect(cells[1].textContent).toBe("1.000"); // 1000.4 → bilangan bulat
    expect(cells[1].className).toMatch(/text-right/);
    expect(cells[1].className).toMatch(/tabular-nums/);
    expect(cells[13].textContent).toBe(Math.round(RF.rows[0].total as number).toLocaleString("id-ID"));
  });

  it("kolom Varian sticky & tabel bisa digulir horizontal", () => {
    const { container } = render(
      <MethodForecastMatrix method={RF} periods={COMPARISON.periods} variantLabel={variantLabel} />,
    );
    expect(screen.getAllByRole("cell")[0].className).toMatch(/sticky/);
    expect(container.querySelector(".overflow-x-auto")).not.toBeNull();
  });

  it("FAILED → — dengan keterangan; NO_SERIES → — dengan keterangan run lama", () => {
    render(<MethodForecastMatrix method={LSTM} periods={COMPARISON.periods} variantLabel={variantLabel} />);
    expect(screen.getAllByLabelText("Metode gagal untuk varian ini").length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText("Run lama: deret per metode tidak disimpan").length).toBeGreaterThan(0);
    const sb = screen.getAllByRole("row").find((r) => r.textContent?.startsWith("SB"))!;
    expect(within(sb).getAllByRole("cell")[1].textContent).toBe("—");
  });
});
