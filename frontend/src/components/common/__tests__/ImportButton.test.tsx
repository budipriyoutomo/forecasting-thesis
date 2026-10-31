import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ImportButton } from "@/components/common/ImportButton";

describe("ImportButton", () => {
  it("memanggil onFile dengan file terpilih (csv/xlsx)", async () => {
    const onFile = vi.fn();
    render(<ImportButton label="Import nilai" onFile={onFile} />);

    const file = new File(["a,b\n1,2"], "nilai.csv", { type: "text/csv" });
    await userEvent.upload(screen.getByLabelText(/import nilai/i), file);

    expect(onFile).toHaveBeenCalledWith(file);
    expect(screen.getByLabelText(/import nilai/i).getAttribute("accept")).toContain(".xlsx");
  });

  it("nonaktif saat pending", () => {
    render(<ImportButton label="Import" onFile={vi.fn()} pending />);
    expect((screen.getByRole("button", { name: /mengimpor/i }) as HTMLButtonElement).disabled).toBe(true);
  });
});
