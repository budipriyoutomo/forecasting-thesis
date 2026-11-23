import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  useMethodComparison,
  useSelectForecastMethod,
  useSelectForecastMethodForRun,
} from "@/hooks/useForecast";
import { api } from "@/lib/api";

vi.mock("@/lib/auth", () => ({ getToken: () => "tok" }));

function setup() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidate = vi.spyOn(qc, "invalidateQueries");
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return { wrapper, invalidate };
}

const KEY = ["forecast-run", "run1", "method-comparison"];

describe("useMethodComparison (CR v3.7)", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("memanggil api.forecast.getMethodComparison(runId, token)", async () => {
    const get = vi
      .spyOn(api.forecast, "getMethodComparison")
      .mockResolvedValue({ success: true, data: { run_id: "run1" } } as never);
    const { wrapper } = setup();
    const { result } = renderHook(() => useMethodComparison("run1"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(get).toHaveBeenCalledWith("run1", "tok");
  });

  it("error envelope → isError dengan pesan backend", async () => {
    vi.spyOn(api.forecast, "getMethodComparison").mockResolvedValue({
      success: false, error: { code: "FORECAST_RUN_NOT_FOUND", message: "Forecast run tidak ditemukan." },
    } as never);
    const { wrapper } = setup();
    const { result } = renderHook(() => useMethodComparison("run1"), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("Forecast run tidak ditemukan.");
  });

  it("ganti metode satu produk → invalidate method-comparison", async () => {
    vi.spyOn(api.forecast, "selectMethod").mockResolvedValue({ success: true, data: {} } as never);
    const { wrapper, invalidate } = setup();
    const { result } = renderHook(() => useSelectForecastMethod("run1"), { wrapper });

    await act(() => result.current.mutateAsync({ resultId: "r1", method: "xgboost", reason: "x" }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: KEY });
  });

  it("ganti metode semua produk → invalidate method-comparison", async () => {
    vi.spyOn(api.forecast, "selectMethodForRun").mockResolvedValue({ success: true, data: {} } as never);
    const { wrapper, invalidate } = setup();
    const { result } = renderHook(() => useSelectForecastMethodForRun("run1"), { wrapper });

    await act(() => result.current.mutateAsync({ method: "xgboost", reason: "x" }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: KEY });
  });
});
