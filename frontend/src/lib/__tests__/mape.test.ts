import { describe, expect, it } from "vitest";

import { mapeLabel } from "@/lib/mape";

describe("mapeLabel (Lewis)", () => {
  it.each([
    [5, "Sangat baik"],
    [10, "Baik"],
    [20, "Cukup"],
    [49.9, "Cukup"],
    [50, "Buruk"],
  ])("%s%% → %s", (v, label) => {
    expect(mapeLabel(v)).toBe(label);
  });

  it("null / tak hingga → tidak terdefinisi", () => {
    expect(mapeLabel(null)).toBe("Tidak terdefinisi");
    expect(mapeLabel(Number.POSITIVE_INFINITY)).toBe("Tidak terdefinisi");
  });
});
