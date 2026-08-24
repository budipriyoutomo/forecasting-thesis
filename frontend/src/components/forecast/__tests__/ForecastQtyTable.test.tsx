import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ForecastQtyTable } from "@/components/forecast/ForecastQtyTable";
import type { ForecastPoint } from "@/types/forecast";

const forecast: ForecastPoint[] = [
  { date: "2026-09-01", value: 1200.4, lower: 1100, upper: 1300 },
  { date: "2026-10-01", value: 1350.6, lower: 1250, upper: 1450 },
  { date: "2026-11-01", value: 1400, lower: 1300, upper: 1500 },
];

// Isi tabel baru dipasang ke DOM setelah Collapsible dibuka (pola sama dgn CandidatesTable).
async function bukaRincian() {
  await userEvent.click(screen.getByRole("button", { name: /rincian qty/i }));
}

describe("ForecastQtyTable", () => {
  it("menampilkan total & rata-rata qty tanpa perlu dibuka", () => {
    render(<ForecastQtyTable forecast={forecast} />);

    // total = 1200,4 + 1350,6 + 1400 = 3951 ; rata-rata = 1317
    // Label & angka ada di elemen berbeda dalam satu kartu, jadi dibaca dari kartunya.
    expect(screen.getByText(/total qty forecast/i).parentElement?.textContent).toContain("3.951");
    expect(screen.getByText(/rata-rata per periode/i).parentElement?.textContent).toContain("1.317");
  });

  it("menyembunyikan rincian per periode sampai dibuka", () => {
    render(<ForecastQtyTable forecast={forecast} />);

    expect(screen.getByRole("button", { name: /rincian qty per periode \(3\)/i })).toBeDefined();
    expect(screen.queryByText("2026-09-01")).toBeNull();
  });

  it("menampilkan qty tiap periode beserta batas bawah/atas setelah dibuka", async () => {
    render(<ForecastQtyTable forecast={forecast} />);
    await bukaRincian();

    expect(screen.getByText("2026-09-01")).toBeDefined();
    expect(screen.getByText("1.200,4")).toBeDefined();
    expect(screen.getByText("1.100")).toBeDefined();
    // 1.300 muncul dua kali: batas atas periode 1 dan batas bawah periode 3.
    expect(screen.getAllByText("1.300")).toHaveLength(2);
  });

  it("tidak merender apa pun saat forecast kosong", () => {
    const { container } = render(<ForecastQtyTable forecast={[]} />);

    expect(container.firstChild).toBeNull();
  });
});
