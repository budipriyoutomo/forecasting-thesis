import { afterEach, describe, expect, it, vi } from "vitest";

import { downloadExport } from "@/lib/download";

afterEach(() => vi.restoreAllMocks());

function mockFileResponse(bytes: string, disposition?: string) {
  const headers = new Headers();
  if (disposition) headers.set("Content-Disposition", disposition);
  const spy = vi.fn(
    async (_input: RequestInfo | URL, _init?: RequestInit) =>
      new Response(new Blob([bytes]), { status: 200, headers }),
  );
  vi.stubGlobal("fetch", spy);
  return spy;
}

describe("downloadExport", () => {
  it("fetch dengan Bearer token dan memicu anchor download", async () => {
    const fetchSpy = mockFileResponse("PKxx", 'attachment; filename="reorder_r1.xlsx"');
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:x"),
      revokeObjectURL: vi.fn(),
    });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    const blob = await downloadExport("/api/v1/reorder/recommendations/export?run_id=r1", "tok", "fallback.xlsx");

    const [, init] = fetchSpy.mock.calls[0];
    expect((init?.headers as Record<string, string>).Authorization).toBe("Bearer tok");
    expect(clickSpy).toHaveBeenCalledOnce();
    expect(blob).toBeInstanceOf(Blob);
  });

  it("melempar error saat status non-OK", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("bad", { status: 404 })));

    await expect(downloadExport("/x", "tok", "f.xlsx")).rejects.toThrow(/gagal/i);
  });
});
