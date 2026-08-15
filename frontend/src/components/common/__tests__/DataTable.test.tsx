import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ColumnDef } from "@tanstack/react-table";
import { describe, expect, it } from "vitest";

import { DataTable } from "@/components/common/DataTable";

interface Row {
  code: string;
  name: string;
  qty: number;
}

const columns: ColumnDef<Row>[] = [
  { accessorKey: "code", header: "Kode" },
  { accessorKey: "name", header: "Nama" },
  { accessorKey: "qty", header: "Jumlah" },
];

const data: Row[] = [
  { code: "MAT-C", name: "Gula Rafinasi", qty: 30 },
  { code: "MAT-A", name: "Botol PET", qty: 10 },
  { code: "MAT-B", name: "Label Tea", qty: 20 },
];

/** Isi kolom pertama tiap baris data, urut tampilan — tanpa baris header. */
function firstColumnValues() {
  const rows = screen.getAllByRole("row").slice(1);
  return rows.map((r) => within(r).getAllByRole("cell")[0].textContent);
}

describe("DataTable", () => {
  it("merender header dan seluruh baris", () => {
    render(<DataTable columns={columns} data={data} />);

    expect(screen.getByRole("columnheader", { name: /kode/i })).toBeDefined();
    expect(firstColumnValues()).toEqual(["MAT-C", "MAT-A", "MAT-B"]);
  });

  it("mengurutkan saat header diklik, dan membalik pada klik kedua", async () => {
    render(<DataTable columns={columns} data={data} />);

    await userEvent.click(screen.getByRole("button", { name: /kode/i }));
    expect(firstColumnValues()).toEqual(["MAT-A", "MAT-B", "MAT-C"]);

    await userEvent.click(screen.getByRole("button", { name: /kode/i }));
    expect(firstColumnValues()).toEqual(["MAT-C", "MAT-B", "MAT-A"]);
  });

  it("menyaring baris lewat kolom pencarian", async () => {
    render(<DataTable columns={columns} data={data} searchColumn="name" searchPlaceholder="Cari material" />);

    await userEvent.type(screen.getByPlaceholderText("Cari material"), "botol");

    expect(firstColumnValues()).toEqual(["MAT-A"]);
  });

  it("tidak menampilkan kotak pencarian bila searchColumn tidak diberikan", () => {
    render(<DataTable columns={columns} data={data} />);

    expect(screen.queryByRole("searchbox")).toBeNull();
  });

  it("kotak pencarian punya nama aksesibel, bukan sekadar placeholder", () => {
    render(<DataTable columns={columns} data={data} searchColumn="name" searchPlaceholder="Cari material" />);

    expect(screen.getByRole("searchbox", { name: "Cari material" })).toBeDefined();
  });

  it("memecah halaman sesuai pageSize dan bisa maju-mundur", async () => {
    render(<DataTable columns={columns} data={data} pageSize={2} />);

    expect(firstColumnValues()).toEqual(["MAT-C", "MAT-A"]);

    await userEvent.click(screen.getByRole("button", { name: /berikutnya/i }));
    expect(firstColumnValues()).toEqual(["MAT-B"]);

    await userEvent.click(screen.getByRole("button", { name: /sebelumnya/i }));
    expect(firstColumnValues()).toEqual(["MAT-C", "MAT-A"]);
  });

  it("tidak menampilkan kontrol halaman bila data muat satu halaman", () => {
    render(<DataTable columns={columns} data={data} pageSize={10} />);

    expect(screen.queryByRole("button", { name: /berikutnya/i })).toBeNull();
  });

  it("menyembunyikan kolom lewat menu tampilan kolom", async () => {
    render(<DataTable columns={columns} data={data} enableColumnVisibility />);

    await userEvent.click(screen.getByRole("button", { name: /kolom/i }));
    await userEvent.click(await screen.findByRole("menuitemcheckbox", { name: /nama/i }));

    expect(screen.queryByRole("columnheader", { name: /nama/i })).toBeNull();
    expect(screen.getByRole("columnheader", { name: /kode/i })).toBeDefined();
  });

  it("menampilkan pesan kosong saat tidak ada data", () => {
    render(<DataTable columns={columns} data={[]} emptyMessage="Belum ada material." />);

    expect(screen.getByText("Belum ada material.")).toBeDefined();
  });

  it("menampilkan pesan kosong saat penyaringan tidak menghasilkan baris", async () => {
    render(<DataTable columns={columns} data={data} searchColumn="name" emptyMessage="Tidak ada hasil." />);

    await userEvent.type(screen.getByRole("searchbox"), "zzz");

    expect(screen.getByText("Tidak ada hasil.")).toBeDefined();
  });
});
