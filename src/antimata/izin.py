"""Audit izin aplikasi dari keluaran ``adb shell dumpsys package``.

Hasilnya indikator untuk ditinjau, bukan bukti. Aplikasi sah (pesan, peta, perekam) juga
meminta banyak izin.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

SEDANG = "SEDANG"
TINGGI = "TINGGI"

AUDIO_KAMERA = {"android.permission.RECORD_AUDIO", "android.permission.CAMERA"}
LOKASI = {
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.ACCESS_BACKGROUND_LOCATION",
}
PESAN_KONTAK = {
    "android.permission.READ_SMS",
    "android.permission.RECEIVE_SMS",
    "android.permission.READ_CALL_LOG",
    "android.permission.READ_CONTACTS",
    "android.permission.PROCESS_OUTGOING_CALLS",
}
INTERNET = "android.permission.INTERNET"
LATAR_BELAKANG = "android.permission.ACCESS_BACKGROUND_LOCATION"
TAMBAHAN = {
    "android.permission.SYSTEM_ALERT_WINDOW": "bisa menampilkan lapisan di atas aplikasi lain",
    "android.permission.REQUEST_INSTALL_PACKAGES": "bisa memasang aplikasi lain",
    "android.permission.RECEIVE_BOOT_COMPLETED": "jalan otomatis saat ponsel menyala",
}

_PAKET = re.compile(r"^\s*Package \[([^\]]+)\]")
_IZIN = re.compile(r"^\s*([A-Za-z][\w.]*)\s*:\s*granted=true")


@dataclass(frozen=True)
class TemuanIzin:
    paket: str
    tingkat: str
    kategori: List[str]
    izin: List[str]


def baca_izin(teks: str) -> Dict[str, Set[str]]:
    """Baca dumpsys (teks) atau JSON ``{"paket": ["izin", ...]}`` menjadi paket -> izin yang diberikan."""
    isi = teks.lstrip()
    if isi.startswith("{"):
        data = json.loads(isi)
        return {p: set(daftar) for p, daftar in data.items()}
    hasil: Dict[str, Set[str]] = {}
    sekarang: Optional[str] = None
    for baris in teks.splitlines():
        m = _PAKET.match(baris)
        if m:
            sekarang = m.group(1)
            hasil.setdefault(sekarang, set())
            continue
        if sekarang:
            izin = _IZIN.match(baris)
            if izin:
                hasil[sekarang].add(izin.group(1))
    return hasil


def audit(
    izin_per_paket: Dict[str, Set[str]],
    hanya: Optional[Iterable[str]] = None,
    abaikan: Optional[Iterable[str]] = None,
) -> List[TemuanIzin]:
    """Tandai aplikasi yang memegang kombinasi izin pemantauan.

    ``hanya``: batasi ke paket ini (mis. daftar aplikasi pihak ketiga, ``pm list packages -3``).
    ``abaikan``: paket yang kamu percayai.
    """
    batas = set(hanya) if hanya is not None else None
    lewati = set(abaikan or [])
    temuan: List[TemuanIzin] = []
    for paket, izin in sorted(izin_per_paket.items()):
        if paket in lewati or (batas is not None and paket not in batas):
            continue
        kategori: List[str] = []
        ditandai: Set[str] = set()
        if izin & AUDIO_KAMERA:
            kategori.append("mikrofon/kamera")
            ditandai |= izin & AUDIO_KAMERA
        if izin & LOKASI:
            kategori.append("lokasi")
            ditandai |= izin & LOKASI
        if izin & PESAN_KONTAK:
            kategori.append("pesan/panggilan/kontak")
            ditandai |= izin & PESAN_KONTAK
        if LATAR_BELAKANG in izin:
            kategori.append("lokasi di latar belakang")
        for nama, arti in TAMBAHAN.items():
            if nama in izin:
                kategori.append(arti)
                ditandai.add(nama)
        inti = sum(
            1 for k in ("mikrofon/kamera", "lokasi", "pesan/panggilan/kontak") if k in kategori
        )
        if INTERNET in izin and inti >= 3:
            tingkat = TINGGI
        elif inti >= 2:
            tingkat = SEDANG
        else:
            continue
        temuan.append(TemuanIzin(paket, tingkat, kategori, sorted(ditandai)))
    return temuan