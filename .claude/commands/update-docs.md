---
description: Sinkronkan docs/PRD.md & docs/ARCHITECTURE.md (dan TASK_BREAKDOWN.md) dengan fitur yang sudah diimplementasi tapi belum terdokumentasi. TIDAK commit.
---

Update dokumen konteks produk/teknis berdasarkan perubahan yang BELUM tercermin di dalamnya. **JANGAN commit/push** — user yang review & commit sendiri.

**HEMAT TOKEN:** cek `--stat` dulu sebelum baca diff penuh; baca hanya file yang relevan dengan delta yang doc-worthy.

## 1. Tentukan scope per dokumen

Tiap dokumen disinkronkan dari commit TERAKHIR ia diubah — bukan dari satu titik bersama, karena PRD dan Architecture bisa drift dengan kecepatan berbeda:

```bash
PRD_BASE=$(git log -1 --format=%H -- docs/PRD.md)
ARCH_BASE=$(git log -1 --format=%H -- docs/ARCHITECTURE.md)

git diff "$PRD_BASE" --stat -- . ':(exclude)docs/PRD.md' ':(exclude)docs/ARCHITECTURE.md'
git diff "$ARCH_BASE" --stat -- . ':(exclude)docs/PRD.md' ':(exclude)docs/ARCHITECTURE.md'
```

Ini menangkap commit yang sudah masuk MAUPUN working tree yang belum commit (satu base vs kondisi sekarang) — jadi seluruh delta yang terakumulasi sejak dokumen terakhir disentuh ikut tertangkap, termasuk dari sesi-sesi sebelumnya. Kalau `*_BASE` kosong (dokumen belum pernah dicommit terpisah), pakai commit pertama repo sebagai base.

## 2. Identifikasi delta yang doc-worthy

Dari diff, cari perubahan yang mengubah kontrak/perilaku yang terdokumentasi — BUKAN detail implementasi internal:
- Endpoint baru/berubah/dihapus, atau field request/response berubah.
- Kolom/tabel DB baru atau berubah (termasuk migrasi Alembic baru).
- **Error code baru** — harus konsisten di tiga tempat: kode, `AGENTS.md` §4, `docs/ARCHITECTURE.md` §5.
- **Engine forecasting baru atau berubah** — nama metode, kuadran yang didukung, minimum data, posisinya di `registry.py`.
- **Perubahan mekanisme seleksi model** — rumus/bobot scoring, guardrail, metrik backtest, aturan fallback & mode manual.
- **Env var / config baru** (`FORECAST_ENGINES_ENABLED`, `SCORING_WEIGHT_*`, `BACKTEST_MIN_PERIODS`, dst) — cek `backend/.env.example` juga sinkron.
- Flow user baru atau berubah (upload → validasi → forecast run → override → export).
- Aturan storage/lifecycle file R2 (§7) yang berubah.
- Fase di `docs/TASK_BREAKDOWN.md` yang sudah selesai tapi belum ditandai.
- Keputusan arsitektur yang MENYIMPANG dari `AGENTS.md` → wajib dicatat di `docs/RECONCILIATION.md`.

Abaikan: refactor internal tanpa perubahan kontrak, rename variabel lokal, bugfix yang tidak mengubah behavior terdokumentasi, perubahan test-only (kecuali ia menyingkap business rule baru yang belum pernah tertulis).

## 3. Update — edit bedah, JANGAN tulis ulang

**`docs/PRD.md`** — dokumen produk. Update hanya kalau delta menyentuh scope/user story/acceptance criteria:
- Tandai delta dengan **[NEW]** / **[CHANGED]** / **[DROPPED]** inline, konsisten dengan gaya existing di sekitarnya.
- Kalau delta menutup salah satu known gap / open question yang tercatat, update atau hapus entry tersebut.
- Update tanggal sync di baris pembuka (`per YYYY-MM-DD`) ke tanggal hari ini kalau file memang memakai konvensi itu.

**`docs/ARCHITECTURE.md`** — dokumen deskriptif (bukan delta-tracked), jadi langsung update section terkait jadi kondisi terkini (tanpa tag [CHANGED]):
- §4 Data Model — kolom/tabel DB baru atau berubah + nomor migrasi terakhir (samakan dengan file terbaru di `backend/alembic/versions/`).
- §5 API Contract — endpoint & error code baru/berubah.
- §6 Forecasting Engine — klasifikasi, backtest, scoring, registry, daftar engine aktif.
- §7 Storage Flow — kalau lifecycle file berubah.
- §8 Error Handling — kalau aturan failure per engine/material berubah.

**`docs/TASK_BREAKDOWN.md`** — tandai fase/task yang sudah selesai, jangan tambah task baru sepihak.

**`docs/RECONCILIATION.md`** — tambah entri hanya untuk keputusan arsitektur yang BERUBAH (apa yang diputuskan, alasannya, apa yang digantikan).

## 4. Laporkan (jangan commit)
- Delta apa yang ditemukan per dokumen (atau "sudah sinkron, tidak ada yang perlu diupdate").
- Section mana yang diedit, ringkas.
- Inkonsistensi lintas-file yang ditemukan (mis. error code ada di kode tapi tidak di `AGENTS.md` §4).
- Hal yang butuh keputusan user (mis. delta ambigu: masuk PRD, ARCHITECTURE, keduanya, atau tidak keduanya).
- Tegaskan: **tidak ada commit/push** dilakukan.
