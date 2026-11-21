import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CostTemplatesPage from "@/app/(dashboard)/cost-templates/page";
import { SUMMARY, TEMPLATE } from "@/components/cost-templates/__tests__/fixtures";
import { api } from "@/lib/api";

vi.mock("@/lib/auth", () => ({ getToken: () => "tok", clearToken: () => {} }));

const DRAFT = { ...TEMPLATE, id: "t2", name: "Draf 2027", is_active: false };

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CostTemplatesPage />
    </QueryClientProvider>,
  );
}

const rowOf = async (name: string) => (await screen.findByText(name)).closest("tr") as HTMLElement;

describe("CostTemplatesPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api.auth, "me").mockResolvedValue({ success: true, data: { id: "u1", role: "admin" } } as never);
    vi.spyOn(api.costTemplates, "list").mockResolvedValue({ success: true, data: [TEMPLATE, DRAFT] } as never);
    vi.spyOn(api.materials, "list").mockResolvedValue({ success: true, data: [] } as never);
  });

  it("Lihat ringkasan membuka panel ringkasan template yang diklik", async () => {
    const summary = vi.spyOn(api.costTemplates, "summary").mockResolvedValue({
      success: true, data: { ...SUMMARY, template_id: "t2" },
    } as never);
    renderPage();

    await userEvent.click(within(await rowOf("Draf 2027")).getByRole("button", { name: /lihat ringkasan/i }));

    const panel = await screen.findByRole("dialog");
    expect(within(panel).getByText(/Ringkasan — Draf 2027/)).toBeDefined();
    await waitFor(() => expect(summary).toHaveBeenCalledWith("t2", "tok"));
    expect(await within(panel).findByText("Overhead / bulan")).toBeDefined();
  });

  it("ringkasan gagal dimuat → pesan error tampil, bukan diam", async () => {
    vi.spyOn(api.costTemplates, "summary").mockResolvedValue({
      success: false, error: { code: "INTERNAL_ERROR", message: "Server error" },
    } as never);
    renderPage();

    await userEvent.click(within(await rowOf("Template 2026")).getByRole("button", { name: /lihat ringkasan/i }));

    expect(await within(await screen.findByRole("dialog")).findByText(/Gagal memuat ringkasan: Server error/)).toBeDefined();
  });

  it("Nonaktifkan template aktif memanggil API deactivate", async () => {
    const deactivate = vi.spyOn(api.costTemplates, "deactivate").mockResolvedValue({
      success: true, data: { ...TEMPLATE, is_active: false },
    } as never);
    renderPage();

    await userEvent.click(within(await rowOf("Template 2026")).getByRole("button", { name: "Nonaktifkan" }));
    await userEvent.click(await screen.findByRole("button", { name: /ya, nonaktifkan/i }));

    await waitFor(() => expect(deactivate).toHaveBeenCalledWith("t1", "tok"));
  });
});
