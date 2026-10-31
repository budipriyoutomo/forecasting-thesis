// Master data variabel eksternal (Fase 11.2b) — cocok dengan backend/app/schemas/external_variable.py
export type ExternalValueType = "numeric" | "flag";
export type ExternalScope = "global" | "product";

export interface ExternalVariable {
  id: string;
  code: string;
  name: string;
  value_type: ExternalValueType;
  scope: ExternalScope;
  unit: string | null;
  description: string | null;
  is_active: boolean;
  n_values: number;
}

export interface ExternalVariableInput {
  code?: string;
  name?: string;
  value_type?: ExternalValueType;
  scope?: ExternalScope;
  unit?: string | null;
  description?: string | null;
  is_active?: boolean;
}

export interface ImportResult {
  imported: number;
}
