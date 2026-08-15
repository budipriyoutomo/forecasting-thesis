import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { CandidatesTable } from "@/components/forecast/CandidatesTable";
import type { ForecastCandidate } from "@/types/forecast";

const candidates: ForecastCandidate[] = [
  { method: "moving_average", mad: 12.5, mfe: -2.1, mse: 240.4, mape: 11.42, mase: 0.98 },
  { method: "xgboost", mad: 8.2, mfe: 0.4, mse: 120.9, mape: 8.2, mase: 0.71 },
  { method: "random_forest", mad: 9.9, mfe: 1.2, mse: 160.2, mape: 9.75, mase: null },
];

// Perbandingan sekarang dibungkus Collapsible: isinya baru dipasang ke DOM setelah
// dibuka, tidak seperti <details> yang selalu merender isinya.
async function bukaPerbandingan() {
  await userEvent.click(screen.getByRole("button", { name: /dasar perbandingan/i }));
}

describe("CandidatesTable", () => {
  it("menyembunyikan detail sampai dibuka", () => {
    render(<CandidatesTable candidates={candidates} winner="xgboost" rankingMetric="mape" />);

    expect(screen.getByRole("button", { name: /dasar perbandingan \(3 metode diuji\)/i })).toBeDefined();
    expect(screen.queryByText("moving_average")).toBeNull();
  });

  it("menampilkan seluruh metode yang dibandingkan beserta metriknya", async () => {
    render(<CandidatesTable candidates={candidates} winner="xgboost" rankingMetric="mape" />);
    await bukaPerbandingan();

    expect(screen.getByText("moving_average")).toBeDefined();
    expect(screen.getByText("xgboost")).toBeDefined();
    expect(screen.getByText("random_forest")).toBeDefined();
    expect(screen.getByText("8.20%")).toBeDefined(); // MAPE pemenang
  });

  it("mengurutkan dari metrik ranking terbaik dan menandai pemenang", async () => {
    render(<CandidatesTable candidates={candidates} winner="xgboost" rankingMetric="mape" />);
    await bukaPerbandingan();

    const rows = screen.getAllByRole("row").slice(1); // buang header
    expect(rows[0].textContent).toContain("xgboost"); // MAPE terendah di atas
    expect(rows[0].textContent).toMatch(/terpilih/i);
    expect(rows[1].textContent).toContain("random_forest");
  });

  it("menampilkan strip untuk metrik yang tak terdefinisi", async () => {
    render(<CandidatesTable candidates={candidates} winner="xgboost" rankingMetric="mape" />);
    await bukaPerbandingan();

    expect(screen.queryByText(/null|NaN/)).toBeNull();
  });

  it("tidak merender apa pun bila hanya satu kandidat (tak ada yang dibandingkan)", () => {
    const { container } = render(
      <CandidatesTable candidates={[candidates[1]]} winner="xgboost" rankingMetric="mape" />,
    );

    expect(container.firstChild).toBeNull();
  });
});
