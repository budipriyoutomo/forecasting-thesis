import { AppHeader } from "@/components/layout/AppHeader";

// Shell untuk semua halaman terproteksi: header + navigasi konsisten.
// Tiap page cukup merender kontennya sendiri tanpa mengulang container/padding.
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />
      <main className="container flex-1 py-8">{children}</main>
    </div>
  );
}
