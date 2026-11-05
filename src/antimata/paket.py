"""Cocokkan daftar paket Android dengan indikator stalkerware yang diketahui.

Ini hanya membaca teks yang kamu berikan. Tidak ada yang dikirim ke mana pun.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

KATA_CURIGA = ("spy", "stalk", "keylog", "snoop", "sniff", "stealth")
TINGGI = "TINGGI"
RENDAH = "RENDAH"

_BARIS_PAKET = re.compile(r"^(?:package:)?(?:.*=)?([A-Za-z][\w]*(?:\.[\w]+)+)\s*$")


@dataclass(frozen=True)
class Temuan:
    paket: str
    tingkat: str
    alasan: str


def baca_daftar_paket(teks: str) -> List[str]:
    """Baca keluaran ``adb shell pm list packages`` (opsi ``-f``/``-3`` juga boleh) atau satu paket per baris."""
    hasil: Set[str] = set()
    for baris in teks.splitlines():
        baris = baris.strip()
        if not baris or baris.startswith("#"):
            continue
        cocok = _BARIS_PAKET.match(baris)
        if cocok:
            hasil.add(cocok.group(1))
    return sorted(hasil)


def muat_ioc(teks: str) -> Dict[str, Dict[str, str]]:
    """Baca ioc.yaml dari repo stalkerware-indicators (Echap): paket -> {nama, jenis}.

    Pembaca ini sengaja minimal dan hanya mengambil daftar ``packages`` tiap entri.
    """
    peta: Dict[str, Dict[str, str]] = {}
    nama = ""
    jenis = ""
    kunci = ""
    for mentah in teks.splitlines():
        baris = mentah.rstrip()
        if not baris.strip() or baris.lstrip().startswith("#"):
            continue
        if baris.startswith("- name:"):
            nama = baris.split(":", 1)[1].strip().strip("\"'")
            jenis = ""
            kunci = ""
            continue
        isi = baris.strip()
        if isi.startswith("- "):
            if kunci == "packages":
                nama_paket = isi[2:].strip().strip("\"'")
                if nama_paket:
                    peta[nama_paket] = {"nama": nama, "jenis": jenis}
            continue
        if ":" in isi:
            k, _, nilai = isi.partition(":")
            kunci = k.strip()
            if kunci == "type":
                jenis = nilai.strip().strip("\"'")
    return peta


def periksa(daftar: List[str], ioc: Optional[Dict[str, Dict[str, str]]] = None) -> List[Temuan]:
    """Kembalikan temuan: kecocokan indikator (TINGGI) dan nama paket mencurigakan (RENDAH)."""
    temuan: List[Temuan] = []
    ioc = ioc or {}
    for p in daftar:
        if p in ioc:
            info = ioc[p]
            jenis = info.get("jenis") or "stalkerware"
            temuan.append(Temuan(p, TINGGI, f"cocok indikator {jenis}: {info.get('nama') or '?'}"))
            continue
        kata = [k for k in KATA_CURIGA if k in p.lower()]
        if kata:
            temuan.append(
                Temuan(p, RENDAH, f"nama paket mengandung kata: {', '.join(kata)} (bisa salah alarm)")
            )
    return temuan