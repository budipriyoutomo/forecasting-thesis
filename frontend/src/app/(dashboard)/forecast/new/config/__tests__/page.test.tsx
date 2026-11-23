import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/components/common/PermissionGate", () => ({
  PermissionGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
vi.mock("@/hooks/useProducts", () => ({
  useProducts: () => ({ data: [] }),
  useProductDemandCoverage: () => ({ data: [] }),
}));
const mutate = vi.fn();
vi.mock("@/hooks/useForecast", () => ({
  useCreateForecastRun: () => ({ mutate, isPending: false, isError: false }),
}));

import ForecastConfigPage from "@/app/(dashboard)/forecast/new/config/page";

describe("Forecast baru — tanpa pilihan metode (23 Nov 2026)", () => {
  it("tidak menampilkan pemilih metode dan menjelaskan pemilihan otomatis", () => {
    render(<ForecastConfigPage />);

    expect(screen.queryByLabelText(/metode forecasting/i)).toBeNull();
    expect(screen.getAllByText(/memilih metode terbaik/i).length).toBeGreaterThan(0);
  });
});
