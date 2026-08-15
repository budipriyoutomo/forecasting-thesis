import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MAIN_CONTENT_ID, SkipLink } from "@/components/layout/SkipLink";

describe("SkipLink", () => {
  it("menautkan ke area konten utama", () => {
    render(<SkipLink />);

    expect(screen.getByRole("link", { name: /lewati ke konten/i }).getAttribute("href")).toBe(
      `#${MAIN_CONTENT_ID}`,
    );
  });

  // Tautan ini hanya berguna bila tersembunyi secara visual tapi muncul saat difokus —
  // kalau di-`hidden` biasa, keyboard tidak akan pernah sampai ke sana.
  it("tersembunyi secara visual namun tetap dapat difokus", () => {
    render(<SkipLink />);
    const link = screen.getByRole("link", { name: /lewati ke konten/i });

    expect(link.className).toContain("sr-only");
    expect(link.className).toContain("focus:not-sr-only");
    expect(link.getAttribute("hidden")).toBeNull();
    expect(link.getAttribute("tabindex")).not.toBe("-1");
  });
});
