import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ImportTemplateCard } from "@/components/common/ImportTemplateCard";
import type { ImportTemplateSpec } from "@/lib/templates";

const SPEC: ImportTemplateSpec = {
  title: "Template stok",
  filename: "template-stok.csv",
  columns: [
    { name: "kode", required: true, description: "Kode material.", example: "M-1" },
    { name: "std", required: false, conditional: true, description: "Standar.", example: "5" },
    { name: "uom", required: false, description: "Satuan.", example: "PCS" },
  ],
  sampleRows: [["M-1", null, "PCS"]],
  notes: ["Catatan pengisian pertama."],
};

describe("ImportTemplateCard", () => {
  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => "blob:template");
    URL.revokeObjectURL = vi.fn();
  });

  it("menampilkan kolom dengan status wajib/bersyarat/opsional dan catatan pengisian", () => {
    render(<ImportTemplateCard template={SPEC} />);

    expect(screen.getByText("Template stok")).toBeDefined();
    expect(screen.getByText("kode")).toBeDefined();
    expect(screen.getByText("Wajib")).toBeDefined();
    expect(screen.getByText("Bersyarat")).toBeDefined();
    expect(screen.getByText("Opsional")).toBeDefined();
    expect(screen.getByText("Catatan pengisian pertama.")).toBeDefined();
  });

  it("mengunduh CSV sesuai spesifikasi (sel null jadi kosong)", async () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    render(<ImportTemplateCard template={SPEC} />);

    await userEvent.click(screen.getByRole("button", { name: /unduh template/i }));

    const blob = (URL.createObjectURL as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0] as Blob;
    expect(blob.type).toContain("text/csv");
    const text = await new Promise<string>((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.readAsText(blob);
    });
    expect(text).toBe("kode,std,uom\nM-1,,PCS\n");
    expect((click.mock.contexts[0] as HTMLAnchorElement).download).toBe("template-stok.csv");
  });
});
