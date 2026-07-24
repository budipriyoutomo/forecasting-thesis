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
        n_materials_detected: 3,
        preview: [{ material_code: "MAT-001", date: "2026-01-01", quantity: 10 }],
        warnings: ["1 kode material belum terdaftar di master data: MAT-999"],
        status: "validated",
      },
    });
    renderPanel();

    const file = new File(["material_code,date,quantity"], "data.csv", { type: "text/csv" });
    await userEvent.upload(screen.getByLabelText(/pilih file csv/i), file);

    expect(await screen.findByText(/material terdeteksi/i)).toBeDefined();
    expect(screen.getByText(/belum terdaftar/i)).toBeDefined();
    expect(screen.getByText("MAT-001")).toBeDefined();
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
