import { AppHeader } from "@/components/layout/AppHeader";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { MAIN_CONTENT_ID, SkipLink } from "@/components/layout/SkipLink";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";

// Shell untuk semua halaman terproteksi: sidebar + header konsisten.
// Tiap page cukup merender kontennya sendiri tanpa mengulang container/padding.
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <SkipLink />
      <AppSidebar />
      {/* min-w-0: tanpa ini tabel lebar mendorong seluruh halaman scroll horizontal di desktop. */}
      <SidebarInset className="min-w-0">
        <AppHeader />
        {/* tabIndex -1 supaya target lompatan benar-benar menerima fokus di semua peramban. */}
        <main id={MAIN_CONTENT_ID} tabIndex={-1} className="mx-auto w-full max-w-screen-2xl flex-1 p-4 outline-none md:p-6">
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
