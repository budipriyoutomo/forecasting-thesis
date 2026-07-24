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

describe("api.dashboard.summary", () => {
  it("GET /dashboard/summary dengan Bearer token", async () => {
    const spy = mockFetch({ success: true, data: {} });

    await api.dashboard.summary("tok");

    const [url, init] = spy.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/dashboard\/summary$/);
    expect((init?.headers as Record<string, string>).Authorization).toBe("Bearer tok");
  });
});

describe("api.forecast", () => {
  it("createRun POST /forecast/runs dengan body JSON", async () => {
    const spy = mockFetch({ success: true, data: { run: {}, results: [] } });

    await api.forecast.createRun({ material_ids: ["m1"], horizon: 30, method: null }, "tok");

    const [url, init] = spy.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/forecast\/runs$/);
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string)).toEqual({
      material_ids: ["m1"],
      horizon: 30,
      method: null,
    });
  });

  it("methods GET /forecast/methods", async () => {
    const spy = mockFetch({ success: true, data: { methods: ["ets"] } });

    await api.forecast.methods("tok");

    expect(String(spy.mock.calls[0][0])).toMatch(/\/api\/v1\/forecast\/methods$/);
  });

  it("getRun GET /forecast/runs/:id", async () => {
    const spy = mockFetch({ success: true, data: { run: {}, results: [] } });

    await api.forecast.getRun("r1", "tok");

    expect(String(spy.mock.calls[0][0])).toMatch(/\/api\/v1\/forecast\/runs\/r1$/);
  });
});

describe("api.reorder", () => {
  it("generate POST /reorder/recommendations dengan run_id + current_stock", async () => {
    const spy = mockFetch({ success: true, data: [] });

    await api.reorder.generate("r1", { m1: 5 }, "tok");

    const [url, init] = spy.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/reorder\/recommendations$/);
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string)).toEqual({ run_id: "r1", current_stock: { m1: 5 } });
  });

  it("list GET dengan filter status di query", async () => {
    const spy = mockFetch({ success: true, data: [] });

    await api.reorder.list("r1", "urgent", "tok");

    expect(String(spy.mock.calls[0][0])).toMatch(/run_id=r1/);
    expect(String(spy.mock.calls[0][0])).toMatch(/status=urgent/);
  });
});

describe("api.overrides", () => {
  it("create POST /overrides dengan body lengkap", async () => {
    const spy = mockFetch({ success: true, data: {} });
    const input = {
      target_type: "reorder_recommendation" as const,
      target_id: "rec1",
      new_value: { recommended_order_qty: 120 },
      reason: "alasan valid",
    };

    await api.overrides.create(input, "tok");

    const [url, init] = spy.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/overrides$/);
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string)).toEqual(input);
  });

  it("list GET /overrides?target_id=", async () => {
    const spy = mockFetch({ success: true, data: [] });

    await api.overrides.list("rec1", "tok");

    expect(String(spy.mock.calls[0][0])).toMatch(/\/api\/v1\/overrides\?target_id=rec1$/);
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

describe("api.uploads.list", () => {
  it("GET /uploads dengan Bearer token", async () => {
    const spy = mockFetch({ success: true, data: [] });

    await api.uploads.list("tok");

    const [url, init] = spy.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/v1\/uploads$/);
    expect((init?.headers as Record<string, string>).Authorization).toBe("Bearer tok");
  });
});
