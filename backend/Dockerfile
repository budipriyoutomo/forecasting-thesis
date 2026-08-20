FROM python:3.11-slim

# Python 3.11 (bukan 3.14 seperti venv dev) — versi yang dipakai CI, dan satu-satunya
# yang punya wheel prebuilt untuk TensorFlow bila LSTM nanti diaktifkan
# (lihat catatan di requirements.txt).

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# requirements di-copy sendiri supaya layer pip ter-cache selama dependency tak berubah.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Jalan sebagai non-root: kalau ada celah di aplikasi, penyerang tidak langsung
# dapat root di dalam container.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Cek yang sama dipakai compose & reverse proxy untuk tahu container siap menerima trafik.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

ENTRYPOINT ["./docker-entrypoint.sh"]
