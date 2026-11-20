# CHANGE REQUEST v3.5 — Keselarasan Frontend ↔ Backend & Matriks Role (RBAC)

> Tanggal: 20 Nov 2026 · Basis audit: repo `forecasting-thesis` commit `8c6a370` ("update kedatangan jadi ROP")
> Status: **Disetujui** (keputusan Budi, 20 Nov 2026) — siap dikerjakan

---

## 0. Ringkasan audit

| Area | Hasil |
|---|---|
| Endpoint (path + method + query param) | ✅ Semua pemanggilan `lib/api.ts` & `lib/exports.ts` punya endpoint di backend (86 route) |
| Field request/response (39 pasang Pydantic ↔ TS type) | ✅ Tidak ada field FE yang hilang di BE |
| Tipe data | ✅ Decimal → `string` konsisten (`model_dump(mode="json")`); input number → Decimal OK |
| Enum / literal | ✅ Identik (`Role`, `ReorderStatus`, `RopFormula`, `OrderQtyPolicy`, `CapacityMode`, status run/result) |
| Perubahan ROP terakhir | ✅ Tidak ada sisa rujukan `material-receipts` di FE; `receipt_qty` deprecated di kedua sisi |
| Frontend build & test | ✅ `tsc --noEmit` 0 error · vitest 301/301 lolos |
| Backend test | ⏳ Belum dijalankan dalam audit ini |

Temuan yang perlu diperbaiki: **4 utama** (§1–§4) + **gap kecil** (§5).

---

## 1. [HIGH] Error 422 / 500 tidak mengikuti envelope `{success, error}`

**Masalah**
- `backend/app/main.py` hanya punya `@app.exception_handler(AppError)`.
- Validasi Pydantic gagal → FastAPI mengembalikan `422 {"detail": [...]}`.
- Exception tak tertangani → `500` teks `Internal Server Error` (bukan JSON).
- FE `request()` di `frontend/src/lib/api.ts` langsung `res.json() as ApiResponse<T>`, lalu hooks memanggil `res.error.message` → **TypeError "Cannot read properties of undefined"**. Untuk 500, `res.json()` sendiri yang throw.
- Pesan validasi berbahasa Indonesia (mis. `_check_code` variabel eksternal, `Field(gt=0)` komponen material) tidak pernah sampai ke user.

**Perbaikan backend** — `backend/app/main.py`
```python
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", [])[1:])
    msg = first.get("msg", "Input tidak valid").removeprefix("Value error, ")
    return JSONResponse(status_code=422, content={
        "success": False,
        "error": {"code": "VALIDATION_ERROR", "message": f"{field}: {msg}" if field else msg},
    })

@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={
        "success": False, "error": {"code": f"HTTP_{exc.status_code}", "message": str(exc.detail)},
    })

@app.exception_handler(Exception)
async def unhandled_error_handler(request, exc):
    logger.exception("Unhandled error")  # tanpa stack trace ke client (AGENTS.md §4)
    return JSONResponse(status_code=500, content={
        "success": False, "error": {"code": "INTERNAL_ERROR", "message": "Terjadi kesalahan di server."},
    })
```

**Perbaikan frontend** — `frontend/src/lib/api.ts` `request()`
```ts
async function request<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, init);
  } catch {
    return { success: false, error: { code: "NETWORK_ERROR", message: "Tidak bisa terhubung ke server." } };
  }
  const body = await res.json().catch(() => null);
  if (body && typeof body === "object" && "success" in body) return body as ApiResponse<T>;
  return { success: false, error: { code: `HTTP_${res.status}`, message: `Permintaan gagal (status ${res.status}).` } };
}
```

**Kriteria selesai**
- [ ] Payload invalid ke `POST /external-variables` (kode bukan snake_case) → 422 envelope, pesan Indonesia tampil di form.
- [ ] Exception sengaja di service → 500 envelope, tanpa stack trace.
- [ ] Unit test FE: `request()` untuk body non-JSON, body `{detail}`, dan network error.
- [ ] Unit test BE: tiga handler di atas.

---

## 2. [HIGH] Lima halaman tidak diproteksi middleware

**Masalah** — `frontend/src/middleware.ts` `PROTECTED_PREFIXES` & `config.matcher` belum memuat:
`/inventory`, `/material-arrivals`, `/cost-templates`, `/external-variables`, `/forecast-settings`.
(`/forecast-settings` tidak tertangkap `/forecast` karena cek `startsWith("/forecast/")`.)
Sebaliknya `/settings` terdaftar padahal `app/(dashboard)/settings/` hanya berisi `.gitkeep`.

Dampak: tidak bocor data (API tetap butuh token), tetapi user tanpa login tidak di-redirect ke `/login` — halaman kosong / skeleton terus.

**Perbaikan**
- Turunkan daftar prefix dari satu sumber: `lib/navigation.ts` (semua `href` sidebar) supaya halaman baru otomatis terproteksi.
- `matcher` memakai negasi: `["/((?!login|_next|favicon.ico|api).*)"]`, lalu cek prefix di fungsi.
- Hapus folder `app/(dashboard)/settings/` atau isi bila memang direncanakan.

**Kriteria selesai**
- [ ] Test middleware: setiap `href` di `navigation.ts` tanpa cookie → redirect `/login?next=…`.
- [ ] Test regresi: menambah item navigasi baru otomatis terproteksi.

---

## 3. [HIGH] RBAC — matriks role final

### 3.1 Keputusan (20 Nov 2026)

| # | Pertanyaan | Keputusan |
|---|---|---|
| 1 | Import nilai variabel eksternal dipindah ke PPIC? | **Ya** — Admin + PPIC |
| 2 | Viewer boleh export? | **Ya** |
| 3 | Visibilitas run | **Opsi A untuk MVP** — semua run terlihat semua role (single-tenant). Opsi B (run "Final/Disetujui") dicatat sebagai post-MVP (§3.5) |
| 4 | Admin = superset PPIC? | **Ya** |

### 3.2 Matriks final

Legenda: ✅ tulis · 👁 baca · ❌ tidak ada akses

| Modul / aksi | Admin | PPIC | Purchasing | Viewer |
|---|:-:|:-:|:-:|:-:|
| Master data: produk, material, BOM, komponen material, kapasitas gudang, template biaya (CRUD + import) | ✅ | 👁 | 👁 | 👁 |
| Pengaturan Forecast | ✅ | 👁 | 👁 | 👁 |
| Variabel eksternal — definisi (CRUD, hapus nilai) | ✅ | 👁 | 👁 | 👁 |
| Variabel eksternal — import nilai bulanan (+ dry-run) | ✅ | ✅ | 👁 | 👁 |
| Upload demand | ✅ | ✅ | ❌ | ❌ |
| Import stok ERP & pemakaian aktual | ✅ | ✅ | ❌ | ❌ |
| Jalankan forecast run | ✅ | ✅ | ❌ | ❌ |
| Pilih metode (per produk / per run) | ✅ | ✅ | ❌ | ❌ |
| Override forecast & qty reorder | ✅ | ✅ | ❌ | ❌ |
| Generate reorder / plan / proyeksi stok | ✅ | ✅ | ❌ | ❌ |
| Adjust kapasitas (suggest / simpan / reset) | ✅ | ✅ | ❌ | ❌ |
| Lihat run, reorder, kedatangan material, proyeksi, metrik, biaya | ✅ | ✅ | ✅ | ✅ |
| Export (xlsx/pdf) & download template | ✅ | ✅ | ✅ | ✅ |
| Dashboard & audit trail override | ✅ | ✅ | ✅ | ✅ |

### 3.3 Pemetaan ke endpoint

| Action key | Role | Endpoint | Status sekarang → target |
|---|---|---|---|
| `master.write` | admin | `POST/PUT/DELETE /products*`, `/materials*`, `/boms*`, `/materials/{id}/components`, `DELETE /material-components/{id}`, `/warehouse/config*`, `/cost-templates*` (termasuk `/import`, `/bulk`, `/activate`) | admin → tetap |
| `settings.write` | admin | `PUT /forecast-settings` | admin → tetap |
| `extvar.define` | admin | `POST /external-variables`, `PUT/DELETE /external-variables/{id}`, `DELETE /external-variables/{id}/values` | admin → tetap |
| `extvar.import` | admin, ppic | `POST /external-variables/values/import` | admin → **admin, ppic** |
| `data.upload` | admin, ppic | `POST /uploads` | semua → **admin, ppic** |
| `data.import_stock` | admin, ppic | `POST /stock-snapshots/import`, `POST /material-usage/import` | admin, ppic → tetap |
| `forecast.run` | admin, ppic | `POST /forecast/runs` | semua → **admin, ppic** |
| `forecast.select` | admin, ppic | `POST /forecast/results/{id}/selection`, `POST /forecast/runs/{id}/selection` | semua → **admin, ppic** |
| `override.create` | admin, ppic | `POST /overrides` | semua → **admin, ppic** (FR-8.2) |
| `planning.run` | admin, ppic | `POST /reorder/recommendations`, `POST /forecast/runs/{id}/plan`, `POST /forecast/runs/{id}/stock-projection` | semua → **admin, ppic** |
| `capacity.adjust` | admin, ppic | `POST /forecast/runs/{id}/capacity-adjustments`, `/suggest`, `/reset` | semua → **admin, ppic** |
| `read` | semua | seluruh `GET` (termasuk `/export`, `/template`) | semua → tetap |

> Catatan: `/capacity-adjustments/suggest` hanya simulasi (tidak menyimpan), tetapi tetap `admin, ppic` karena hanya relevan bagi yang bisa menyimpan hasilnya.

### 3.4 Prasyarat: visibilitas run (Opsi A)

**Masalah** — Pengecekan kepemilikan `str(run.user_id) != str(user_id)` di:
- `backend/app/services/forecast_run_service.py` (≈ baris 166)
- `backend/app/services/reorder_service.py` (≈ baris 551)
- `backend/app/services/stock_projection_service.py` (≈ baris 257)
- serta repository `list_runs_for_user`, `get_latest_run_for_user` (dashboard), dan service lain yang menerima `user_id` untuk membaca run (metrics, warehouse validation, capacity adjustment, export, planning).

Akibatnya Purchasing **tidak pernah melihat** reorder buatan PPIC — bertentangan dengan user story #5 PRD.

**Perbaikan**
- Baca: hapus filter pemilik; run cukup harus ada (`ForecastRunNotFoundError` bila tidak ada).
- `GET /forecast/runs` → semua run terbaru dulu, tambah field `created_by` (nama/email) agar pemilih run di halaman Kedatangan Material jelas.
- Dashboard → "run terakhir" = run terbaru organisasi, bukan milik user.
- Tulis: tetap dicatat `user_id` pelaku (audit), RBAC dari §3.3 yang membatasi.
- Update docs: ARCHITECTURE §5 (aturan visibilitas), PRD FR-8.

### 3.5 Post-MVP — Opsi B: run "Final/Disetujui"
- Kolom `forecast_runs.approval_status` (`DRAFT` | `FINAL`), `approved_by`, `approved_at`; satu run FINAL aktif per periode perencanaan.
- `POST /forecast/runs/{id}/finalize` (admin, ppic) dengan alasan + audit trail.
- Purchasing & Viewer: default hanya melihat run FINAL. Alasan bisnis: PO dibuat dari rencana resmi, bukan draft/simulasi.

### 3.6 Penerapan teknis

**Backend — sumber tunggal izin** `backend/app/utils/permissions.py`
```python
PERMISSIONS: dict[str, tuple[str, ...]] = {
    "master.write":      ("admin",),
    "settings.write":    ("admin",),
    "extvar.define":     ("admin",),
    "extvar.import":     ("admin", "ppic"),
    "data.upload":       ("admin", "ppic"),
    "data.import_stock": ("admin", "ppic"),
    "forecast.run":      ("admin", "ppic"),
    "forecast.select":   ("admin", "ppic"),
    "override.create":   ("admin", "ppic"),
    "planning.run":      ("admin", "ppic"),
    "capacity.adjust":   ("admin", "ppic"),
}

def require_permission(action: str):
    return require_role(*PERMISSIONS[action])
```
Semua router memakai `dependencies=[Depends(require_permission("..."))]` — tidak ada lagi `require_role("admin")` tersebar.

**Frontend** `frontend/src/lib/permissions.ts`
```ts
import type { Role } from "@/types/auth";

export const PERMISSIONS = {
  "master.write": ["admin"],
  "settings.write": ["admin"],
  "extvar.define": ["admin"],
  "extvar.import": ["admin", "ppic"],
  "data.upload": ["admin", "ppic"],
  "data.import_stock": ["admin", "ppic"],
  "forecast.run": ["admin", "ppic"],
  "forecast.select": ["admin", "ppic"],
  "override.create": ["admin", "ppic"],
  "planning.run": ["admin", "ppic"],
  "capacity.adjust": ["admin", "ppic"],
} as const satisfies Record<string, readonly Role[]>;

export type Action = keyof typeof PERMISSIONS;
export const can = (role: Role | undefined, action: Action) =>
  !!role && (PERMISSIONS[action] as readonly Role[]).includes(role);
```
- Hook `useCan(action)` membaca `useMe()`.
- Tombol tulis (Tambah/Edit/Hapus/Import/Generate/Override/Pilih metode/Adjust) disembunyikan bila `!can(...)`. Halaman tetap bisa dibuka (baca).
- `/forecast/new` (upload + konfigurasi run): untuk Purchasing/Viewer tampilkan pesan "Hanya PPIC/Admin yang dapat menjalankan forecast" + link ke halaman baca.
- Respons `AUTH_FORBIDDEN` tetap ditangani (defensif) dengan toast yang jelas.

**Sinkronisasi** — test kontrak membandingkan peta BE dan FE (mis. BE expose `GET /api/v1/auth/permissions` *atau* test CI yang mem-parse keduanya) agar tidak drift.

### 3.7 Kriteria selesai
- [ ] `test_rbac.py`: setiap endpoint tulis × 4 role → 2xx / 403 sesuai matriks §3.2.
- [ ] Purchasing bisa `GET` reorder, proyeksi, kedatangan material milik run buatan PPIC.
- [ ] Purchasing `POST /overrides` → 403 `AUTH_FORBIDDEN`.
- [ ] Viewer bisa export semua laporan.
- [ ] PPIC bisa import nilai variabel eksternal, tidak bisa membuat/menghapus definisinya.
- [ ] Test FE per halaman: tombol tulis tidak dirender untuk role tanpa izin.
- [ ] Test sinkronisasi peta izin BE ↔ FE.
- [ ] Docs diperbarui: PRD FR-8.2 (matriks), ARCHITECTURE §5 (role per endpoint), AGENTS.md.

---

## 4. [MEDIUM] Label dashboard: "material" padahal produk

**Masalah** — `backend/app/services/dashboard_service.py`: `latest_run.n_materials = len(results)` padahal `forecast_results` per **produk**. FE `dashboard/page.tsx` menampilkan "… dari {run.n_materials} material".

**Perbaikan**
- BE: ganti `n_materials` → `n_products` di `latest_run` (`n_materials` level atas = jumlah master material tetap).
- FE: `types/dashboard.ts` & `dashboard/page.tsx` → "dari {run.n_products} produk".
- Update `test_dashboard_service.py`, `test_dashboard_api.py`, test FE terkait.

---

## 5. Gap kecil (backlog)

| # | Gap | Saran |
|---|---|---|
| 5.1 | Import produk/material/BOM (`POST /products|materials|boms/import`) tidak ada UI | Tambah `ImportButton` di halaman master data (role `master.write`) + template unduhan, **atau** tandai endpoint sebagai internal/seed |
| 5.2 | `GET /stock-snapshots`, `GET /material-usage`, `GET /uploads/{id}`, `GET /external-variables/{id}/values` tidak dipakai FE | Tampilkan riwayat di halaman Persediaan Material / Variabel Eksternal, atau dokumentasikan sebagai API-only |
| 5.3 | `AUTH_TOKEN_EXPIRED` / `AUTH_TOKEN_MISSING_OR_INVALID` tidak ditangani FE | Di `request()`/QueryProvider: kode tsb → `clearToken()` + redirect `/login?next=` |
| 5.4 | `ReorderRecommendation` FE tidak memuat `ordering_cost`, `holding_cost`, `total_inventory_cost`, `unit_price_used`, `holding_rate_used` | Tambahkan ke `types/reorder.ts` bila akan ditampilkan (rincian biaya per material) |
| 5.5 | `Material.dimension` dikirim BE tapi tidak ada di FE | Bila dimensi sudah tidak dipakai (kapasitas per grup sejak 19 Nov 2026), deprecate di BE; bila masih, tambah ke type & form |
| 5.6 | Asumsi kedatangan = periode yang sama (lead time < 1 bulan) | Halaman Kedatangan Material & proyeksi: badge peringatan untuk material dengan `lead_time_days ≥ 30` ("asumsi kedatangan tidak berlaku — lead time ≥ 1 periode"). Tetap dicatat sebagai batasan thesis |

---

## 6. Urutan pengerjaan yang disarankan

1. §1 envelope error (BE + FE) — fondasi agar pesan 403/422 tampil benar.
2. §2 middleware.
3. §3.4 visibilitas run (Opsi A) → §3.6 peta izin BE → FE `can()` → §3.7 test.
4. §4 label dashboard.
5. §5 backlog sesuai prioritas produk.