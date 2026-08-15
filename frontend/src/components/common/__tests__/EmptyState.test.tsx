import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EmptyState } from "@/components/common/EmptyState";

describe("EmptyState", () => {
  it("menampilkan pesan", () => {
    render(<EmptyState message="Belum ada produk." />);

    expect(screen.getByText("Belum ada produk.")).toBeDefined();
  });

  it("menampilkan petunjuk langkah berikutnya bila ada", () => {
    render(<EmptyState message="Belum ada produk." hint="Tambah dulu di menu Produk." />);

    expect(screen.getByText("Tambah dulu di menu Produk.")).toBeDefined();
  });

  it("merender aksi bila ada", () => {
    render(<EmptyState message="Belum ada data." action={<button>Tambah</button>} />);

    expect(screen.getByRole("button", { name: "Tambah" })).toBeDefined();
  });

  it("punya peran status supaya terbaca screen reader", () => {
    render(<EmptyState message="Belum ada data." />);

    expect(screen.getByRole("status")).toBeDefined();
  });
});
