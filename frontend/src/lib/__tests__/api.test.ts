import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/lib/api";

afterEach(() => {
  vi.restoreAllMocks();
});

function mockFetch(body: unknown) {
  const spy = vi.fn(
    async (_input: RequestInfo | URL, _init?: RequestInit) =>
      new Response(JSON.stringify(body), { status: 200 }),
  );
  vi.stubGlobal("fetch", spy);
  return spy;
}

describe("api.health", () => {
  it("memanggil GET /health di backend dan mengembalikan envelope sukses", async () => {
    const spy = mockFetch({ success: true, data: { status: "ok" } });

    const res = await api.health();

    expect(spy).toHaveBeenCalledTimes(1);
    expect(String(spy.mock.calls[0][0])).toMatch(/\/health$/);
    expect(res).toEqual({ success: true, data: { status: "ok" } });
  });

  it("meneruskan envelope error apa adanya (tidak melempar exception)", async () => {
    mockFetch({ success: false, error: { code: "RATE_LIMIT_EXCEEDED", message: "terlalu banyak request" } });

    const res = await api.health();

    expect(res.success).toBe(false);
    if (!res.success) {
      expect(res.error.code).toBe("RATE_LIMIT_EXCEEDED");
    }
  });
});

describe("api.auth.login", () => {
  it("POST /api/v1/auth/login dengan body JSON email+password", async () => {
    const spy = mockFetch({ success: true, data: { access_token: "t", token_type: "bearer" } });

    await api.auth.login("a@b.com", "secret");

    const [url, init] = spy.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/auth\/login$/);
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string)).toEqual({ email: "a@b.com", password: "secret" });
  });
});

describe("api.auth.me", () => {
  it("GET /api/v1/auth/me dengan Bearer token", async () => {
    const spy = mockFetch({ success: true, data: { id: "1", email: "a@b.com" } });

    await api.auth.me("tok-9");

    const [url, init] = spy.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/auth\/me$/);
    expect((init?.headers as Record<string, string>).Authorization).toBe("Bearer tok-9");
  });
});

describe("api.materials", () => {
  it("list GET /materials dengan Bearer token", async () => {
    const spy = mockFetch({ success: true, data: [] });

    await api.materials.list("tok");

    const [url, init] = spy.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/materials$/);
    expect((init?.headers as Record<string, string>).Authorization).toBe("Bearer tok");
  });

  it("create POST /materials dengan body JSON", async () => {
    const spy = mockFetch({ success: true, data: {} });
    const input = { code: "RM-1", name: "A", unit: "kg", lead_time_days: 3, moq: 10 };

    await api.materials.create(input, "tok");

    const [url, init] = spy.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/materials$/);
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string)).toEqual(input);
  });

  it("update PUT /materials/:id", async () => {
    const spy = mockFetch({ success: true, data: {} });

    await api.materials.update("m1", { name: "B" }, "tok");

    const [url, init] = spy.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/materials\/m1$/);
    expect(init?.method).toBe("PUT");
  });

  it("remove DELETE /materials/:id", async () => {
    const spy = mockFetch({ success: true, data: { id: "m1", deleted: true } });

    await api.materials.remove("m1", "tok");

    const [url, init] = spy.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/materials\/m1$/);
    expect(init?.method).toBe("DELETE");
  });
});

describe("api.uploads.create", () => {
  it("mengirim file sebagai multipart dengan header Authorization", async () => {
    const spy = mockFetch({ success: true, data: { session_id: "s-1" } });
    const file = new File(["material_code,date,quantity"], "data.csv", { type: "text/csv" });

    await api.uploads.create(file, "token-123");

    const [url, init] = spy.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/uploads$/);
    expect(init?.method).toBe("POST");
    expect((init?.headers as Record<string, string>).Authorization).toBe("Bearer token-123");
    expect(init?.body).toBeInstanceOf(FormData);
  });
});
