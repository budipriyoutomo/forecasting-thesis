import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ExogUsage } from "@/components/forecast/ExogUsage";

describe("ExogUsage", () => {
  it("menampilkan jumlah dipakai dan alasan drop", () => {
    render(
      <ExogUsage hyperparameters={{ exog_used: ["suhu", "inflasi"], exog_dropped: { promo: "missing_history" } }} />,
    );
    expect(screen.getByText("Variabel eksternal dipakai 2 / 3")).toBeDefined();
    expect(screen.getByText("suhu, inflasi")).toBeDefined();
    expect(screen.getByText("promo")).toBeDefined();
    expect(screen.getByText(/nilai histori belum lengkap/i)).toBeDefined();
  });

  it("tidak tampil untuk metode tanpa variabel eksternal", () => {
    const { container } = render(<ExogUsage hyperparameters={{ alpha: 0.3 }} />);
    expect(container.innerHTML).toBe("");
  });
});
