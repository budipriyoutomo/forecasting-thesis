import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WarehouseConfigForm } from "@/components/warehouse/WarehouseConfigForm";

afterEach(() => vi.restoreAllMocks());

describe("WarehouseConfigForm", () => {
  it("validasi nilai wajib > 0 tanpa memanggil onSubmit", async () => {
    const onSubmit = vi.fn();
    render(<WarehouseConfigForm onSubmit={onSubmit} />);

    await userEvent.click(screen.getByRole("button", { name: /simpan konfigurasi/i }));

    expect(await screen.findAllByText(/lebih dari 0/i)).toBeDefined();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submit mengirim area + pallet_dimension", async () => {
    const onSubmit = vi.fn();
    render(<WarehouseConfigForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/luas gudang/i), "100");
    await userEvent.type(screen.getByLabelText(/panjang/i), "1.2");
    await userEvent.type(screen.getByLabelText(/lebar/i), "1");
    await userEvent.type(screen.getByLabelText(/tinggi/i), "1.5");
    await userEvent.click(screen.getByRole("button", { name: /simpan konfigurasi/i }));

    expect(onSubmit).toHaveBeenCalledWith({
      warehouse_area_m2: 100,
      pallet_dimension: { length: 1.2, width: 1, height: 1.5 },
    });
  });
});
