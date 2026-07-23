# ForecastIQ — Frontend

Next.js (App Router) + TypeScript + Tailwind + shadcn/ui + TanStack Query.
Struktur `src/` mengikuti `docs/ARCHITECTURE.md` §3. Halaman/komponen per fitur
ditulis mengikuti urutan fase di `docs/TASK_BREAKDOWN.md` — saat ini baru
halaman depan (cek koneksi backend, kriteria selesai Fase 0).

## Menjalankan
```bash
npm install
cp .env.local.example .env.local   # isi NEXT_PUBLIC_API_URL, dst
npm run dev        # http://localhost:3000
npm test           # vitest
npm run lint       # eslint
npm run typecheck  # tsc --noEmit
```

## Referensi wajib sebelum menulis kode
1. `../AGENTS.md` §8 (konvensi penamaan komponen/hook/type)
2. `../docs/ARCHITECTURE.md` §3 (struktur frontend) dan §5 (kontrak API)
3. `src/lib/api.ts` + `src/types/api.ts` — envelope response backend
   (`{ success, data | error }`), semua fungsi API mengembalikan `ApiResponse<T>`
   dan tidak melempar exception untuk error bisnis.
