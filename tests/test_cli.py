import contextlib
import io
import json
import os
import tempfile
import zipfile

from antimata.cli import main

IOC = """\
- name: ContohPemantau
  type: stalkerware
  packages:
  - com.contoh.pemantau
"""
DUMPSYS = """\
Packages:
  Package [com.contoh.pemantau] (a1):
    install permissions:
      android.permission.INTERNET: granted=true
    User 0: installed=true
      runtime permissions:
        android.permission.RECORD_AUDIO: granted=true
        android.permission.ACCESS_FINE_LOCATION: granted=true
        android.permission.READ_SMS: granted=true
"""


def _jalankan(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        kode = main(argv)
    return kode, out.getvalue(), err.getvalue()


def _tulis(folder, nama, isi):
    path = os.path.join(folder, nama)
    with open(path, "w", encoding="utf-8") as f:
        f.write(isi)
    return path


def test_paket_dengan_ioc():
    with tempfile.TemporaryDirectory() as d:
        daftar = _tulis(d, "paket.txt", "package:com.contoh.pemantau\npackage:com.aman.app\n")
        ioc = _tulis(d, "ioc.yaml", IOC)
        kode, out, _ = _jalankan(["paket", daftar, "--ioc", ioc])
    assert kode == 0
    assert "[TINGGI] com.contoh.pemantau" in out
    assert "indikator, bukan bukti" in out


def test_paket_tanpa_ioc_memberi_peringatan():
    with tempfile.TemporaryDirectory() as d:
        daftar = _tulis(d, "paket.txt", "package:com.aman.app\n")
        kode, out, _ = _jalankan(["paket", daftar])
    assert kode == 0
    assert "tanpa --ioc" in out
    assert "Tidak ada temuan." in out


def test_paket_json():
    with tempfile.TemporaryDirectory() as d:
        daftar = _tulis(d, "paket.txt", "package:com.contoh.phonespy\n")
        kode, out, _ = _jalankan(["paket", daftar, "--json"])
    assert kode == 0
    assert json.loads(out)[0]["tingkat"] == "RENDAH"


def test_izin_menampilkan_temuan():
    with tempfile.TemporaryDirectory() as d:
        dump = _tulis(d, "dump.txt", DUMPSYS)
        kode, out, _ = _jalankan(["izin", dump])
    assert kode == 0
    assert "[TINGGI] com.contoh.pemantau" in out


def test_izin_abaikan_dan_pihak_ketiga():
    with tempfile.TemporaryDirectory() as d:
        dump = _tulis(d, "dump.txt", DUMPSYS)
        abaikan = _tulis(d, "abaikan.txt", "package:com.contoh.pemantau\n")
        kode, out, _ = _jalankan(["izin", dump, "--abaikan", abaikan])
        assert "Tidak ada aplikasi" in out
        pihak = _tulis(d, "p3.txt", "package:com.lain.app\n")
        kode2, out2, _ = _jalankan(["izin", dump, "--pihak-ketiga", pihak])
    assert kode == 0 and kode2 == 0
    assert "Tidak ada aplikasi" in out2


def test_berkas_tidak_ada_keluar_kode_2():
    kode, _, err = _jalankan(["paket", "tidak_ada.txt"])
    assert kode == 2
    assert "tidak bisa membaca" in err


def test_json_rusak_keluar_kode_2():
    with tempfile.TemporaryDirectory() as d:
        dump = _tulis(d, "dump.json", "{bukan json")
        kode, _, err = _jalankan(["izin", dump])
    assert kode == 2
    assert "JSON tidak valid" in err


def test_metadata_periksa_dan_bersih_dokumen():
    with tempfile.TemporaryDirectory() as d:
        doc = os.path.join(d, "a.docx")
        with zipfile.ZipFile(doc, "w") as z:
            z.writestr("docProps/core.xml", "<c xmlns:dc='y'><dc:creator>Budi Contoh</dc:creator></c>")
        kode, out, _ = _jalankan(["metadata", "periksa", doc])
        assert kode == 0 and "Budi Contoh" in out
        kode2, out2, _ = _jalankan(["metadata", "bersih", doc])
        assert kode2 == 0
        assert os.path.exists(os.path.join(d, "a.bersih.docx"))
        kode3, out3, _ = _jalankan(["metadata", "periksa", os.path.join(d, "a.bersih.docx")])
    assert kode3 == 0 and "Budi Contoh" not in out3


def test_metadata_bersih_ke_folder_tujuan():
    with tempfile.TemporaryDirectory() as d:
        doc = os.path.join(d, "a.docx")
        with zipfile.ZipFile(doc, "w") as z:
            z.writestr("docProps/core.xml", "<c/>")
        keluar = os.path.join(d, "hasil")
        kode, _, _ = _jalankan(["metadata", "bersih", doc, "--keluar", keluar])
        assert kode == 0
        assert os.path.exists(os.path.join(keluar, "a.docx"))


def test_metadata_jenis_tidak_didukung_keluar_kode_2():
    with tempfile.TemporaryDirectory() as d:
        pdf = _tulis(d, "a.pdf", "%PDF-1.4")
        kode, _, err = _jalankan(["metadata", "periksa", pdf])
    assert kode == 2
    assert "belum didukung" in err


def test_checklist_cetak_dan_simpan():
    kode, out, _ = _jalankan(["checklist"])
    assert kode == 0 and "CATATAN KESELAMATAN" in out
    with tempfile.TemporaryDirectory() as d:
        md = os.path.join(d, "cek.md")
        kode2, _, _ = _jalankan(["checklist", "--simpan", md])
        assert kode2 == 0
        with open(md, encoding="utf-8") as f:
            assert f.read().startswith("# Daftar periksa keamanan")