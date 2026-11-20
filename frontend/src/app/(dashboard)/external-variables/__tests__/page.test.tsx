import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ExternalVariablesPage from "@/app/(dashboard)/external-variables/page";
import { api } from "@/lib/api";

vi.mock("@/lib/auth", () => ({ getToken: () => "tok", clearToken: () => {} }));

const VARIABLE = {
  id: "v1", code: "suhu", name: "Suhu", value_type: "numeric", scope: "global",
  unit: "°C", description: null, is_active: true, n_values: 2,
};

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ExternalVariablesPage />
    </QueryClientProvider>,
  );
}

// CR v3.5 §5.2 — "Lihat nilai" (GET /external-variables/{id}/values), terbuka untuk semua role.
describe("ExternalVariablesPage — lihat nilai", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api.externalVariables, "list").mockResolvedValue({ success: true, data: [VARIABLE] } as never);
    vi.spyOn(api.externalVariables, "coverage").mockResolvedValue({ success: true, data: [] } as never);
    vi.spyOn(api.products, "list").mockResolvedValue({ success: true, data: [] } as never);
    vi.spyOn(api.auth, "me").mockResolvedValue({ success: true, data: { role: "viewer" } } as never);
  });

  it("viewer membuka dialog nilai per periode", async () => {
    const values = vi.spyOn(api.externalVariables, "values").mockResolvedValue({
      success: true, data: [{ product_id: null, period: "2026-01-01", value: 31.5 }],
    } as never);
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: /lihat nilai/i }));

    expect(await screen.findByRole("dialog", { name: /nilai suhu/i })).toBeDefined();
    expect(await screen.findByText("31,5")).toBeDefined();
    expect(values).toHaveBeenCalledWith("v1", "tok");
  });
});
