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

// GET /external-variables/{id}/values (CR v3.5 §5.2)
export interface ExternalVariableValue {
  product_id: string | null;
  period: string;
  value: number;
}

// PUT /external-variables/{id}/values — ubah/tambah nilai dari dialog "Ubah" (21 Nov 2026)
export interface ExternalVariableValueChange {
  period: string;
  value: number;
  product_id: string | null;
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
  /** CR v3.4 — baris yang periodenya digeser ke awal bulan (opsional: respons lama tidak punya) */
  normalized?: number;
  /** CR v3.4 — baris ganda di bulan yang sama, ditimpa baris terakhir */
  overwritten?: number;
  /** CR v3.4 §4.3 — "long" (variable_code,period,value) | "wide" (period + kolom per kode) */
  format?: "long" | "wide";
  /** Sel kosong / "-" / "NA" yang dilewati, per kode variabel */
  skipped?: Record<string, number>;
  warnings?: string[];
}

/** POST /external-variables/values/import?dry_run=true — validasi tanpa menyimpan. */
export interface ImportDryRunResult extends ImportResult {
  dry_run: true;
  valid: boolean;
  /** Maks. 100 pertama; total di n_errors */
  errors: string[];
  n_errors: number;
}

/** CR v3.4 §4.2 — GET /external-variables/coverage */
export interface ExternalVariableCoverage {
  variable_id: string;
  code: string;
  first_period: string | null;
  last_period: string | null;
  n_expected: number;
  n_filled: number;
  missing_periods: string[];
}
