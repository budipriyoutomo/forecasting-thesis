import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ExternalVariableForm } from "@/components/external-variables/ExternalVariableForm";

describe("ExternalVariableForm", () => {
  it("validasi kode snake_case", async () => {
    const onSubmit = vi.fn();
    render(<ExternalVariableForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/^kode$/i), "Suhu Udara");
    await userEvent.type(screen.getByLabelText(/^nama$/i), "Suhu");
    await userEvent.click(screen.getByRole("button", { name: /simpan variabel/i }));

    expect(await screen.findByText(/snake_case/i)).toBeDefined();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submit variabel flag per produk", async () => {
    const onSubmit = vi.fn();
    render(<ExternalVariableForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/^kode$/i), "promo");
    await userEvent.type(screen.getByLabelText(/^nama$/i), "Promosi");
    await userEvent.click(screen.getByRole("radio", { name: /flag/i }));
    await userEvent.click(screen.getByRole("radio", { name: /per produk/i }));
    await userEvent.click(screen.getByRole("button", { name: /simpan variabel/i }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ code: "promo", name: "Promosi", value_type: "flag", scope: "product" }),
    );
  });

  it("kode tidak bisa diubah saat edit", () => {
    render(
      <ExternalVariableForm
        initial={{
          id: "v1", code: "suhu", name: "Suhu", value_type: "numeric", scope: "global",
          unit: "°C", description: null, is_active: true, n_values: 0,
        }}
        onSubmit={vi.fn()}
      />,
    );
    expect((screen.getByLabelText(/^kode$/i) as HTMLInputElement).disabled).toBe(true);
  });

  it("petunjuk kategori → beberapa flag & larangan variabel turunan demand (CR v3.4 §4.4–4.5)", () => {
    render(<ExternalVariableForm onSubmit={vi.fn()} />);
    expect(screen.getByText(/variabel kategori .*buat sebagai beberapa flag/i)).toBeDefined();
    expect(screen.getByText(/turunan demand/i)).toBeDefined();
  });
});
