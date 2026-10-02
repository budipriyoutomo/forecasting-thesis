import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CostTemplatesTable } from "@/components/cost-templates/CostTemplatesTable";

import { TEMPLATE } from "./fixtures";

const NON_AKTIF = { ...TEMPLATE, id: "t2", name: "Draf 2027", is_active: false };

describe("CostTemplatesTable", () => {
  it("menampilkan S, H dalam Rupiah dan badge aktif", () => {
    render(<CostTemplatesTable templates={[TEMPLATE, NON_AKTIF]} />);
    expect(screen.getAllByText("Rp 250.000").length).toBe(2);
    expect(screen.getAllByText("Rp 800").length).toBe(2);
    expect(screen.getByText("Aktif")).toBeDefined();
  });

  it("tombol Aktifkan hanya untuk template non-aktif", async () => {
    const onActivate = vi.fn();
    render(<CostTemplatesTable templates={[TEMPLATE, NON_AKTIF]} onActivate={onActivate} />);
    const buttons = screen.getAllByRole("button", { name: /aktifkan/i });
    expect(buttons.length).toBe(1);
    await userEvent.click(buttons[0]);
    // Aktivasi mengubah S & H yang dipakai EOQ → wajib konfirmasi dulu.
    expect(onActivate).not.toHaveBeenCalled();
    await userEvent.click(await screen.findByRole("button", { name: /ya, aktifkan/i }));
    expect(onActivate).toHaveBeenCalledWith(expect.objectContaining({ id: "t2" }));
  });

  it("memilih baris memanggil onSelect", async () => {
    const onSelect = vi.fn();
    render(<CostTemplatesTable templates={[TEMPLATE]} onSelect={onSelect} />);
    await userEvent.click(screen.getByRole("button", { name: /lihat ringkasan/i }));
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: "t1" }));
  });
});
