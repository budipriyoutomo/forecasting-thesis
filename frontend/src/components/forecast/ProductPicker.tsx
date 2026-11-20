"use client";

import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate } from "@/lib/format";
import type { Product, ProductDemandCoverage } from "@/types/product";

// CR v3.6 §5 — pemilihan produk sebelum run: search, "pilih semua hasil filter", dan cakupan
// histori demand (jumlah bulan & periode terakhir) supaya planner tahu produk mana yang datanya
// cukup. `minPeriods` = BACKTEST_MIN_PERIODS backend (default 12) — di bawahnya ditandai.
export function ProductPicker({
  products,
  coverage = [],
  selected,
  onChange,
  minPeriods = 12,
}: {
  products: Product[];
  coverage?: ProductDemandCoverage[];
  selected: string[];
  onChange: (ids: string[]) => void;
  minPeriods?: number;
}) {
  const [query, setQuery] = useState("");
  const cov = useMemo(() => new Map(coverage.map((c) => [c.product_id, c])), [coverage]);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? products.filter((p) => `${p.code} ${p.name}`.toLowerCase().includes(q)) : products;
  }, [products, query]);
  const chosen = new Set(selected);
  const allFiltered = filtered.length > 0 && filtered.every((p) => chosen.has(p.id));
  const someFiltered = filtered.some((p) => chosen.has(p.id));

  const toggle = (id: string) => onChange(chosen.has(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  const toggleAll = () => {
    const ids = new Set(filtered.map((p) => p.id));
    onChange(allFiltered ? selected.filter((id) => !ids.has(id)) : [...new Set([...selected, ...ids])]);
  };

  return (
    <div className="flex flex-col gap-3">
      <Input
        type="search"
        aria-label="Cari produk"
        placeholder="Cari kode / nama produk…"
        className="h-9 max-w-xs"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="max-h-[420px] overflow-auto rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <Checkbox
                  aria-label="Pilih semua hasil filter"
                  checked={allFiltered ? true : someFiltered ? "indeterminate" : false}
                  onCheckedChange={toggleAll}
                />
              </TableHead>
              <TableHead>Kode</TableHead>
              <TableHead>Nama</TableHead>
              <TableHead className="text-right">Histori</TableHead>
              <TableHead>Data terakhir</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((p) => {
              const c = cov.get(p.id);
              const n = c?.n_periods ?? null;
              const short = n !== null && n < minPeriods;
              return (
                <TableRow key={p.id} data-state={chosen.has(p.id) ? "selected" : undefined}>
                  <TableCell>
                    <Checkbox
                      aria-label={`Pilih ${p.code}`}
                      checked={chosen.has(p.id)}
                      onCheckedChange={() => toggle(p.id)}
                    />
                  </TableCell>
                  <TableCell className="font-medium">{p.code}</TableCell>
                  <TableCell>{p.name}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {n === null ? (
                      "—"
                    ) : (
                      <span className="inline-flex items-center gap-2">
                        {n} bulan
                        {short && <Badge variant="warning">kurang dari {minPeriods}</Badge>}
                      </span>
                    )}
                  </TableCell>
                  <TableCell>{formatDate(c?.last_period ?? null)}</TableCell>
                </TableRow>
              );
            })}
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-sm text-muted-foreground">
                  Tidak ada produk yang cocok.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
