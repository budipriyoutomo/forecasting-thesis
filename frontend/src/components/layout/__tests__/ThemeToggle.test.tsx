import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ThemeToggle } from "@/components/layout/ThemeToggle";

const setTheme = vi.fn();
const useThemeMock = vi.fn(() => ({ resolvedTheme: "light", setTheme }));
vi.mock("next-themes", () => ({ useTheme: () => useThemeMock() }));

afterEach(() => {
  setTheme.mockReset();
});

describe("ThemeToggle", () => {
  it("beralih ke tema gelap saat tema aktif terang", async () => {
    useThemeMock.mockReturnValue({ resolvedTheme: "light", setTheme });
    render(<ThemeToggle />);

    await userEvent.click(screen.getByRole("button"));

    expect(setTheme).toHaveBeenCalledWith("dark");
  });

  it("beralih ke tema terang saat tema aktif gelap", async () => {
    useThemeMock.mockReturnValue({ resolvedTheme: "dark", setTheme });
    render(<ThemeToggle />);

    await userEvent.click(screen.getByRole("button"));

    expect(setTheme).toHaveBeenCalledWith("light");
  });

  it("punya label aksesibel", () => {
    useThemeMock.mockReturnValue({ resolvedTheme: "light", setTheme });
    render(<ThemeToggle />);

    expect(screen.getByRole("button", { name: /tema/i })).toBeDefined();
  });
});
