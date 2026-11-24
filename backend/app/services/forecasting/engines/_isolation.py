"""
Isolasi proses untuk engine berat (24 Nov 2026) — dipakai LSTM (TensorFlow).

Kenapa: TensorFlow bisa mematikan PROSES, bukan sekadar melempar exception — di-OOM-kill kernel
saat training di VPS 4 GB, atau SIGILL bila CPU tidak punya instruksi AVX. Bila training jalan di
proses worker uvicorn, worker itu ikut mati → Caddy membalas 502 dan seluruh run gagal (melanggar
AGENTS #8). `run_isolated` menjalankan fungsi di child process (`spawn`) sehingga:
  - crash / kill → `EngineCrashError` dengan alasan bahasa natural (metode tercatat gagal);
  - melewati `timeout` → child dihentikan, `EngineCrashError` (LSTM_ENGINE_TIMEOUT_SECONDS
    akhirnya benar-benar berlaku);
  - exception biasa di child → dilempar ulang di parent dengan tipe builtin yang sama
    (ModuleNotFoundError mempertahankan `.name`, dipakai `_failure_reason`);
  - memori TensorFlow dilepas ke OS setiap kali child selesai.

`fn` & `args` wajib bisa di-pickle (fungsi level modul).
"""
from __future__ import annotations

import builtins
import multiprocessing as mp
import signal
from collections.abc import Callable


class EngineCrashError(RuntimeError):
    """Child process engine mati / timeout — pesan sudah berupa alasan bahasa natural."""


def _child(conn, fn: Callable, args: tuple) -> None:
    try:
        conn.send(("ok", fn(*args)))
    except BaseException as exc:  # noqa: BLE001 — diteruskan ke parent apa adanya
        conn.send(("err", type(exc).__name__, str(exc), getattr(exc, "name", None)))
    finally:
        conn.close()


def _crash_reason(exitcode: int | None) -> str:
    if exitcode is not None and exitcode < 0:
        sig = -exitcode
        if sig == signal.SIGKILL:
            return (
                "Proses training dihentikan sistem (SIGKILL) — kemungkinan besar server kehabisan "
                "memori. Kurangi UVICORN_WORKERS atau tambah RAM."
            )
        if sig == signal.SIGILL:
            return (
                "Proses training crash (Illegal instruction) — CPU server kemungkinan tidak "
                "mendukung instruksi AVX yang dibutuhkan TensorFlow."
            )
        try:
            name = signal.Signals(sig).name
        except ValueError:
            name = f"sinyal {sig}"
        return f"Proses training crash ({name})."
    return f"Proses training berhenti tanpa hasil (kode keluar {exitcode})."


def _reraise(type_name: str, message: str, name: str | None):
    cls = getattr(builtins, type_name, None)
    if isinstance(cls, type) and issubclass(cls, ImportError):
        raise cls(message, name=name)
    if isinstance(cls, type) and issubclass(cls, Exception):
        try:
            raise cls(message)
        except TypeError:  # konstruktor builtin yang butuh argumen lain
            pass
    raise EngineCrashError(f"{type_name}: {message}")


def run_isolated(fn: Callable, args: tuple, timeout: float):
    ctx = mp.get_context("spawn")
    recv, send = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_child, args=(send, fn, args), daemon=True)
    proc.start()
    send.close()  # parent hanya membaca; EOF terdeteksi saat child mati
    try:
        if not recv.poll(timeout):
            proc.kill()
            proc.join()
            raise EngineCrashError(
                f"Training melebihi batas waktu {timeout:g} detik dan dihentikan "
                "(LSTM_ENGINE_TIMEOUT_SECONDS)."
            )
        try:
            message = recv.recv()
        except EOFError:
            proc.join()
            raise EngineCrashError(_crash_reason(proc.exitcode)) from None
    finally:
        recv.close()
    proc.join()
    if message[0] == "ok":
        return message[1]
    _reraise(*message[1:])
