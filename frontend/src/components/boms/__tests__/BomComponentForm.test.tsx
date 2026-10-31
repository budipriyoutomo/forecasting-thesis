import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { BomComponentForm } from "@/components/boms/BomComponentForm";

const MATERIALS = [
  { id: "btl", code: "BTL-WHITE", name: "Bottle White", unit: "PCS" },
  { id: "pre", code: "PRE-WHITE", name: "Preform White", unit: "PCS" },
] as never[];

describe("BomComponentForm", () => {
  it("menolak komponen = induk & submit komponen level 2", async () => {
    const onSubmit = vi.fn();
    render(<BomComponentForm parents={[{ id: "btl", code: "BTL-WHITE" }]} materials={MATERIALS} onSubmit={onSubmit} />);

    await userEvent.selectOptions(screen.getByLabelText(/material induk/i), "btl");
    await userEvent.selectOptions(screen.getByLabelText(/^komponen$/i), "btl");
    await userEvent.click(screen.getByRole("button", { name: /tambah komponen/i }));
    expect(screen.getByText(/dirinya sendiri/i)).toBeDefined();

    await userEvent.selectOptions(screen.getByLabelText(/^komponen$/i), "pre");
    await userEvent.click(screen.getByRole("button", { name: /tambah komponen/i }));
    expect(onSubmit).toHaveBeenCalledWith({ parentId: "btl", componentId: "pre", qty: 1 });
  });
});
