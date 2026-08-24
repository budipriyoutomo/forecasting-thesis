# Panduan Deployment VPS — ForecastIQ

Runbook langkah demi langkah dari VPS kosong sampai aplikasi bisa dipakai planner.
Untuk **kenapa** arsitekturnya begini (topologi, alasan tiap keputusan), lihat
`ARCHITECTURE.md` §10 dan `RECONCILIATION.md` §Deployment VPS. Dokumen ini fokus ke
**caranya**.

> **Status verifikasi (20 Agustus 2026).** Seluruh artefak deployment sudah dibuat dan
> `docker compose config` sudah divalidasi, tapi **image belum pernah benar-benar di-build**
> karena Docker daemon mati di mesin dev saat penyusunan. Jalankan langkah §4 dengan
> membaca log, bukan berasumsi mulus. Dua hal lain yang belum diuji ke server sungguhan:
> perilaku `copy_object` dan `S3_ADDRESSING_STYLE` di IDCloudHost (§8.5).

---

## 0. Prasyarat

**Spesifikasi VPS minimum:**

| Sumber daya | Minimum | Catatan |
|---|---|---|
| RAM | 4 GB | Build image butuh paling banyak: `pip install` xgboost/lightgbm/scikit-learn/statsmodels dan `next build` sama-sama rakus. Dengan 2 GB, **wajib** tambah swap (§2.4) atau build akan kena OOM killer di tengah jalan. |
| vCPU | 2 | `UVICORN_WORKERS` jangan melebihi jumlah core — forecasting CPU-bound. |
| Disk | 40 GB SSD | Image backend besar (dependency ML). Postgres + volume Caddy menyusul. |
| OS | Ubuntu 22.04 / 24.04 LTS | Perintah di bawah memakai `apt`. |

**Yang harus sudah ada sebelum mulai:**

- Domain yang bisa kamu atur DNS-nya.
- Project **Supabase** (untuk Auth — lihat §1.2). Tanpa ini tidak ada yang bisa login.
- Akun **IDCloudHost Object Storage** + bucket (§1.3). Tanpa ini upload & export gagal.
- Akses SSH root (atau sudo) ke VPS.

---

## 1. Persiapan di luar VPS

Kerjakan tiga hal ini **sebelum** menyentuh server — dua di antaranya butuh waktu propagasi.

### 1.1 DNS

Arahkan A record domain ke IP VPS:

```
Type  Name              Value            TTL
A     forecastiq        <IP_VPS>         300
```

**Lakukan ini lebih dulu dan tunggu sampai benar-benar resolve.** Caddy menerbitkan
sertifikat lewat HTTP-01 challenge — kalau domain belum mengarah ke VPS saat container
pertama kali start, penerbitan gagal. Let's Encrypt punya rate limit (5 kegagalan per
akun per jam), jadi mencoba berulang-ulang justru memperlambat.

Cek dari mesin lokal:

```bash
dig +short forecastiq.example.com     # harus keluar IP VPS
```

### 1.2 Supabase Auth

Backend memverifikasi password ke Supabase Auth, lalu mencari profil + role di tabel
`users` miliknya sendiri. `DEV_AUTH_ENABLED` **diabaikan total** saat `ENVIRONMENT`
bukan `development`, jadi jalur ini tidak bisa dilewati di production.

1. Buat project di [supabase.com](https://supabase.com) (region terdekat, mis. Singapore).
2. Catat dari **Settings → API**: `Project URL`, `anon public key`, `service_role key`.
3. Buat user admin pertama di **Authentication → Users → Add user**: isi email + password,
   centang *Auto Confirm User*. **Catat UUID user yang terbentuk** — dipakai di §5.

> Supabase di sini dipakai **hanya untuk Auth**. Database aplikasi berjalan di VPS
> (Postgres di compose). Kalau kamu justru ingin DB-nya juga di Supabase, lihat §3.3.

### 1.3 Bucket IDCloudHost

1. Buat bucket, mis. `forecastiq-bucket`.
2. Terbitkan **access key** & **secret key** S3.
3. Bucket harus **private** — aplikasi mengakses via kredensial, tidak ada URL publik
   yang dibagikan ke browser.

Endpoint & region yang dipakai default: `https://is3.cloudhost.id`, region `SouthJkt-a`.

---

## 2. Siapkan VPS

### 2.1 User non-root

Jangan menjalankan deployment sebagai root.

```bash
ssh root@<IP_VPS>

adduser deploy                      # isi password
usermod -aG sudo deploy
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy/    # bawa SSH key root
```

Keluar, lalu masuk lagi sebagai `deploy` — **pastikan berhasil sebelum menutup sesi root**,
supaya tidak terkunci di luar:

```bash
ssh deploy@<IP_VPS>
```

### 2.2 Matikan login root & password (setelah §2.1 terbukti jalan)

```bash
sudo nano /etc/ssh/sshd_config
```

```
PermitRootLogin no
PasswordAuthentication no
```

```bash
sudo systemctl restart ssh
```

> **Buka terminal kedua dan uji login sebelum menutup sesi yang sekarang.** Kalau
> konfigurasinya salah dan kamu sudah keluar, satu-satunya jalan masuk adalah konsol
> web/VNC dari panel penyedia VPS.

### 2.3 Firewall

Hanya tiga port yang perlu terbuka. Port aplikasi (3000/8000) dan Postgres (5432)
sengaja **tidak** di-publish oleh `docker-compose.prod.yml`, jadi tidak perlu — dan
tidak boleh — dibuka.

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

### 2.4 Swap (wajib kalau RAM < 4 GB)

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

### 2.5 Docker

```bash
sudo apt update && sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo usermod -aG docker $USER
newgrp docker                       # atau logout & login ulang

docker compose version              # harus keluar v2.x
```

### 2.6 Git & make

```bash
sudo apt install -y git make
```

---

## 3. Ambil kode & konfigurasi

### 3.1 Clone

```bash
cd ~
git clone <URL_REPO> forecastiq
cd forecastiq
```

### 3.2 Buat `.env.prod`

```bash
cp .env.prod.example .env.prod
chmod 600 .env.prod          # jangan sampai world-readable — isinya kredensial
```

Bikin dua secret dulu, jangan mengarang sendiri:

```bash
openssl rand -hex 32         # → JWT_SECRET_KEY
openssl rand -base64 24      # → POSTGRES_PASSWORD
```

Lalu `nano .env.prod` dan isi:

| Variabel | Isi dengan | Kalau kosong |
|---|---|---|
| `DOMAIN` | `forecastiq.example.com` | Caddy tidak bisa menerbitkan sertifikat |
| `TLS_EMAIL` | email kamu (notifikasi Let's Encrypt) | sama seperti di atas |
| `JWT_SECRET_KEY` | hasil `openssl rand -hex 32` | **token bisa dipalsukan siapa saja** |
| `POSTGRES_PASSWORD` | hasil `openssl rand -base64 24` | container Postgres menolak start |
| `DATABASE_URL` | ganti `GANTI_PASSWORD` dengan password di atas | seluruh endpoint DB mati |
| `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | dari §1.2 | **tidak ada yang bisa login** |
| `S3_ACCESS_KEY`, `S3_SECRET_KEY` | dari §1.3 | upload & export gagal |
| `S3_BUCKET_NAME` | nama bucket kamu | sama seperti di atas |
| `CORS_ORIGINS` | `https://forecastiq.example.com` | (jarang terpakai — frontend & backend satu domain) |
| `NEXT_PUBLIC_API_URL` | `https://forecastiq.example.com` | frontend menembak `localhost:8000` |
| `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` | dari §1.2 (anon key, **bukan** service_role) | — |
| `DEFAULT_ORDERING_COST`, `DEFAULT_HOLDING_COST_RATE` | biaya pesan & % biaya simpan riil | **EOQ dan cost summary tampil 0** padahal perhitungannya benar |

> **`DEFAULT_ORDERING_COST` dan `DEFAULT_HOLDING_COST_RATE` yang bernilai nol adalah
> jebakan paling sering**: aplikasi jalan normal, tidak ada error, tapi seluruh angka EOQ
> dan ringkasan biaya keluar 0. Isi dengan angka riil perusahaan.

> **`NEXT_PUBLIC_*` di-inline ke bundel JavaScript saat image di-build**, bukan dibaca
> saat container start. Mengubah nilainya nanti **wajib** disertai build ulang
> (`make prod-deploy`), bukan sekadar `restart`.

Validasi sebelum lanjut:

```bash
make prod-check
```

Ini menolak berlanjut kalau `JWT_SECRET_KEY`/`POSTGRES_PASSWORD` masih kosong, `DATABASE_URL`
masih berisi `GANTI_PASSWORD`, atau `DOMAIN` masih `example.com` — lebih baik gagal di sini
daripada 10 menit kemudian saat container start. Supabase/S3/biaya yang kosong hanya
diperingatkan (⚠️), bukan diblokir, karena ada skenario sah untuk menunda pengisiannya.

### 3.3 (Opsional) Pakai Supabase sebagai database, bukan Postgres di VPS

Kalau memilih ini:

1. Ganti `DATABASE_URL` di `.env.prod` dengan connection string Supabase
   (format `postgresql+asyncpg://...`, pakai **connection pooler** kalau tersedia).
2. Hapus service `postgres` beserta blok `depends_on` di `docker-compose.prod.yml`,
   dan hapus volume `pgdata_prod`.

Sisa langkahnya sama.

---

## 4. Nyalakan

```bash
make prod-up
```

Yang terjadi berurutan:

1. Image backend & frontend di-build. **Ini lama** — 5–15 menit di build pertama,
   tergantung VPS (dependency ML backend dan `next build` keduanya berat).
2. Postgres start, ditunggu sampai healthcheck-nya hijau.
3. Backend start → entrypoint menjalankan `alembic upgrade head` → uvicorn.
   Kalau migrasi gagal, container **sengaja** ikut gagal start (lihat §8.3).
4. Caddy start, minta sertifikat ke Let's Encrypt, mulai melayani 80/443.

Pantau:

```bash
make prod-logs      # ikuti log semua service
make prod-ps        # status container
```

Semua container harus berstatus `running`, dan backend/postgres `(healthy)`.

---

## 5. Buat user admin pertama

Ini langkah yang paling mudah terlewat: **`make seed-users` tidak bisa dipakai di
production** — skripnya menolak jalan kalau `ENVIRONMENT != development`, supaya akun
demo tidak pernah menyelinap ke server sungguhan.

Login butuh **dua hal sekaligus**: kredensial valid di Supabase Auth (§1.2) **dan** baris
profil di tabel `users` milik aplikasi. Yang kedua harus dibuat manual sekali:

```bash
make prod-psql
```

```sql
INSERT INTO users (id, email, name, role, is_verified)
VALUES (
  '<UUID_DARI_SUPABASE>',        -- UUID user dari §1.2 langkah 3
  'admin@perusahaan.com',        -- HARUS sama persis dengan email di Supabase Auth
  'Nama Admin',
  'admin',
  true                           -- kalau false, login ditolak AUTH_EMAIL_NOT_VERIFIED
);
```

Cek:

```sql
SELECT email, role, is_verified FROM users;
\q
```

Role yang valid: `admin`, `ppic`, `purchasing`, `viewer`. Hanya `admin` yang boleh menulis
master data. **Email harus identik** dengan yang di Supabase Auth — pencocokan profil
memakai email, jadi beda satu huruf berarti login ditolak meski password benar.

User berikutnya ditambahkan dengan cara yang sama: buat di Supabase Auth, lalu `INSERT`
satu baris di sini.

---

## 6. Verifikasi

Urut dari lapisan terluar, supaya kalau gagal langsung ketahuan di mana:

```bash
# 1. TLS & backend hidup
curl https://forecastiq.example.com/health
# → {"success":true,"data":{"status":"ok","version":"0.1.0","environment":"production"}}

# 2. Sertifikat valid (bukan self-signed)
curl -sI https://forecastiq.example.com | head -1

# 3. Frontend
curl -sI https://forecastiq.example.com/login | head -1     # → 200

# 4. Redirect HTTP → HTTPS
curl -sI http://forecastiq.example.com | head -1            # → 308
```

Pastikan `"environment":"production"` — kalau masih `development`, `.env.prod` tidak
terbaca dan jalur login demo ikut aktif.

Lalu lewat browser, uji berurutan:

1. Buka `https://forecastiq.example.com` → dialihkan ke `/login`.
2. Login dengan akun §5.
3. Buat satu produk & satu material di `/products` dan `/materials`.
4. **Upload CSV** di `/forecast/new` — ini yang membuktikan object storage benar-benar
   tersambung. Kalau gagal dengan `STORAGE_UPLOAD_FAILED`, lihat §8.5.
5. Jalankan forecast run, lalu hitung reorder → cek EOQ dan cost summary **tidak nol**
   (kalau nol, lihat catatan biaya di §3.2).
6. Export Excel — membuktikan jalur tulis `permanent/exports/` juga jalan.

---

## 7. Operasi rutin

### 7.1 Cron pembersih file temp

**Wajib.** Tanpa ini, file upload yang tidak jadi divalidasi menumpuk di bucket selamanya.

```bash
crontab -e
```

```cron
*/30 * * * * cd /home/deploy/forecastiq && /usr/bin/make prod-cleanup >> /var/log/forecastiq-cleanup.log 2>&1
```

Pakai path absolut `/usr/bin/make` — `PATH` milik cron jauh lebih pendek daripada
`PATH` shell interaktif, dan job yang gagal karena `make: command not found` tidak
akan terlihat sampai bucket penuh.

Uji sekali secara manual dulu:

```bash
make prod-cleanup
```

### 7.2 Backup database

Belum otomatis — jadwalkan sendiri. Simpan hasilnya **di luar VPS**; backup yang hanya
ada di mesin yang sama tidak menolong saat VPS-nya yang hilang.

```bash
make prod-backup                    # → ~/forecastiq-backups/db-<tanggal>-<jam>.sql.gz
make prod-backup BACKUP_DIR=/mnt/backup
```

Jadwalkan harian:

```cron
0 2 * * * cd /home/deploy/forecastiq && /usr/bin/make prod-backup >> /var/log/forecastiq-backup.log 2>&1
```

Restore (minta konfirmasi ketik `ya` sebelum menimpa):

```bash
make prod-restore f=~/forecastiq-backups/db-2026-08-20-0200.sql.gz
```

Jangan lupa `.env.prod` sendiri juga perlu dicadangkan (di tempat aman — isinya kredensial).

### 7.3 Deploy versi baru

```bash
cd ~/forecastiq
git pull
make prod-deploy        # build ulang + restart; migrasi jalan otomatis
```

Ada jeda beberapa detik saat container backend/frontend diganti — normal untuk skala ini.
`make prod-deploy` selalu build ulang, jadi perubahan `NEXT_PUBLIC_*` ikut terbawa.

### 7.4 Rollback

```bash
git log --oneline -10
git checkout <commit_sebelumnya>
make prod-deploy
```

> **Migrasi database tidak ikut otomatis mundur.** Kalau versi yang di-rollback
> menyertakan migrasi skema, turunkan manual dulu **sebelum** menjalankan versi lama:
> ```bash
> make prod-downgrade        # mundur 1 revisi; n=2 untuk lebih
> ```
> Restore backup (§7.2) kalau ragu — data historis & override bersifat append-only dan
> tidak boleh hilang.

### 7.5 Perintah harian

```bash
make prod-ps                       # status semua container
make prod-logs                     # ikuti log semua service
make prod-logs s=backend           # satu service saja
make prod-restart s=backend        # restart satu service
make prod-down                     # hentikan (volume & data tetap aman)
make prod-up                       # nyalakan lagi
make prod-shell                    # shell di container backend
make help                          # daftar lengkap target

docker system df                   # pemakaian disk
docker system prune -a             # bersihkan image lama (hati-hati: bukan volume)
```

> **Target development ditolak di server.** Selama `.env.prod` ada, `make up`, `make dev`,
> `make migrate`, dan `make seed-*` menolak jalan — semuanya memakai `docker-compose.yml`
> versi dev (bind mount, `--reload`, Postgres terbuka di `:5432`) atau `backend/.venv` yang
> tidak ada di server. Padanan production-nya ada di `make help`. Kalau memang disengaja:
> `FORCE_DEV=1 make <target>`.

---

## 8. Troubleshooting

### 8.1 Sertifikat TLS gagal terbit

Gejala: browser memperingatkan sertifikat tidak valid, log Caddy menyebut challenge gagal.

```bash
make prod-logs s=caddy
```

Urutan pemeriksaan:
1. `dig +short <domain>` dari luar VPS — sudah mengarah ke IP yang benar?
2. Port 80 terbuka? (`sudo ufw status`) — HTTP-01 challenge butuh port 80, bukan hanya 443.
3. Ada layanan lain yang sudah memakai port 80? (`sudo lsof -i :80`)
4. Kena rate limit Let's Encrypt? Tunggu satu jam; jangan restart berulang-ulang.

Volume `caddy_data` menyimpan sertifikat — **jangan dihapus** saat bereksperimen, itu
justru memicu penerbitan ulang.

### 8.2 Build kena OOM / terhenti tiba-tiba

Gejala: build berhenti tanpa pesan jelas, atau `Killed`.

```bash
free -h
dmesg | grep -i "out of memory" | tail
```

Tambah swap (§2.4). Kalau tetap gagal, build satu per satu supaya puncak pemakaian
memorinya tidak bertumpuk:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml build backend
docker compose --env-file .env.prod -f docker-compose.prod.yml build frontend
make prod-up
```

(Dua baris pertama sengaja memakai perintah panjang — tidak ada target `make` untuk
build per-service karena ini kasus darurat, bukan alur normal.)

### 8.3 Container backend gagal start / restart terus

Ini **disengaja** kalau migrasi gagal: `docker-entrypoint.sh` memakai `set -e`, jadi
aplikasi tidak akan pernah hidup di atas skema database yang salah.

```bash
make prod-logs s=backend
```

- `alembic upgrade head` gagal → biasanya `DATABASE_URL` salah (password tidak cocok
  dengan `POSTGRES_PASSWORD`, atau host bukan `postgres`).
- Postgres belum siap → seharusnya sudah ditangani `depends_on: service_healthy`; cek
  `docker compose ... ps` apakah Postgres benar-benar `(healthy)`.
- Untuk masuk dan memeriksa tanpa menjalankan migrasi, sementara set `RUN_MIGRATIONS=false`
  di `.env.prod`, `make prod-up`, lalu perbaiki dari dalam container.

### 8.4 Login selalu gagal

- `AUTH_INVALID_CREDENTIALS` dengan status **503** → `SUPABASE_URL`/`SUPABASE_KEY` kosong
  atau salah. Backend sengaja tidak diam-diam meloloskan siapa pun.
- Password benar tapi tetap ditolak → baris di tabel `users` belum ada, atau **email-nya
  beda** dengan yang di Supabase Auth (§5).
- `AUTH_EMAIL_NOT_VERIFIED` → kolom `is_verified` masih `false`:
  ```sql
  UPDATE users SET is_verified = true WHERE email = 'admin@perusahaan.com';
  ```

### 8.5 Upload gagal (`STORAGE_UPLOAD_FAILED`)

- Pesan "Object storage belum dikonfigurasi" → `S3_ENDPOINT_URL`/`S3_ACCESS_KEY` kosong.
- Kredensial terisi tapi tetap gagal → kemungkinan besar **addressing style**. Kalau
  provider tidak punya wildcard DNS untuk `{bucket}.is3.cloudhost.id`, ubah di `.env.prod`:
  ```
  S3_ADDRESSING_STYLE=path
  ```
  lalu `make prod-restart s=backend` (ini env backend biasa, **tidak** perlu build ulang).
- Upload berhasil tapi gagal saat validasi/pindah permanen → `copy_object` bermasalah.
  Belum diuji ke IDCloudHost; laporkan lognya kalau kejadian.

### 8.6 Perubahan `NEXT_PUBLIC_*` tidak berpengaruh

Bukan bug. Nilainya sudah dipanggang ke dalam bundel JavaScript saat build. Jalankan
`make prod-deploy` (build ulang), bukan `restart`.

### 8.7 Halaman lambat / backend berat

```bash
docker stats
```

Tiap worker uvicorn memuat scikit-learn/XGBoost sendiri (ratusan MB). Turunkan
`UVICORN_WORKERS` ke `1` di `.env.prod` kalau RAM mepet, atau naikkan (maksimal sejumlah
core) kalau CPU menganggur dan RAM lega.

---

## 9. Catatan LSTM

`tensorflow` masih di-comment di `backend/requirements.txt`, jadi engine `lstm` otomatis
dikeluarkan dari perbandingan (`ARCHITECTURE.md` §6.4) — dan `.env.prod.example` sengaja
tidak mencantumkannya di `FORECAST_ENGINES_ENABLED`, supaya ketiadaannya eksplisit dan
bukan kegagalan diam-diam.

Untuk mengaktifkan:

1. Uncomment `tensorflow>=2.16` di `backend/requirements.txt` (image memakai Python 3.11,
   yang punya wheel resmi TF).
2. Tambahkan `lstm` ke `FORECAST_ENGINES_ENABLED` di `.env.prod`.
3. `make prod-deploy`.

Konsekuensi: image bertambah ±1 GB, build jauh lebih lama, dan RAM saat training naik
signifikan. `LSTM_ENGINE_TIMEOUT_SECONDS` (default 120 detik) mungkin perlu dinaikkan di
VPS yang lambat. Di VPS 4 GB dengan banyak SKU, pertimbangkan `UVICORN_WORKERS=1`.

---

## 10. Ringkasan berkas

| Berkas | Peran |
|---|---|
| `.env.prod` | seluruh kredensial & konfigurasi server (**jangan di-commit**, mode 600) |
| `.env.prod.example` | template yang di-commit |
| `docker-compose.prod.yml` | definisi stack production |
| `Caddyfile` | reverse proxy, TLS, security header |
| `backend/Dockerfile` + `docker-entrypoint.sh` | image backend, migrasi saat start |
| `frontend/Dockerfile` | image frontend (Next.js standalone) |
| `Makefile` target `prod-*` | perintah operasional (`make help` untuk daftar lengkap) |

---
*Pertanyaan "kenapa begini bukan begitu" dijawab di `RECONCILIATION.md` §Deployment VPS.*
