// Cocok dengan backend/app/schemas/override.py — jaga urutan & isi tetap sama.
export type OverrideTargetType = "forecast_result" | "reorder_recommendation";

export interface Override {
  id: string;
  target_type: OverrideTargetType;
  target_id: string;
  user_id: string;
  previous_value: Record<string, unknown> | null;
  new_value: Record<string, unknown>;
  reason: string;
  created_at: string | null;
}

export interface OverrideInput {
  target_type: OverrideTargetType;
  target_id: string;
  new_value: Record<string, unknown>;
  reason: string;
}
