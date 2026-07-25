import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { UploadPanel } from "@/components/upload/UploadPanel";
import { api } from "@/lib/api";

afterEach(() => {
  vi.restoreAllMocks();
  document.cookie = "fiq_token=tok; path=/";
});

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <UploadPanel />
    </QueryClientProvider>,
  );
}

describe("UploadPanel", () => {
  it("upload sukses menampilkan ringkasan + preview", async () => {
    vi.spyOn(api.uploads, "create").mockResolvedValue({
      success: true,
      data: {
        session_id: "s-1",
        n_rows: 12,
        n_products_detected: 3,
        preview: [{ product_code: "SKU-001", period: "2026-01-01", actual: 100 }],
        warnings: ["1 kode produk belum terdaftar di master data: SKU-999"],
        status: "validated",
      },
    });
    renderPanel();

    const file = new File(["product_code,period,actual"], "data.csv", { type: "text/csv" });
    await userEvent.upload(screen.getByLabelText(/pilih file csv/i), file);

    expect(await screen.findByText(/produk terdeteksi/i)).toBeDefined();
    expect(screen.getByText(/belum terdaftar/i)).toBeDefined();
    expect(screen.getByText("SKU-001")).toBeDefined();
  });

  it("menampilkan pesan error dari backend", async () => {
    vi.spyOn(api.uploads, "create").mockResolvedValue({
      success: false,
      error: { code: "UPLOAD_INVALID_FORMAT", message: "Kolom wajib hilang: quantity" },
    });
    renderPanel();

    const file = new File(["x"], "data.csv", { type: "text/csv" });
    await userEvent.upload(screen.getByLabelText(/pilih file csv/i), file);

    expect(await screen.findByText(/Kolom wajib hilang/i)).toBeDefined();
  });
});
