import { NextResponse, type NextRequest } from "next/server";

import { TOKEN_COOKIE } from "@/lib/auth";

// Proteksi route grup (dashboard): tanpa token cookie → redirect ke /login.
// Middleware jalan di edge/server, jadi token disimpan di cookie (bukan localStorage).
const PROTECTED_PREFIXES = [
  "/dashboard",
  "/products",
  "/materials",
  "/boms",
  "/forecast",
  "/warehouse",
  "/settings",
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const needsAuth = PROTECTED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
  if (!needsAuth) return NextResponse.next();

  const token = request.cookies.get(TOKEN_COOKIE)?.value;
  if (!token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/products/:path*",
    "/materials/:path*",
    "/boms/:path*",
    "/forecast/:path*",
    "/warehouse/:path*",
    "/settings/:path*",
  ],
};
