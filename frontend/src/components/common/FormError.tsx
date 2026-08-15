import { AlertCircle } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";

// Galat dari API saat submit — bukan galat validasi per field (itu tugas FormMessage
// dari ui/form.tsx). Sebelumnya empat form menuliskan paragraf destructive sendiri.
export function FormError({ message }: { message: string | null | undefined }) {
  if (!message) return null;

  return (
    <Alert variant="destructive" role="alert">
      <AlertCircle className="size-4" />
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}
