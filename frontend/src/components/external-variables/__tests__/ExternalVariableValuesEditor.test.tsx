import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ExternalVariableValuesEditor } from "@/components/external-variables/ExternalVariableValuesEditor";

const VALUES = [
  { product_id: null, period: "2026-01-01", value: 30 },
  { product_id: null, period: "2026-02-01", value: 28.5 },
];

// 21 Nov 2026 — dialog "Ubah" kini bisa mengubah nilai per periode, bukan hanya definisi.
describe("ExternalVariableValuesEditor", () => {
  it("mengubah nilai yang ada dan menambah periode baru", async () => {
    const onSave = vi.fn();
    render(<ExternalVariableValuesEditor values={VALUES} valueType="numeric" scope="global" products={[]} onSave={onSave} />);

    const jan = screen.getByLabelText("Nilai 2026-01");
    await userEvent.clear(jan);
    await userEvent.type(jan, "31,2");
    await userEvent.click(screen.getByRole("button", { name: /tambah periode/i }));
    await userEvent.type(screen.getByLabelText("Periode baris baru 1"), "2026-03");
    await userEvent.type(screen.getByLabelText("Nilai baris baru 1"), "27");
    await userEvent.click(screen.getByRole("button", { name: /simpan nilai/i }));

    // baris baru tampil paling atas
    expect(onSave).toHaveBeenCalledWith([
      { period: "2026-03-01", value: 27, product_id: null },
      { period: "2026-01-01", value: 31.2, product_id: null },
    ]);
  }, 20_000); // banyak userEvent.type — lambat saat suite paralel

  it("tombol simpan nonaktif bila belum ada perubahan, error validasi ditampilkan", async () => {
    const onSave = vi.fn();
    render(<ExternalVariableValuesEditor values={VALUES} valueType="flag" scope="global" products={[]} onSave={onSave} />);
    const save = screen.getByRole("button", { name: /simpan nilai/i }) as HTMLButtonElement;
    expect(save.disabled).toBe(true);

    const jan = screen.getByLabelText("Nilai 2026-01");
    await userEvent.clear(jan);
    await userEvent.type(jan, "5");
    await userEvent.click(save);

    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByText(/harus bernilai 0 atau 1/)).toBeDefined();
  });
});
