import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Button } from "@/components/ui/button";

afterEach(() => vi.restoreAllMocks());

// Label pemicu dan label konfirmasi sengaja dibedakan: keduanya hidup bersamaan di DOM
// saat dialog terbuka (pemicu tidak dilepas Radix), jadi label yang sama bikin ambigu —
// bagi test maupun bagi screen reader.
function renderDialog(onConfirm = vi.fn()) {
  render(
    <ConfirmDialog
      trigger={<Button>Hapus</Button>}
      title="Hapus produk?"
      description="Tindakan ini tidak bisa dibatalkan."
      confirmLabel="Ya, hapus"
      onConfirm={onConfirm}
    />,
  );
  return onConfirm;
}

describe("ConfirmDialog", () => {
  it("tidak menjalankan aksi sebelum dikonfirmasi", async () => {
    const onConfirm = renderDialog();

    await userEvent.click(screen.getByRole("button", { name: "Hapus" }));

    expect(await screen.findByText("Hapus produk?")).toBeDefined();
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("menjalankan aksi setelah tombol konfirmasi ditekan", async () => {
    const onConfirm = renderDialog();

    await userEvent.click(screen.getByRole("button", { name: "Hapus" }));
    await userEvent.click(await screen.findByRole("button", { name: "Ya, hapus" }));

    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("membatalkan tanpa menjalankan aksi", async () => {
    const onConfirm = renderDialog();

    await userEvent.click(screen.getByRole("button", { name: "Hapus" }));
    await userEvent.click(await screen.findByRole("button", { name: /batal/i }));

    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("menampilkan konsekuensi, bukan cuma pertanyaan", async () => {
    renderDialog();

    await userEvent.click(screen.getByRole("button", { name: "Hapus" }));

    expect(await screen.findByText("Tindakan ini tidak bisa dibatalkan.")).toBeDefined();
  });
});
