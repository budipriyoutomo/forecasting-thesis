"use client";

import { Badge } from "@/components/ui/badge";
import { formatNumber } from "@/lib/format";

export interface BomTreeNode {
  material_id?: string | null;
  product_id?: string;
  code: string | null;
  name: string | null;
  unit?: string | null;
  qty_per_unit?: number;
  level: number;
  purchased?: boolean;
  component_id?: string | null;
  children: BomTreeNode[];
}

// BOM multi-level (Fase 11.3): FG → material dibeli (level 1) → komponen (level 2+, informasi
// saja — Keputusan #4: Bottle dibeli jadi, Preform tidak dipesan).
function Node({ node, onRemove }: { node: BomTreeNode; onRemove?: (componentId: string) => void }) {
  return (
    <li role="treeitem" aria-level={node.level + 1} aria-selected={false} aria-expanded={node.children.length ? true : undefined}>
      <div className="flex flex-wrap items-center gap-2 py-1 text-sm">
        <span className="font-medium">{node.code}</span>
        <span className="text-muted-foreground">{node.name}</span>
        {node.qty_per_unit != null && (
          <span className="tabular-nums text-muted-foreground">
            × {formatNumber(node.qty_per_unit, 6)} {node.unit ?? ""}
          </span>
        )}
        {node.level === 1 && <Badge variant="secondary">Dibeli</Badge>}
        {node.level >= 2 && <Badge variant="outline">Informasi</Badge>}
        {onRemove && node.component_id && (
          <button
            type="button"
            className="text-xs text-destructive underline-offset-2 hover:underline"
            onClick={() => onRemove(node.component_id as string)}
          >
            Lepas komponen
          </button>
        )}
      </div>
      {node.children.length > 0 && (
        <ul role="group" className="ml-5 border-l pl-3">
          {node.children.map((c) => (
            <Node key={`${c.material_id}-${c.component_id ?? "l1"}`} node={c} onRemove={onRemove} />
          ))}
        </ul>
      )}
    </li>
  );
}

export function BomTree({ tree, onRemove }: { tree: BomTreeNode; onRemove?: (componentId: string) => void }) {
  return (
    <ul role="tree" aria-label={`Struktur BOM ${tree.code}`} className="rounded-lg border p-3">
      <Node node={tree} onRemove={onRemove} />
    </ul>
  );
}
