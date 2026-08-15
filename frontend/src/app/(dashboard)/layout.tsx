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
      <SidebarInset>
        <AppHeader />
        {/* tabIndex -1 supaya target lompatan benar-benar menerima fokus di semua peramban. */}
        <main id={MAIN_CONTENT_ID} tabIndex={-1} className="flex-1 p-4 outline-none md:p-6">
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
