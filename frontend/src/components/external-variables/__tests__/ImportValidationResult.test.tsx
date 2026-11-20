import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ImportValidationResult } from "@/components/external-variables/ImportValidationResult";
import type { ImportDryRunResult } from "@/types/externalVariable";

const base: ImportDryRunResult = {
  dry_run: true, valid: true, errors: [], n_errors: 0, format: "wide",
  imported: 204, normalized: 204, overwritten: 0, skipped: { hari_promo: 4 }, warnings: [],
};

describe("ImportValidationResult", () => {
  it("file valid: jumlah siap diimpor + sel dilewati", () => {
    render(<ImportValidationResult result={base} />);
    expect(screen.getByText(/file valid/i).textContent).toContain("204 nilai siap diimpor");
    expect(screen.getByText(/hari_promo 4/)).toBeDefined();
  });

  it("file tidak valid: semua error tampil + sisa yang tidak ditampilkan", () => {
    render(
      <ImportValidationResult
        result={{
          ...base, valid: false, n_errors: 102,
          errors: ["Baris 3: variabel 'hujan' tidak dikenal.", "Baris 4: 'period' bukan tanggal valid."],
          warnings: ["Kolom tidak dikenal diabaikan: kolom_aneh."],
        }}
      />,
    );
    expect(screen.getByText(/102 error/i)).toBeDefined();
    expect(screen.getByText("Baris 3: variabel 'hujan' tidak dikenal.")).toBeDefined();
    expect(screen.getByText(/100 error lain tidak ditampilkan/i)).toBeDefined();
    expect(screen.getByText(/kolom_aneh/)).toBeDefined();
  });
});
