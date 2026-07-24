import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MethodSelector } from "@/components/config/MethodSelector";
import { api } from "@/lib/api";

beforeEach(() => {
  document.cookie = "fiq_token=tok; path=/";
});

afterEach(() => {
  vi.restoreAllMocks();
});

function renderSelector(onChange = vi.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MethodSelector value="" onChange={onChange} />
    </QueryClientProvider>,
  );
  return onChange;
}

describe("MethodSelector", () => {
  it("menampilkan opsi Otomatis + metode aktif dari backend", async () => {
    vi.spyOn(api.forecast, "methods").mockResolvedValue({
      success: true,
      data: { methods: ["ets", "croston"] },
    });
    renderSelector();

    expect(screen.getByRole("option", { name: /Otomatis \(Direkomendasikan\)/i })).toBeDefined();
    await waitFor(() => expect(screen.getByRole("option", { name: /Croston/i })).toBeDefined());
    expect(screen.getByRole("option", { name: /ETS/i })).toBeDefined();
  });

  it("memanggil onChange saat metode dipilih", async () => {
    vi.spyOn(api.forecast, "methods").mockResolvedValue({
      success: true,
      data: { methods: ["ets"] },
    });
    const onChange = renderSelector();

    await waitFor(() => screen.getByRole("option", { name: /ETS/i }));
    await userEvent.selectOptions(screen.getByLabelText(/metode forecasting/i), "ets");

    expect(onChange).toHaveBeenCalledWith("ets");
  });
});
