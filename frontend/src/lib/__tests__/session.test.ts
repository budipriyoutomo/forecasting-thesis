import { afterEach, describe, expect, it, vi } from "vitest";

import { getToken, setToken } from "@/lib/auth";
import { _resetSessionExpired, handleSessionExpired, safeNext } from "@/lib/session";

// CR v3.5 §5.3 — token kedaluwarsa/invalid: hapus cookie lalu kembali ke login.
afterEach(() => {
  _resetSessionExpired();
  document.cookie = "fiq_token=; path=/; max-age=0";
});

describe("handleSessionExpired", () => {
  it("menghapus token dan redirect ke /login dengan next = halaman saat ini", () => {
    setToken("tok");
    const navigate = vi.fn();

    handleSessionExpired(navigate, "/forecast/new/config?x=1");

    expect(getToken()).toBeNull();
    expect(navigate).toHaveBeenCalledWith("/login?next=%2Fforecast%2Fnew%2Fconfig%3Fx%3D1&reason=expired");
  });

  it("hanya redirect sekali walau banyak request 401 bersamaan", () => {
    const navigate = vi.fn();

    handleSessionExpired(navigate, "/dashboard");
    handleSessionExpired(navigate, "/dashboard");

    expect(navigate).toHaveBeenCalledTimes(1);
  });

  it("di halaman login tidak redirect lagi", () => {
    const navigate = vi.fn();
    handleSessionExpired(navigate, "/login?next=%2Fdashboard");
    expect(navigate).not.toHaveBeenCalled();
  });
});

describe("safeNext", () => {
  it.each([
    ["/materials", "/materials"],
    ["/forecast/new/config?x=1", "/forecast/new/config?x=1"],
    [null, "/dashboard"],
    ["", "/dashboard"],
    ["https://evil.example/x", "/dashboard"],
    ["//evil.example", "/dashboard"],
    ["/\\evil.example", "/dashboard"],
    ["/login", "/dashboard"],
  ])("%s → %s (cegah open redirect & loop ke login)", (input, expected) => {
    expect(safeNext(input)).toBe(expected);
  });
});
