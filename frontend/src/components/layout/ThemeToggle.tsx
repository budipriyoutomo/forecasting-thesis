"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";

// Tombol tunggal, bukan menu tiga pilihan: planner cuma butuh terang/gelap.
// `resolvedTheme` dipakai (bukan `theme`) supaya saat setelan "system" aktif,
// tombol tetap membalik dari tampilan yang benar-benar terlihat user.
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={isDark ? "Beralih ke tema terang" : "Beralih ke tema gelap"}
      onClick={() => setTheme(isDark ? "light" : "dark")}
    >
      {isDark ? <Sun /> : <Moon />}
    </Button>
  );
}
