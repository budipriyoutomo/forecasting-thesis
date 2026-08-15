import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PageHeader } from "@/components/common/PageHeader";

describe("PageHeader", () => {
  it("merender judul sebagai heading tingkat 1", () => {
    render(<PageHeader title="Master Data Produk" />);

    expect(screen.getByRole("heading", { level: 1, name: "Master Data Produk" })).toBeDefined();
  });

  it("merender deskripsi bila ada", () => {
    render(<PageHeader title="Kapasitas Gudang" description="Atur luas gudang dan dimensi palet." />);

    expect(screen.getByText("Atur luas gudang dan dimensi palet.")).toBeDefined();
  });

  it("tidak merender deskripsi bila tidak diberikan", () => {
    const { container } = render(<PageHeader title="Dashboard" />);

    expect(container.querySelector("p")).toBeNull();
  });

  it("merender slot aksi", () => {
    render(<PageHeader title="Produk" actions={<button>Tambah produk</button>} />);

    expect(screen.getByRole("button", { name: "Tambah produk" })).toBeDefined();
  });
});
