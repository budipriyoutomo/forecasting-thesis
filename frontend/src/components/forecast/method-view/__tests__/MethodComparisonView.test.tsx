import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MethodComparisonView } from "@/components/forecast/method-view/MethodComparisonView";
import { api } from "@/lib/api";

import { COMPARISON, PRODUCTS } from "./fixture";

vi.mock("@/lib/auth", () => ({ getToken: () => "tok" }));

function renderView() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MethodComparisonView runId="run1" products={PRODUCTS} />
    </QueryClientProvider>,
  );
}

// Render 3 section penuh (matriks 12 bulan + tooltip) berat di jsdom — batas waktu longgar.
describe("MethodComparisonView (CR v3.7 §4.2)", { timeout: 20000 }, () => {
  beforeEach(() => vi.restoreAllMocks());

  it("section bernomor mengikuti urutan respons + analisis di akhir", async () => {
    vi.spyOn(api.forecast, "getMethodComparison").mockResolvedValue({ success: true, data: COMPARISON } as never);
    renderView();

    await screen.findByText(/1\. metode random forest/i);
    const headings = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(headings).toEqual([
      expect.stringMatching(/^1\. Metode Random Forest/),
      expect.stringMatching(/^2\. Metode LSTM/),
      expect.stringMatching(/^3\. Metode Moving Average/),
      "4. Analisis pemilihan metode terbaik",
    ]);
    expect(api.forecast.getMethodComparison).toHaveBeenCalledWith("run1", "tok");
  });

  it("badge Terbaik di section metode terbaik run saja", async () => {
    vi.spyOn(api.forecast, "getMethodComparison").mockResolvedValue({ success: true, data: COMPARISON } as never);
    renderView();

    await screen.findByText(/1\. metode random forest/i);
    const [rf, lstm] = screen.getAllByRole("heading", { level: 3 });
    expect(within(rf).getByText("Terbaik")).toBeDefined();
    expect(within(lstm).queryByText("Terbaik")).toBeNull();
  });

  it("chip navigasi lompat per metode + Analisis", async () => {
    vi.spyOn(api.forecast, "getMethodComparison").mockResolvedValue({ success: true, data: COMPARISON } as never);
    renderView();

    const nav = await screen.findByRole("navigation", { name: /lompat ke metode/i });
    const links = within(nav).getAllByRole("link");
    expect(links.map((l) => l.textContent)).toEqual(["Random Forest", "LSTM", "Moving Average", "Analisis"]);
    expect(links[0].getAttribute("href")).toBe("#method-random_forest");
    expect(document.getElementById("method-random_forest")).not.toBeNull();
    expect(links[3].getAttribute("href")).toBe("#method-analysis");
  });

  it("tiap section punya (a) hasil ramalan dan (b) pengujian peramalan", async () => {
    vi.spyOn(api.forecast, "getMethodComparison").mockResolvedValue({ success: true, data: COMPARISON } as never);
    renderView();

    await screen.findByText(/1\. metode random forest/i);
    expect(screen.getAllByText(/a\. hasil ramalan/i)).toHaveLength(3);
    expect(screen.getAllByText(/b\. pengujian peramalan/i)).toHaveLength(3);
  });

  it("error → EmptyState dengan pesan backend", async () => {
    vi.spyOn(api.forecast, "getMethodComparison").mockResolvedValue({
      success: false, error: { code: "FORECAST_RUN_NOT_FOUND", message: "Forecast run tidak ditemukan." },
    } as never);
    renderView();

    expect(await screen.findByText("Forecast run tidak ditemukan.")).toBeDefined();
  });

  it("tanpa metode → keadaan kosong", async () => {
    vi.spyOn(api.forecast, "getMethodComparison").mockResolvedValue({
      success: true, data: { ...COMPARISON, methods: [], run_selection: null },
    } as never);
    renderView();

    expect(await screen.findByText(/belum ada hasil per metode/i)).toBeDefined();
  });
});
