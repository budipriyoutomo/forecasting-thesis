"use client";

import {
  type ColumnDef,
  type ColumnFiltersState,
  type SortingState,
  type VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ChevronsUpDown, SlidersHorizontal } from "lucide-react";
import { type ReactNode, useState } from "react";

import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// Tabel data bersama: sorting, pencarian, halaman, dan tampil/sembunyi kolom.
//
// TanStack Table dipatok ke v8 — v9 (mayor saat ini di npm) memakai API yang
// berbeda (`useTable`, `createCoreRowModel`, sistem feature), sementara dokumentasi
// data table shadcn yang jadi acuan proyek ini seluruhnya v8. Pilihan itu sengaja
// dikurung di berkas ini saja supaya bisa dipindah tanpa menyentuh halaman.

export interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  /** accessorKey kolom yang disaring kotak pencarian. Tanpa ini kotak tidak muncul. */
  searchColumn?: string;
  searchPlaceholder?: string;
  /** Jumlah baris per halaman. Kontrol halaman disembunyikan bila data muat satu halaman. */
  pageSize?: number;
  enableColumnVisibility?: boolean;
  emptyMessage?: string;
  /** Kontrol tambahan di baris alat, sebelah kanan kotak pencarian. */
  toolbar?: ReactNode;
}

export function DataTable<TData, TValue>({
  columns,
  data,
  searchColumn,
  searchPlaceholder = "Cari…",
  pageSize = 10,
  enableColumnVisibility = false,
  emptyMessage = "Tidak ada data.",
  toolbar,
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});

  const table = useReactTable({
    data,
    columns,
    state: { sorting, columnFilters, columnVisibility },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize } },
  });

  const rows = table.getRowModel().rows;
  const showPagination = table.getPageCount() > 1;
  const hasToolbar = Boolean(searchColumn) || enableColumnVisibility || Boolean(toolbar);

  return (
    <div className="flex flex-col gap-3">
      {hasToolbar && (
        <div className="flex flex-wrap items-center gap-2">
          {searchColumn && (
            <Input
              className="h-9 max-w-xs"
              type="search"
              // Placeholder bukan label: ia hilang begitu user mengetik dan tidak
              // selalu dibacakan screen reader.
              aria-label={searchPlaceholder}
              placeholder={searchPlaceholder}
              value={(table.getColumn(searchColumn)?.getFilterValue() as string) ?? ""}
              onChange={(e) => table.getColumn(searchColumn)?.setFilterValue(e.target.value)}
            />
          )}
          <div className="ml-auto flex items-center gap-2">
            {toolbar}
            {enableColumnVisibility && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <SlidersHorizontal />
                    Kolom
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {table
                    .getAllColumns()
                    .filter((c) => c.getCanHide())
                    .map((column) => (
                      <DropdownMenuCheckboxItem
                        key={column.id}
                        className="capitalize"
                        checked={column.getIsVisible()}
                        onCheckedChange={(value) => column.toggleVisibility(!!value)}
                      >
                        {String(column.columnDef.header ?? column.id)}
                      </DropdownMenuCheckboxItem>
                    ))}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        </div>
      )}

      {rows.length === 0 ? (
        <EmptyState message={emptyMessage} />
      ) : (
        // Tabel lebar harus menggulir di dalam kotaknya sendiri, bukan mendorong
        // lebar halaman — ini yang bikin tabel terjepit di layar sempit.
        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id}>
                  {headerGroup.headers.map((header) => {
                    const label = header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext());
                    const sorted = header.column.getIsSorted();

                    return (
                      <TableHead key={header.id} className="whitespace-nowrap">
                        {header.column.getCanSort() && label !== null ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="-ml-3 h-8 data-[state=open]:bg-accent"
                            onClick={header.column.getToggleSortingHandler()}
                          >
                            {label}
                            {sorted === "asc" ? (
                              <ArrowUp />
                            ) : sorted === "desc" ? (
                              <ArrowDown />
                            ) : (
                              <ChevronsUpDown className="opacity-50" />
                            )}
                          </Button>
                        ) : (
                          label
                        )}
                      </TableHead>
                    );
                  })}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.id} data-state={row.getIsSelected() && "selected"}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {showPagination && (
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm text-muted-foreground">
            Halaman {table.getState().pagination.pageIndex + 1} dari {table.getPageCount()}
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
            >
              Sebelumnya
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
            >
              Berikutnya
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
