import argparse
import json
import sys
from pathlib import Path

from . import __version__, checklist, izin, metadata, paket

CATATAN = (
    "Catatan: hasil ini adalah indikator, bukan bukti. 'Tidak ditemukan' tidak berarti aman. "
    "Stalkerware yang canggih tidak tertangkap oleh pemeriksaan sederhana ini."
)


def _baca(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        print(f"Error: tidak bisa membaca {path}: {error}", file=sys.stderr)
        return None


def _daftar_dari(path):
    teks = _baca(path)
    return None if teks is None else paket.baca_daftar_paket(teks)


def _perintah_paket(a):
    teks = _baca(a.berkas)
    if teks is None:
        return 2
    daftar = paket.baca_daftar_paket(teks)
    ioc = {}
    if a.ioc:
        isi_ioc = _baca(a.ioc)
        if isi_ioc is None:
            return 2
        ioc = paket.muat_ioc(isi_ioc)
    temuan = paket.periksa(daftar, ioc)
    if a.json:
        print(json.dumps([t.__dict__ for t in temuan], ensure_ascii=False, indent=2))
        return 0
    print(f"Paket diperiksa: {len(daftar)} | indikator dimuat: {len(ioc)}")
    if not a.ioc:
        print("Peringatan: tanpa --ioc hanya pemeriksaan nama paket yang dilakukan (lemah).")
    for t in temuan:
        print(f"[{t.tingkat}] {t.paket}: {t.alasan}")
    if not temuan:
        print("Tidak ada temuan.")
    print("\n" + CATATAN)
    return 0


def _perintah_izin(a):
    teks = _baca(a.berkas)
    if teks is None:
        return 2
    try:
        izin_paket = izin.baca_izin(teks)
    except ValueError as error:
        print(f"Error: format JSON tidak valid: {error}", file=sys.stderr)
        return 2
    hanya = _daftar_dari(a.pihak_ketiga) if a.pihak_ketiga else None
    abaikan = _daftar_dari(a.abaikan) if a.abaikan else None
    if (a.pihak_ketiga and hanya is None) or (a.abaikan and abaikan is None):
        return 2
    temuan = izin.audit(izin_paket, hanya, abaikan)
    if a.json:
        print(json.dumps([t.__dict__ for t in temuan], ensure_ascii=False, indent=2))
        return 0
    print(f"Aplikasi dibaca: {len(izin_paket)}")
    for t in temuan:
        print(f"[{t.tingkat}] {t.paket}: {', '.join(t.kategori)}")
    if not temuan:
        print("Tidak ada aplikasi dengan kombinasi izin yang menonjol.")
    print("\n" + CATATAN)
    return 0


def _perintah_periksa(a):
    kode = 0
    for berkas in a.berkas:
        try:
            temuan = metadata.periksa_berkas(berkas)
        except metadata.MetadataError as error:
            print(f"Error: {error}", file=sys.stderr)
            kode = 2
            continue
        print(f"{berkas}:")
        for baris in temuan or ["tidak ada metadata yang menonjol"]:
            print(f"  - {baris}")
    return kode


def _perintah_bersih(a):
    kode = 0
    keluar = Path(a.keluar) if a.keluar else None
    if keluar:
        keluar.mkdir(parents=True, exist_ok=True)
    for berkas in a.berkas:
        sumber = Path(berkas)
        tujuan = (keluar / sumber.name) if keluar else sumber.with_name(f"{sumber.stem}.bersih{sumber.suffix}")
        try:
            metadata.bersihkan_berkas(sumber, tujuan)
        except metadata.MetadataError as error:
            print(f"Error: {error}", file=sys.stderr)
            kode = 2
            continue
        print(f"{sumber} -> {tujuan}")
    return kode


def _perintah_checklist(a):
    if a.simpan:
        Path(a.simpan).write_text(checklist.ke_markdown(), encoding="utf-8")
        print(f"Tersimpan: {a.simpan}")
    else:
        print(checklist.ke_teks())
    return 0


def bangun_parser():
    p = argparse.ArgumentParser(prog="antimata", description="Alat pertahanan privasi dan antipemantauan")
    p.add_argument("--version", action="version", version=f"antimata {__version__}")
    sub = p.add_subparsers(dest="perintah", required=True)

    s = sub.add_parser("paket", help="cocokkan daftar paket Android dengan indikator stalkerware")
    s.add_argument("berkas", help="keluaran 'adb shell pm list packages' (atau satu paket per baris)")
    s.add_argument("--ioc", help="ioc.yaml dari github.com/AssoEchap/stalkerware-indicators")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fungsi=_perintah_paket)

    s = sub.add_parser("izin", help="audit izin aplikasi dari keluaran 'adb shell dumpsys package'")
    s.add_argument("berkas", help="keluaran dumpsys, atau JSON {paket: [izin]}")
    s.add_argument("--pihak-ketiga", help="daftar paket pihak ketiga ('pm list packages -3') untuk membatasi audit")
    s.add_argument("--abaikan", help="daftar paket yang kamu percayai")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fungsi=_perintah_izin)

    m = sub.add_parser("metadata", help="periksa atau bersihkan metadata foto dan dokumen")
    msub = m.add_subparsers(dest="aksi", required=True)
    s = msub.add_parser("periksa", help="tampilkan metadata yang ditemukan")
    s.add_argument("berkas", nargs="+")
    s.set_defaults(fungsi=_perintah_periksa)
    s = msub.add_parser("bersih", help="tulis salinan tanpa metadata (asli tidak diubah)")
    s.add_argument("berkas", nargs="+")
    s.add_argument("--keluar", metavar="FOLDER", help="folder tujuan (bawaan: samping berkas, akhiran .bersih)")
    s.set_defaults(fungsi=_perintah_bersih)

    s = sub.add_parser("checklist", help="daftar periksa keamanan akun dan perangkat")
    s.add_argument("--simpan", metavar="FILE.md", help="simpan sebagai Markdown")
    s.set_defaults(fungsi=_perintah_checklist)
    return p


def main(argv=None):
    a = bangun_parser().parse_args(argv)
    return a.fungsi(a)


if __name__ == "__main__":
    sys.exit(main())