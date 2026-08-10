import { redirect } from "next/navigation";

// Root bukan halaman sendiri: langsung ke dashboard. Middleware yang memutuskan
// apakah user perlu dilempar ke /login (lihat src/middleware.ts).
export default function HomePage() {
  redirect("/dashboard");
}
