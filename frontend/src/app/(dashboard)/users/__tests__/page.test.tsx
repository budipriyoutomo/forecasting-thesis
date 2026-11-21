import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import UsersPage from "@/app/(dashboard)/users/page";
import { api } from "@/lib/api";

vi.mock("@/lib/auth", () => ({ getToken: () => "tok", clearToken: () => {} }));

const ME = { id: "u-admin", email: "admin@x.id", name: "Admin Satu", role: "admin", is_verified: true };
const USERS = [
  { ...ME, is_active: true, created_at: "2026-11-01T00:00:00Z" },
  { id: "u-ppic", email: "ppic@x.id", name: "Planner", role: "ppic", is_verified: true, is_active: true, created_at: null },
  { id: "u-old", email: "old@x.id", name: "Mantan", role: "viewer", is_verified: true, is_active: false, created_at: null },
];

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <UsersPage />
    </QueryClientProvider>,
  );
}

const row = async (name: string) => (await screen.findByText(name)).closest("tr") as HTMLElement;

// CR v3.7 — User Management khusus admin (user.manage).
describe("UsersPage — admin", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api.auth, "me").mockResolvedValue({ success: true, data: ME } as never);
    vi.spyOn(api.users, "list").mockResolvedValue({ success: true, data: USERS } as never);
  });

  it("menampilkan daftar user dengan role dan status", async () => {
    renderPage();

    const planner = await row("Planner");
    expect(within(planner).getByText("ppic@x.id")).toBeDefined();
    expect((within(planner).getByLabelText(/role planner/i) as HTMLSelectElement).value).toBe("ppic");
    expect(within(planner).getByText("Aktif")).toBeDefined();
    expect(within(await row("Mantan")).getByText("Nonaktif")).toBeDefined();
  });

  it("mengubah role user lain lewat dropdown", async () => {
    const update = vi.spyOn(api.users, "update").mockResolvedValue({
      success: true, data: { ...USERS[1], role: "purchasing" },
    } as never);
    renderPage();

    await userEvent.selectOptions(within(await row("Planner")).getByLabelText(/role planner/i), "purchasing");

    await waitFor(() => expect(update).toHaveBeenCalledWith("u-ppic", { role: "purchasing" }, "tok"));
  });

  it("menonaktifkan & mengaktifkan kembali user lain", async () => {
    const update = vi.spyOn(api.users, "update").mockResolvedValue({ success: true, data: USERS[1] } as never);
    renderPage();

    await userEvent.click(within(await row("Planner")).getByRole("button", { name: "Nonaktifkan" }));
    await waitFor(() => expect(update).toHaveBeenCalledWith("u-ppic", { is_active: false }, "tok"));

    await userEvent.click(within(await row("Mantan")).getByRole("button", { name: "Aktifkan" }));
    await waitFor(() => expect(update).toHaveBeenCalledWith("u-old", { is_active: true }, "tok"));
  });

  it("baris diri sendiri: role & nonaktifkan dikunci", async () => {
    renderPage();

    const self = await row("Admin Satu");
    expect(within(self).getByText("(Anda)")).toBeDefined();
    expect((within(self).getByLabelText(/role admin satu/i) as HTMLSelectElement).disabled).toBe(true);
    expect((within(self).getByRole("button", { name: "Nonaktifkan" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("menambah user lewat dialog", async () => {
    const create = vi.spyOn(api.users, "create").mockResolvedValue({
      success: true, data: { ...USERS[1], id: "u-new", email: "baru@x.id", name: "Baru" },
    } as never);
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: /tambah user/i }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Email"), "baru@x.id");
    await userEvent.type(within(dialog).getByLabelText("Nama"), "Baru");
    await userEvent.selectOptions(within(dialog).getByLabelText("Role"), "purchasing");
    await userEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));

    await waitFor(() =>
      expect(create).toHaveBeenCalledWith({ email: "baru@x.id", name: "Baru", role: "purchasing" }, "tok"),
    );
  });

  it("menampilkan pesan error backend saat tambah user gagal", async () => {
    vi.spyOn(api.users, "create").mockResolvedValue({
      success: false, error: { code: "USER_EMAIL_EXISTS", message: "Email 'ppic@x.id' sudah terdaftar." },
    } as never);
    renderPage();

    await userEvent.click(await screen.findByRole("button", { name: /tambah user/i }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Email"), "ppic@x.id");
    await userEvent.type(within(dialog).getByLabelText("Nama"), "Dobel");
    await userEvent.click(within(dialog).getByRole("button", { name: "Simpan" }));

    expect(await within(dialog).findByText(/sudah terdaftar/)).toBeDefined();
  });
});

describe("UsersPage — non-admin", () => {
  it("menampilkan pesan khusus admin dan tidak memuat daftar user", async () => {
    vi.restoreAllMocks();
    vi.spyOn(api.auth, "me").mockResolvedValue({ success: true, data: { ...ME, role: "ppic" } } as never);
    const list = vi.spyOn(api.users, "list").mockResolvedValue({ success: true, data: [] } as never);
    renderPage();

    expect(await screen.findByText(/khusus admin/i)).toBeDefined();
    expect(list).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: /tambah user/i })).toBeNull();
  });
});
