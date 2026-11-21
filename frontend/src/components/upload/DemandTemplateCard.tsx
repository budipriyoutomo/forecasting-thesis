"use client";

import { ImportTemplateCard } from "@/components/common/ImportTemplateCard";
import { DEMAND_TEMPLATE } from "@/lib/templates";

// Template unduhan histori demand — kini memakai kartu template bersama (ImportTemplateCard).
export function DemandTemplateCard() {
  return <ImportTemplateCard template={DEMAND_TEMPLATE} />;
}
