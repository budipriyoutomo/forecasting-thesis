import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import DashboardLayout from "@/app/(dashboard)/layout";
import { MAIN_CONTENT_ID } from "@/components/layout/SkipLink";

vi.mock("@/components/layout/AppHeader", () => ({ AppHeader: () => null }));
vi.mock("@/components/layout/AppSidebar", () => ({ AppSidebar: () => null }));

describe("DashboardLayout", () => {
  // Area konten adalah flex item di samping sidebar. Tanpa min-w-0 ia tidak bisa menyusut di
  // bawah lebar isinya: tabel lebar mendorong seluruh halaman scroll horizontal di desktop
  // (terukur di Chrome 1280px: dokumen jadi 1536px), bukan tabelnya yang scroll.
  it("area konten boleh menyusut (min-w-0) supaya tabel lebar scroll di dalam wrapper-nya", () => {
    const { container } = render(<DashboardLayout>isi</DashboardLayout>);
    const main = container.querySelector(`#${MAIN_CONTENT_ID}`);
    expect(main?.parentElement?.className).toMatch(/\bmin-w-0\b/);
  });
});
