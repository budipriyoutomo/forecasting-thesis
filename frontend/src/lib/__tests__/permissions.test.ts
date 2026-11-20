import { describe, expect, it } from "vitest";

import { can, PERMISSIONS, type Action } from "@/lib/permissions";
import type { Role } from "@/types/auth";

// CR v3.5 §3.2 — matriks role final. Peta yang sama di backend
// (app/utils/permissions.py) dicek oleh backend/tests/unit/test_rbac.py.
const ROLES: Role[] = ["admin", "ppic", "purchasing", "viewer"];

describe("can()", () => {
  it.each([
    ["master.write", ["admin"]],
    ["settings.write", ["admin"]],
    ["extvar.define", ["admin"]],
    ["extvar.import", ["admin", "ppic"]],
    ["data.upload", ["admin", "ppic"]],
    ["forecast.run", ["admin", "ppic"]],
    ["override.create", ["admin", "ppic"]],
    ["capacity.adjust", ["admin", "ppic"]],
  ] as [Action, Role[]][])("%s hanya untuk %j", (action, allowed) => {
    for (const role of ROLES) expect(can(role, action)).toBe(allowed.includes(role));
  });

  it("admin = superset PPIC", () => {
    for (const action of Object.keys(PERMISSIONS) as Action[]) {
      if (can("ppic", action)) expect(can("admin", action)).toBe(true);
    }
  });

  it("purchasing & viewer tidak punya aksi tulis apa pun", () => {
    for (const action of Object.keys(PERMISSIONS) as Action[]) {
      expect(can("purchasing", action)).toBe(false);
      expect(can("viewer", action)).toBe(false);
    }
  });

  it("role belum diketahui (profil belum dimuat) → tidak boleh", () => {
    expect(can(undefined, "master.write")).toBe(false);
  });
});
