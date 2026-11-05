"""Daftar periksa keamanan akun, perangkat, dan privasi."""
from __future__ import annotations

from typing import Dict, List

PERINGATAN_KESELAMATAN = (
    "Kalau kamu curiga dipantau oleh orang yang dekat denganmu: menghapus aplikasi pemantau "
    "bisa membuat pelakunya tahu dan situasinya jadi lebih berbahaya. Cari bantuan dulu dari "
    "lembaga pendamping yang kamu percaya, dan gunakan perangkat lain yang aman untuk mencari "
    "bantuan serta menyimpan bukti."
)

CHECKLIST: Dict[str, List[str]] = {
    "Akun": [
        "Aktifkan verifikasi dua langkah di email utama, media sosial, dan perbankan.",
        "Utamakan aplikasi autentikator atau kunci keamanan daripada kode lewat SMS.",
        "Buka daftar perangkat yang sedang masuk di akun email dan keluarkan yang tidak kamu kenal.",
        "Periksa email dan nomor pemulihan akun: pastikan itu milikmu.",
        "Periksa aturan penerusan email otomatis dan aplikasi pihak ketiga yang punya akses.",
        "Gunakan kata sandi unik untuk tiap akun penting (pakai pengelola kata sandi).",
    ],
    "Ponsel": [
        "Pasang pembaruan sistem dan aplikasi, serta pakai kunci layar yang kuat.",
        "Buka Pengaturan > Aksesibilitas dan matikan layanan yang tidak kamu pasang sendiri.",
        "Buka Pengaturan > Admin perangkat dan akses notifikasi: cabut aplikasi yang tidak kamu kenal.",
        "Periksa daftar aplikasi lengkap, termasuk yang tidak punya ikon di layar utama.",
        "Matikan pemasangan dari sumber tidak dikenal dan aktifkan Play Protect.",
        "Tinjau izin lokasi, mikrofon, kamera, dan SMS: cabut yang tidak diperlukan aplikasinya.",
        "Jalankan 'antimata paket' dan 'antimata izin' lalu tinjau hasilnya (indikator, bukan bukti).",
    ],
    "Jaringan": [
        "Ganti kata sandi admin dan Wi-Fi router, dan periksa daftar perangkat yang terhubung.",
        "Hindari Wi-Fi publik untuk akun penting, atau pakai VPN tepercaya.",
    ],
    "Foto dan dokumen": [
        "Matikan penyimpanan lokasi pada kamera bila tidak perlu.",
        "Bersihkan metadata sebelum membagikan foto atau dokumen: 'antimata metadata bersih'.",
        "Ingat: metadata dokumen bisa memuat nama pembuat dan perusahaan.",
    ],
    "Pelacak fisik": [
        "Jika muncul peringatan pelacak asing di ponsel, periksa tas dan kendaraan.",
    ],
}


def ke_teks() -> str:
    baris: List[str] = []
    for judul, butir in CHECKLIST.items():
        baris.append(judul.upper())
        baris.extend(f"[ ] {b}" for b in butir)
        baris.append("")
    baris.append("CATATAN KESELAMATAN")
    baris.append(PERINGATAN_KESELAMATAN)
    return "\n".join(baris)


def ke_markdown() -> str:
    baris: List[str] = ["# Daftar periksa keamanan", ""]
    for judul, butir in CHECKLIST.items():
        baris.append(f"## {judul}")
        baris.extend(f"- [ ] {b}" for b in butir)
        baris.append("")
    baris.append("## Catatan keselamatan")
    baris.append(PERINGATAN_KESELAMATAN)
    return "\n".join(baris) + "\n"