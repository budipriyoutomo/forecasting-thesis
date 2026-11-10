import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProductsPage from "@/app/(dashboard)/products/page";
import { api } from "@/lib/api";

vi.mock("@/lib/auth", () => ({ getToken: () => "tok" }));

const product = { id: "p1", code: "KBYPL 200", name: "Produk A", category: null, unit: "PCS", cost_price: null, selling_price: null };

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ProductsPage />
    </QueryClientProvider>,
  );
}

async function confirmDelete() {
  fireEvent.click(await screen.findByRole("button", { name: "Hapus" }));
  fireEvent.click(await screen.findByRole("button", { name: "Ya, hapus produk" }));
}

describe("ProductsPage — hapus produk", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api.products, "list").mockResolvedValue({ success: true, data: [product] });
  });

  it("memanggil API hapus setelah konfirmasi", async () => {
    const remove = vi.spyOn(api.products, "remove").mockResolvedValue({ success: true, data: { id: "p1", deleted: true } });
    renderPage();
    await confirmDelete();
    await waitFor(() => expect(remove).toHaveBeenCalledWith("p1", "tok"));
  });

  it("menampilkan pesan error bila backend menolak", async () => {
    vi.spyOn(api.products, "remove").mockResolvedValue({
      success: false,
      error: { code: "FORBIDDEN", message: "Akses ditolak" },
    } as never);
    renderPage();
    await confirmDelete();
    expect(await screen.findByText(/Gagal menghapus produk: Akses ditolak/)).toBeDefined();
  });
});
