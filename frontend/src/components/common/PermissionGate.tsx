"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { useMe } from "@/hooks/useAuth";
import { can, type Action } from "@/lib/permissions";

// Gate satu halaman tulis penuh (CR v3.5 §3.6): role tanpa izin melihat pesan + link ke
// halaman baca, bukan form yang pasti ditolak 403. Selama profil dimuat tidak merender
// apa pun supaya pesan "tidak diizinkan" tidak berkedip untuk PPIC/Admin.
export function PermissionGate({
  action,
  message,
  readHref,
  readLabel,
  children,
}: {
  action: Action;
  message: string;
  readHref: string;
  readLabel: string;
  children: ReactNode;
}) {
  const { data: user, isPending } = useMe();
  if (isPending && !user) return null;
  if (can(user?.role, action)) return <>{children}</>;
  return (
    <Alert>
      <AlertDescription>
        {message}{" "}
        <Link href={readHref} className="font-medium underline underline-offset-4">
          Lihat {readLabel}
        </Link>
        .
      </AlertDescription>
    </Alert>
  );
}
