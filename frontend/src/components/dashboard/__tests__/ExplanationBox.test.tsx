import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ExplanationBox } from "@/components/dashboard/ExplanationBox";

describe("ExplanationBox", () => {
  it("menampilkan penjelasan bila ada", () => {
    render(<ExplanationBox explanation="Metode ETS dipilih karena pola konsumsi mulus." />);

    expect(screen.getByText(/Kenapa metode ini/i)).toBeDefined();
    expect(screen.getByText(/pola konsumsi mulus/i)).toBeDefined();
  });

  it("tidak render apa pun bila penjelasan null", () => {
    const { container } = render(<ExplanationBox explanation={null} />);
    expect(container.firstChild).toBeNull();
  });
});
