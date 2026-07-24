import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MaterialForm } from "@/components/materials/MaterialForm";
import type { Material } from "@/types/material";

afterEach(() => vi.restoreAllMocks());

describe("MaterialForm", () => {
  it("validasi field wajib tanpa memanggil onSubmit", async () => {
    const onSubmit = vi.fn();
    render(<MaterialForm onSubmit={onSubmit} />);

    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    expect(await screen.findByText(/Kode wajib diisi/i)).toBeDefined();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submit mengirim input yang benar (category kosong -> null)", async () => {
    const onSubmit = vi.fn();
    render(<MaterialForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/^kode$/i), "RM-001");
    await userEvent.type(screen.getByLabelText(/^nama$/i), "Tepung");
    await userEvent.type(screen.getByLabelText(/^satuan$/i), "kg");
    await userEvent.clear(screen.getByLabelText(/lead time/i));
    await userEvent.type(screen.getByLabelText(/lead time/i), "7");
    await userEvent.clear(screen.getByLabelText(/^moq$/i));
    await userEvent.type(screen.getByLabelText(/^moq$/i), "100");
    await userEvent.click(screen.getByRole("button", { name: /simpan/i }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({
      code: "RM-001",
      name: "Tepung",
      category: null,
      unit: "kg",
      lead_time_days: 7,
      moq: 100,
    });
  });

  it("mengisi nilai awal saat mode edit", () => {
    const material: Material = {
      id: "m1",
      code: "RM-009",
      name: "Gula",
      category: "Bahan",
      unit: "kg",
      lead_time_days: 5,
      moq: "50",
      manual_safety_stock: null,
    };
    render(<MaterialForm initial={material} onSubmit={vi.fn()} />);

    expect((screen.getByLabelText(/^kode$/i) as HTMLInputElement).value).toBe("RM-009");
    expect((screen.getByLabelText(/^nama$/i) as HTMLInputElement).value).toBe("Gula");
  });
});
