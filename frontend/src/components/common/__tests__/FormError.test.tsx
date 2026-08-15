import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FormError } from "@/components/common/FormError";

describe("FormError", () => {
  it("menampilkan pesan galat", () => {
    render(<FormError message="Kode SKU sudah dipakai." />);

    expect(screen.getByText("Kode SKU sudah dipakai.")).toBeDefined();
  });

  it("tidak merender apa pun bila tidak ada galat", () => {
    const { container } = render(<FormError message={null} />);

    expect(container.firstChild).toBeNull();
  });

  // Galat submit muncul setelah user menekan tombol, jadi harus diumumkan
  // screen reader tanpa memindahkan fokus.
  it("diumumkan sebagai peringatan", () => {
    render(<FormError message="Gagal menyimpan." />);

    expect(screen.getByRole("alert")).toBeDefined();
  });
});
