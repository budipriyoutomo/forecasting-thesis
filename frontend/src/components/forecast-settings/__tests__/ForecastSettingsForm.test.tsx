import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ForecastSettingsForm } from "@/components/forecast-settings/ForecastSettingsForm";

const AVAILABLE = ["exponential_smoothing", "lstm", "moving_average", "random_forest", "xgboost"];

describe("ForecastSettingsForm", () => {
  it("metrik tampil berupa checkbox (bukan radio), semua tercentang bila belum diatur", () => {
    render(<ForecastSettingsForm initial={{ enabled_methods: null }} available={AVAILABLE} onSubmit={vi.fn()} />);

    const group = screen.getByRole("group", { name: /metrik yang ditampilkan/i });
    expect(within(group).queryAllByRole("radio")).toHaveLength(0);
    const boxes = within(group).getAllByRole("checkbox") as HTMLInputElement[];
    expect(boxes.map((b) => b.value)).toEqual(["mad", "mfe", "mse", "mape"]);
    expect(boxes.every((b) => b.checked)).toBe(true);
    expect(screen.queryByText(/metrik penentu metode pemenang/i)).toBeNull();
  });

  it("submit hanya metrik yang dicentang, urutan baku", async () => {
    const onSubmit = vi.fn();
    render(
      <ForecastSettingsForm
        initial={{ display_metrics: ["mape", "mad"], enabled_methods: null }}
        available={AVAILABLE}
        onSubmit={onSubmit}
      />,
    );

    expect((screen.getByRole("checkbox", { name: /^mse/i }) as HTMLInputElement).checked).toBe(false);
    await userEvent.click(screen.getByRole("checkbox", { name: /^mfe/i }));
    await userEvent.click(screen.getByRole("checkbox", { name: /^mape/i }));
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ display_metrics: ["mad", "mfe"], enabled_methods: AVAILABLE }),
    );
    expect(onSubmit.mock.calls[0][0]).not.toHaveProperty("ranking_metric");
  });

  it("minimal satu metrik tampil", async () => {
    render(<ForecastSettingsForm initial={{ display_metrics: ["mad"], enabled_methods: null }} available={AVAILABLE} onSubmit={vi.fn()} />);

    await userEvent.click(screen.getByRole("checkbox", { name: /^mad/i }));

    expect(screen.getByText(/pilih minimal satu metrik/i)).toBeDefined();
    expect((screen.getByRole("button", { name: /simpan/i }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("tombol simpan nonaktif selama menyimpan & menampilkan error", () => {
    render(
      <ForecastSettingsForm
        initial={{ enabled_methods: null }}
        available={AVAILABLE}
        onSubmit={vi.fn()}
        pending
        error="Role Anda tidak diizinkan mengakses resource ini."
      />,
    );

    expect((screen.getByRole("button", { name: /menyimpan/i }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/tidak diizinkan/i)).toBeDefined();
  });

  it("belum diatur (null) → semua metode tercentang", () => {
    render(
      <ForecastSettingsForm
        initial={{ enabled_methods: null }}
        available={AVAILABLE}
        onSubmit={vi.fn()}
      />,
    );

    const boxes = within(screen.getByRole("group", { name: /metode aktif/i })).getAllByRole(
      "checkbox",
    ) as HTMLInputElement[];
    expect(boxes).toHaveLength(5);
    expect(boxes.every((b) => b.checked)).toBe(true);
    expect(screen.getByRole("checkbox", { name: /moving average/i })).toBeDefined();
  });

  it("submit hanya metode yang dicentang", async () => {
    const onSubmit = vi.fn();
    render(
      <ForecastSettingsForm
        initial={{ enabled_methods: ["moving_average", "xgboost", "lstm"] }}
        available={AVAILABLE}
        onSubmit={onSubmit}
      />,
    );

    expect((screen.getByRole("checkbox", { name: /random forest/i }) as HTMLInputElement).checked).toBe(false);
    await userEvent.click(screen.getByRole("checkbox", { name: /lstm/i }));
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ enabled_methods: ["moving_average", "xgboost"] }),
    );
  });

  it("minimal satu metode aktif", async () => {
    const onSubmit = vi.fn();
    render(
      <ForecastSettingsForm
        initial={{ enabled_methods: ["moving_average"] }}
        available={AVAILABLE}
        onSubmit={onSubmit}
      />,
    );

    await userEvent.click(screen.getByRole("checkbox", { name: /moving average/i }));

    expect(screen.getByText(/pilih minimal satu metode/i)).toBeDefined();
    expect((screen.getByRole("button", { name: /simpan/i }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("opsi engine: grid α, metrik α, grid search & winsorize", async () => {
    const onSubmit = vi.fn();
    render(
      <ForecastSettingsForm
        initial={{ enabled_methods: null, es_alpha_grid: [0.2, 0.8] }}
        available={AVAILABLE}
        onSubmit={onSubmit}
      />,
    );

    const grid = screen.getByLabelText(/grid α/i) as HTMLInputElement;
    expect(grid.value).toBe("0.2, 0.8");
    await userEvent.clear(grid);
    await userEvent.type(grid, "0.05, 0,95");
    await userEvent.click(screen.getByRole("radio", { name: /mape \(α\)/i }));
    await userEvent.click(screen.getByRole("checkbox", { name: /grid search/i }));
    await userEvent.click(screen.getByRole("checkbox", { name: /outlier/i }));
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        es_alpha_grid: [0.05, 0.95],
        es_alpha_metric: "mape",
        ml_grid_search: true,
        ml_winsorize: true,
      }),
    );
  });

  it("grid α di luar (0, 1) ditolak", async () => {
    render(
      <ForecastSettingsForm initial={{ enabled_methods: null }} available={AVAILABLE} onSubmit={vi.fn()} />,
    );
    const grid = screen.getByLabelText(/grid α/i);
    await userEvent.clear(grid);
    await userEvent.type(grid, "0.5; 1.2");

    expect(screen.getByText(/antara 0 dan 1/i)).toBeDefined();
    expect((screen.getByRole("button", { name: /simpan/i }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("perencanaan persediaan: service level & metode EOQ", async () => {
    const onSubmit = vi.fn();
    render(
      <ForecastSettingsForm
        initial={{ enabled_methods: null, service_level_pct: 95, eoq_method: "classic" }}
        available={AVAILABLE}
        onSubmit={onSubmit}
      />,
    );
    expect((screen.getByRole("radio", { name: /^95%/ }) as HTMLInputElement).checked).toBe(true);
    await userEvent.click(screen.getByRole("radio", { name: /^99%/ }));
    await userEvent.click(screen.getByRole("radio", { name: /^eoq dinamis/i }));
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ service_level_pct: 99, eoq_method: "dynamic" }));
  });

  it("kebijakan reorder: rumus titik pesan & qty pesan (default perilaku lama)", async () => {
    const onSubmit = vi.fn();
    render(
      <ForecastSettingsForm initial={{ enabled_methods: null }} available={AVAILABLE} onSubmit={onSubmit} />,
    );
    expect((screen.getByRole("radio", { name: /μ·L \+ SS \+ B/ }) as HTMLInputElement).checked).toBe(true);
    expect((screen.getByRole("radio", { name: /^order-up-to/i }) as HTMLInputElement).checked).toBe(true);

    await userEvent.click(screen.getByRole("radio", { name: /^standar/i }));
    await userEvent.click(screen.getByRole("radio", { name: /^kelipatan eoq/i }));
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ rop_formula: "standard", order_qty_policy: "eoq" }));
  });
});
