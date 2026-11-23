import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CandidatesTable } from "@/components/forecast/CandidatesTable";
import type { ForecastCandidate } from "@/types/forecast";

const POINT = [{ date: "2026-09-01", value: 100, lower: 90, upper: 110 }];

const candidates: ForecastCandidate[] = [
  { method: "moving_average", mad: 12.5, mfe: -2.1, mse: 240.4, mape: 11.42, mase: 0.98, forecast: POINT },
  { method: "xgboost", mad: 8.2, mfe: 0.4, mse: 120.9, mape: 8.2, mase: 0.71, forecast: POINT },
  { method: "random_forest", mad: 9.9, mfe: 1.2, mse: 160.2, mape: 9.75, mase: null, forecast: POINT },
];

const ALL = ["mad", "mfe", "mape"] as const;

async function buka() {
  await userEvent.click(screen.getByRole("button", { name: /perbandingan metode/i }));
}

describe("CandidatesTable (Fase 11.15 — run lama tanpa peringkat)", () => {
  it("menyembunyikan detail sampai dibuka bila metode sudah dipilih", () => {
    render(<CandidatesTable candidates={candidates} selectedMethod="xgboost" displayMetrics={[...ALL]} />);

    expect(screen.getByRole("button", { name: /perbandingan metode \(3 metode\)/i })).toBeDefined();
    expect(screen.queryByText("moving_average")).toBeNull();
  });

  it("langsung terbuka bila metode belum dipilih", () => {
    render(
      <CandidatesTable candidates={candidates} selectedMethod={null} displayMetrics={[...ALL]} onSelect={vi.fn()} />,
    );

    expect(screen.getByText("moving_average")).toBeDefined();
  });

  it("hanya kolom metrik yang dicentang, tanpa kolom rank", async () => {
    render(<CandidatesTable candidates={candidates} selectedMethod="xgboost" displayMetrics={["mad", "mape"]} />);
    await buka();

    const headers = screen.getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual(["Metode", "MAD", "MAPE"]);
    expect(screen.queryByText(/rank/i)).toBeNull();
    expect(screen.getByText("11.42%")).toBeDefined();
    expect(screen.queryByText("240.40")).toBeNull(); // MSE bukan metrik tampil
  });

  it("MFE ditampilkan bertanda (arah bias)", async () => {
    render(<CandidatesTable candidates={candidates} selectedMethod="xgboost" displayMetrics={["mfe"]} />);
    await buka();

    expect(screen.getByText("-2.10")).toBeDefined();
  });

  it("urutan kandidat tidak diurutkan menurut metrik (tidak ada penilaian)", async () => {
    render(<CandidatesTable candidates={candidates} selectedMethod="xgboost" displayMetrics={[...ALL]} />);
    await buka();

    const rows = screen.getAllByRole("row").slice(1);
    expect(rows.map((r) => within(r).getAllByRole("cell")[0].textContent)).toEqual([
      "moving_average",
      "xgboostdipakai",
      "random_forest",
    ]);
  });

  it("tombol Pilih memanggil onSelect dengan metodenya", async () => {
    const onSelect = vi.fn();
    render(
      <CandidatesTable candidates={candidates} selectedMethod="xgboost" displayMetrics={[...ALL]} onSelect={onSelect} />,
    );
    await buka();

    expect(screen.queryByRole("button", { name: /pilih xgboost/i })).toBeNull(); // sudah dipakai
    await userEvent.click(screen.getByRole("button", { name: /pilih random_forest/i }));

    expect(onSelect).toHaveBeenCalledWith("random_forest");
  });

  it("kandidat tanpa deret forecast (run lama) tidak bisa dipilih", async () => {
    const old = candidates.map(({ forecast: _f, ...c }) => c);
    render(<CandidatesTable candidates={old} selectedMethod="xgboost" displayMetrics={[...ALL]} onSelect={vi.fn()} />);
    await buka();

    expect(screen.queryByRole("button", { name: /^pilih /i })).toBeNull();
  });

  it("mode manual (satu kandidat, tanpa onSelect) tidak menampilkan tabel", () => {
    const { container } = render(
      <CandidatesTable candidates={[candidates[0]]} selectedMethod="moving_average" displayMetrics={[...ALL]} />,
    );

    expect(container.innerHTML).toBe("");
  });
});


describe("CandidatesTable — hanya MAD, MFE, MAPE + tooltip (21 Nov 2026)", () => {
  it("MSE & MASE tidak pernah tampil, walau ada di pengaturan lama", async () => {
    const rows = [
      ...candidates,
      { method: "lstm", mad: 1, mfe: 0, mse: 1, mape: 30, mase: 1.3, forecast: POINT },
    ];
    render(
      <CandidatesTable candidates={rows} selectedMethod="xgboost" displayMetrics={["mase", "mse", "mape"] as never} />,
    );
    await buka();

    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Metode", "MAPE"]);
    expect(screen.queryByText(/naive/i)).toBeNull();
    expect(screen.getByText("Cukup")).toBeDefined(); // label MAPE Lewis 30%
  });

  it("setiap header metrik punya tombol definisi", async () => {
    render(<CandidatesTable candidates={candidates} selectedMethod="xgboost" displayMetrics={[...ALL]} />);
    await buka();

    for (const label of ["MAD", "MFE", "MAPE"]) {
      expect(screen.getByRole("button", { name: `Definisi ${label}` })).toBeDefined();
    }
    await userEvent.hover(screen.getByRole("button", { name: "Definisi MFE" }));
    expect((await screen.findAllByText(/bias/i)).length).toBeGreaterThan(0);
  });
});


describe("CandidatesTable — peringkat metode terbaik (23 Nov 2026)", () => {
  const ranked: ForecastCandidate[] = [
    { ...candidates[1], rank: 1 },
    { ...candidates[2], rank: 2 },
    { ...candidates[0], rank: 3 },
  ];

  it("kolom Peringkat + badge terbaik pada peringkat 1", async () => {
    render(<CandidatesTable candidates={ranked} selectedMethod="xgboost" displayMetrics={["mad"]} />);
    await buka();

    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Peringkat", "Metode", "MAD"]);
    const first = screen.getAllByRole("row")[1];
    expect(within(first).getByText("terbaik")).toBeDefined();
    expect(within(first).getAllByRole("cell")[0].textContent).toBe("1");
  });

  it("badge terbaik tetap di peringkat 1 walau planner memakai metode lain", async () => {
    render(<CandidatesTable candidates={ranked} selectedMethod="moving_average" displayMetrics={["mad"]} />);
    await buka();

    const rows = screen.getAllByRole("row").slice(1);
    expect(within(rows[0]).getByText("terbaik")).toBeDefined();
    expect(within(rows[2]).getByText("dipakai")).toBeDefined();
  });
});
