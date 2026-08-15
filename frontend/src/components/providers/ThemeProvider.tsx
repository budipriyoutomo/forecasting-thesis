"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ComponentProps } from "react";

// Tema disimpan next-themes di localStorage dan diterapkan sebagai class pada <html>,
// selaras dengan `darkMode: ["class"]` di tailwind.config.ts.
export function ThemeProvider({ children, ...props }: ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
