"use client";

// Penjelasan bahasa natural per hasil forecast (FR — untuk user non-teknis).
export function ExplanationBox({ explanation }: { explanation: string | null }) {
  if (!explanation) return null;
  return (
    <div className="rounded-md border-l-4 border-primary bg-muted/50 p-3 text-sm">
      <p className="mb-1 font-medium">Kenapa metode ini?</p>
      <p className="text-muted-foreground">{explanation}</p>
    </div>
  );
}
