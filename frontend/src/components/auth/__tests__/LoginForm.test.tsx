import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "@/components/auth/LoginForm";
import { api } from "@/lib/api";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

afterEach(() => {
  vi.restoreAllMocks();
  push.mockReset();
  window.history.replaceState({}, "", "/login");
  document.cookie = "fiq_token=; path=/; max-age=0";
});

function renderForm() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <LoginForm />
    </QueryClientProvider>,
  );
}

describe("LoginForm", () => {
  it("validasi email tidak valid tanpa memanggil API", async () => {
    const spy = vi.spyOn(api.auth, "login");
    renderForm();

    await userEvent.type(screen.getByLabelText(/email/i), "bukan-email");
    await userEvent.type(screen.getByLabelText(/password/i), "secret");
    await userEvent.click(screen.getByRole("button", { name: /masuk/i }));

    expect(await screen.findByText(/Format email tidak valid/i)).toBeDefined();
    expect(spy).not.toHaveBeenCalled();
  });

  it("login sukses menyimpan token dan redirect ke /dashboard", async () => {
    vi.spyOn(api.auth, "login").mockResolvedValue({
      success: true,
      data: {
        access_token: "tok-abc",
        token_type: "bearer",
        user: { id: "1", email: "a@b.com", name: "A", role: "ppic", is_verified: true },
      },
    });
    renderForm();

    await userEvent.type(screen.getByLabelText(/email/i), "a@b.com");
    await userEvent.type(screen.getByLabelText(/password/i), "secret");
    await userEvent.click(screen.getByRole("button", { name: /masuk/i }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
    expect(document.cookie).toContain("fiq_token=tok-abc");
  });

  it("menampilkan pesan error dari backend saat kredensial salah", async () => {
    vi.spyOn(api.auth, "login").mockResolvedValue({
      success: false,
      error: { code: "AUTH_INVALID_CREDENTIALS", message: "Email atau password salah." },
    });
    renderForm();

    await userEvent.type(screen.getByLabelText(/email/i), "a@b.com");
    await userEvent.type(screen.getByLabelText(/password/i), "salah");
    await userEvent.click(screen.getByRole("button", { name: /masuk/i }));

    expect(await screen.findByText(/Email atau password salah/i)).toBeDefined();
    expect(push).not.toHaveBeenCalled();
  });

  // CR v3.5 §5.3 — kembali ke halaman asal setelah login ulang (param `next` dari middleware/sesi berakhir).
  async function loginOk() {
    vi.spyOn(api.auth, "login").mockResolvedValue({
      success: true,
      data: {
        access_token: "tok-abc",
        token_type: "bearer",
        user: { id: "1", email: "a@b.com", name: "A", role: "ppic", is_verified: true },
      },
    });
    renderForm();
    await userEvent.type(screen.getByLabelText(/email/i), "a@b.com");
    await userEvent.type(screen.getByLabelText(/password/i), "secret");
    await userEvent.click(screen.getByRole("button", { name: /masuk/i }));
  }

  it("redirect ke `next` setelah login", async () => {
    window.history.replaceState({}, "", "/login?next=%2Fmaterials");
    await loginOk();
    await waitFor(() => expect(push).toHaveBeenCalledWith("/materials"));
  });

  it("`next` ke domain lain diabaikan → /dashboard", async () => {
    window.history.replaceState({}, "", "/login?next=https%3A%2F%2Fevil.example");
    await loginOk();
    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
  });

  it("reason=expired menampilkan pesan sesi berakhir", async () => {
    window.history.replaceState({}, "", "/login?next=%2Fdashboard&reason=expired");
    renderForm();
    expect(await screen.findByText(/sesi anda telah berakhir/i)).toBeDefined();
  });

  it("tanpa reason tidak ada pesan sesi berakhir", () => {
    renderForm();
    expect(screen.queryByText(/sesi anda telah berakhir/i)).toBeNull();
  });
});
