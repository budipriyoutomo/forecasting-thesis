import { afterEach, describe, expect, it, vi } from "vitest";

import { downloadExport } from "@/lib/download";
import { handleSessionExpired } from "@/lib/session";

vi.mock("@/lib/session", () => ({ handleSessionExpired: vi.fn() }));

afterEach(() => vi.restoreAllMocks());

function mockFileResponse(bytes: string, disposition?: string) {
  const headers = new Headers();
  if (disposition) headers.set("Content-Disposition", disposition);
  const spy = vi.fn(
    async (_input: RequestInfo | URL, _init?: RequestInit) =>
      // Body string, bukan new Blob([...]): di Node 22 (CI) Blob jsdom ≠ Blob undici sehingga
      // Response menstringify-nya jadi "[object Blob]".
      new Response(bytes, { status: 200, headers }),
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
    // Cek isi, bukan kelas: Response.blob() mengembalikan Blob realm Node, bukan jsdom.
    expect(blob.size).toBe("PKxx".length);
  });

  it("melempar error saat status non-OK", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("bad", { status: 404 })));

    await expect(downloadExport("/x", "tok", "f.xlsx")).rejects.toThrow(/gagal/i);
  });

  it("401 → sesi berakhir (logout + ke login), tetap melempar error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 401 })));

    await expect(downloadExport("/api/v1/x/export", "tok", "f.xlsx")).rejects.toThrow();
    expect(handleSessionExpired).toHaveBeenCalledOnce();
  });
});
