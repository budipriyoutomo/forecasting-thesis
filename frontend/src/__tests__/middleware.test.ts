import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { TOKEN_COOKIE } from "@/lib/auth";
import { NAV_GROUPS } from "@/lib/navigation";
import { config, isProtectedPath, middleware } from "@/middleware";

// CR v3.5 §2 — prefix yang diproteksi diturunkan dari navigasi sidebar, jadi setiap
// halaman di menu otomatis butuh login.
const NAV_HREFS = NAV_GROUPS.flatMap((g) => g.items.map((i) => i.href));

function req(path: string, token?: string) {
  const r = new NextRequest(new URL(path, "http://localhost"));
  if (token) r.cookies.set(TOKEN_COOKIE, token);
  return r;
}

describe("middleware proteksi route", () => {
  it.each(NAV_HREFS)("%s tanpa cookie → redirect /login?next=…", (href) => {
    const res = middleware(req(href));

    expect(res.status).toBe(307);
    const location = new URL(res.headers.get("location") as string);
    expect(location.pathname).toBe("/login");
    expect(location.searchParams.get("next")).toBe(href);
  });

  it.each(NAV_HREFS)("%s dengan cookie → diteruskan", (href) => {
    const res = middleware(req(href, "tok"));

    expect(res.headers.get("location")).toBeNull();
  });

  it("sub-halaman ikut terproteksi", () => {
    expect(isProtectedPath("/material-arrivals/abc")).toBe(true);
    expect(isProtectedPath("/forecast/run-1/results")).toBe(true);
    expect(isProtectedPath("/forecast-settings")).toBe(true);
  });

  it("halaman publik tidak diproteksi", () => {
    expect(isProtectedPath("/login")).toBe(false);
    expect(isProtectedPath("/")).toBe(false);
    // /forecast tidak boleh ikut menangkap prefix yang hanya mirip.
    expect(isProtectedPath("/forecastx")).toBe(false);
  });

  it("matcher mengecualikan login, aset Next, favicon, dan api", () => {
    const pattern = new RegExp(`^${config.matcher[0]}$`);
    expect(pattern.test("/inventory")).toBe(true);
    expect(pattern.test("/login")).toBe(false);
    expect(pattern.test("/_next/static/chunk.js")).toBe(false);
    expect(pattern.test("/favicon.ico")).toBe(false);
  });
});
