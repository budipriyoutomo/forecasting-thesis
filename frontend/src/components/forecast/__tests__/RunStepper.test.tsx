import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RunStepper } from "@/components/forecast/RunStepper";
import { deriveRunSteps } from "@/lib/runSteps";

const steps = deriveRunSteps({
  run: { status: "COMPLETED", n_products: 3, n_completed: 3, n_failed: 0, n_pending_selection: 0 },
  hasPlanning: true,
});

describe("RunStepper", () => {
  // 5 langkah sebaris baru di xl: di lg (1024px) area konten di samping sidebar hanya ~720px,
  // sehingga 5 kolom membuat tiap kartu ~136px dan label/hint terpotong-potong.
  it("5 langkah sebaris hanya mulai xl; lg memakai 3 kolom", () => {
    render(<RunStepper steps={steps} active="reorder" onChange={() => {}} />);
    const list = screen.getByRole("list");
    expect(list.className).toMatch(/\bxl:grid-cols-5\b/);
    expect(list.className).toMatch(/\blg:grid-cols-3\b/);
    expect(list.className).not.toMatch(/\blg:grid-cols-5\b/);
  });
});
