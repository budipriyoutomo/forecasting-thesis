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

// Radix Select hanya merender opsi setelah dropdown dibuka — beda dengan <select>
// native yang selalu punya <option> di DOM.
async function bukaDropdown() {
  await userEvent.click(screen.getByRole("combobox", { name: /metode forecasting/i }));
}

describe("MethodSelector", () => {
  it("menampilkan opsi Otomatis + metode aktif dari backend", async () => {
    vi.spyOn(api.forecast, "methods").mockResolvedValue({
      success: true,
      data: { methods: ["ets", "croston"] },
    });
    renderSelector();

    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: /metode forecasting/i })).not.toHaveProperty(
        "disabled",
        true,
      ),
    );
    await bukaDropdown();

    expect(await screen.findByRole("option", { name: /Otomatis \(Direkomendasikan\)/i })).toBeDefined();
    expect(screen.getByRole("option", { name: /Croston/i })).toBeDefined();
    expect(screen.getByRole("option", { name: /ETS/i })).toBeDefined();
  });

  it("memanggil onChange saat metode dipilih", async () => {
    vi.spyOn(api.forecast, "methods").mockResolvedValue({
      success: true,
      data: { methods: ["ets"] },
    });
    const onChange = renderSelector();

    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: /metode forecasting/i })).not.toHaveProperty(
        "disabled",
        true,
      ),
    );
    await bukaDropdown();
    await userEvent.click(await screen.findByRole("option", { name: /ETS/i }));

    await waitFor(() => expect(onChange).toHaveBeenCalledWith("ets"));
  });

  it("mode otomatis dikirim sebagai string kosong, bukan sentinel internal", async () => {
    vi.spyOn(api.forecast, "methods").mockResolvedValue({
      success: true,
      data: { methods: ["ets"] },
    });
    const onChange = vi.fn();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <MethodSelector value="ets" onChange={onChange} />
      </QueryClientProvider>,
    );

    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: /metode forecasting/i })).not.toHaveProperty(
        "disabled",
        true,
      ),
    );
    await bukaDropdown();
    await userEvent.click(await screen.findByRole("option", { name: /Otomatis/i }));

    await waitFor(() => expect(onChange).toHaveBeenCalledWith(""));
  });
});
