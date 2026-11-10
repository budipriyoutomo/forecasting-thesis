import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MethodSelectionDialog } from "@/components/forecast/MethodSelectionDialog";

describe("MethodSelectionDialog (Fase 11.15)", () => {
  it("alasan wajib sebelum metode dipakai", async () => {
    const onSubmit = vi.fn();
    render(
      <MethodSelectionDialog
        target={{ method: "xgboost", label: "SKU-001 — Kursi Lipat" }}
        onSubmit={onSubmit}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText(/xgboost/)).toBeDefined();
    await userEvent.click(screen.getByRole("button", { name: /pakai metode/i }));
    expect(screen.getByText(/alasan wajib diisi/i)).toBeDefined();
    expect(onSubmit).not.toHaveBeenCalled();

    await userEvent.type(screen.getByLabelText(/alasan/i), "Pola musiman");
    await userEvent.click(screen.getByRole("button", { name: /pakai metode/i }));
    expect(onSubmit).toHaveBeenCalledWith("Pola musiman");
  });

  it("menampilkan error dari server & nonaktif saat menyimpan", () => {
    render(
      <MethodSelectionDialog
        target={{ method: "xgboost", label: "semua produk" }}
        onSubmit={vi.fn()}
        onClose={vi.fn()}
        pending
        error="Metode tidak tersedia"
      />,
    );

    expect(screen.getByText(/metode tidak tersedia/i)).toBeDefined();
    expect((screen.getByRole("button", { name: /menyimpan/i }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("tertutup bila tidak ada target", () => {
    render(<MethodSelectionDialog target={null} onSubmit={vi.fn()} onClose={vi.fn()} />);

    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
