import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FeatureImportance } from "@/components/forecast/FeatureImportance";

describe("FeatureImportance", () => {
  it("menampilkan fitur terurut dengan persentase", () => {
    render(<FeatureImportance importance={{ lag_1: 0.6, suhu: 0.3, month: 0.1 }} />);

    const items = screen.getAllByRole("listitem");
    expect(items[0].textContent).toContain("Lag 1");
    expect(items[0].textContent).toContain("60.0%");
    expect(items[1].textContent).toContain("suhu");
    expect(items[2].textContent).toContain("Bulan");
  });

  it("tidak merender apa pun tanpa data", () => {
    const { container } = render(<FeatureImportance importance={null} />);
    expect(container.firstChild).toBeNull();
  });
});
