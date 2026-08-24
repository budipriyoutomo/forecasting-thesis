import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DemandTemplateCard } from "@/components/upload/DemandTemplateCard";

describe("DemandTemplateCard", () => {
  beforeEach(() => {
    // jsdom tidak punya URL.createObjectURL; unduhan dipicu lewat blob URL.
    URL.createObjectURL = vi.fn(() => "blob:template");
    URL.revokeObjectURL = vi.fn();
  });

  it("menampilkan kolom wajib dan opsional beserta contoh isinya", () => {
    render(<DemandTemplateCard />);

    // `product_code` muncul di tabel kolom dan di catatan bawah kartu.
    expect(screen.getAllByText("product_code").length).toBeGreaterThan(0);
    expect(screen.getByText("forecast_existing")).toBeDefined();
    expect(screen.getAllByText(/wajib/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/opsional/i).length).toBeGreaterThan(0);
  });

  it("mengunduh CSV template saat tombol diklik", async () => {
    render(<DemandTemplateCard />);

    await userEvent.click(screen.getByRole("button", { name: /unduh template/i }));

    expect(URL.createObjectURL).toHaveBeenCalled();
    const blob = (URL.createObjectURL as unknown as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as Blob;
    expect(blob.type).toContain("text/csv");
  });
});
