import os
import tempfile
import zipfile
from unittest import mock

import pytest
from PIL import Image

from antimata.metadata import MetadataError, bersihkan_berkas, jenis_berkas, periksa_berkas

CORE = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<cp:coreProperties xmlns:cp="x" xmlns:dc="y" xmlns:dcterms="z">'
    "<dc:creator>Budi Contoh</dc:creator><cp:lastModifiedBy>Siti Contoh</cp:lastModifiedBy>"
    "<dc:title>Rahasia</dc:title>"
    '<dcterms:created xsi:type="dcterms:W3CDTF">2026-01-01T00:00:00Z</dcterms:created>'
    "</cp:coreProperties>"
)
APP = (
    '<?xml version="1.0"?><Properties><Application>Word</Application>'
    "<Company>PT Contoh</Company><Manager>Pak Contoh</Manager></Properties>"
)


def _foto_jpeg(path):
    exif = Image.Exif()
    exif[271] = "MerekContoh"
    exif[272] = "ModelContoh"
    exif[0x8825] = {1: "S", 2: (6.0, 12.0, 0.0), 3: "E", 4: (106.0, 50.0, 0.0)}
    Image.new("RGB", (8, 6), (200, 30, 30)).save(path, exif=exif)


def _foto_png(path):
    from PIL.PngImagePlugin import PngInfo

    info = PngInfo()
    info.add_text("Author", "Budi Contoh")
    Image.new("RGB", (4, 4), (0, 0, 255)).save(path, pnginfo=info)


def _dokumen(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", "<w:document>isi dokumen</w:document>")
        z.writestr("docProps/core.xml", CORE)
        z.writestr("docProps/app.xml", APP)


def test_jenis_berkas():
    assert jenis_berkas("a.JPG") == "gambar"
    assert jenis_berkas("a.docx") == "office"
    assert jenis_berkas("a.pdf") is None


def test_periksa_jpeg_menemukan_gps_dan_kamera():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "foto.jpg")
        _foto_jpeg(path)
        temuan = periksa_berkas(path)
    teks = "\n".join(temuan)
    assert "Lokasi GPS: ADA" in teks
    assert "MerekContoh" in teks and "ModelContoh" in teks


def test_bersihkan_jpeg_menghapus_exif_dan_gps():
    with tempfile.TemporaryDirectory() as d:
        sumber = os.path.join(d, "foto.jpg")
        tujuan = os.path.join(d, "foto.bersih.jpg")
        _foto_jpeg(sumber)
        bersihkan_berkas(sumber, tujuan)
        assert periksa_berkas(tujuan) == []
        assert len(periksa_berkas(sumber)) > 0  # berkas asli tidak diubah
        with Image.open(tujuan) as img:
            assert img.size == (8, 6)


def test_periksa_dan_bersihkan_png_dengan_teks_tertanam():
    with tempfile.TemporaryDirectory() as d:
        sumber = os.path.join(d, "g.png")
        tujuan = os.path.join(d, "g.bersih.png")
        _foto_png(sumber)
        assert any("Teks tertanam" in t for t in periksa_berkas(sumber))
        bersihkan_berkas(sumber, tujuan)
        assert periksa_berkas(tujuan) == []


def test_periksa_dokumen_office():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "a.docx")
        _dokumen(path)
        teks = "\n".join(periksa_berkas(path))
    for nilai in ("Budi Contoh", "Siti Contoh", "Rahasia", "PT Contoh", "Pak Contoh"):
        assert nilai in teks


def test_bersihkan_dokumen_office_membuang_identitas_tapi_menjaga_isi():
    with tempfile.TemporaryDirectory() as d:
        sumber = os.path.join(d, "a.docx")
        tujuan = os.path.join(d, "a.bersih.docx")
        _dokumen(sumber)
        bersihkan_berkas(sumber, tujuan)
        teks = "\n".join(periksa_berkas(tujuan))
        with zipfile.ZipFile(tujuan) as z:
            isi = z.read("word/document.xml").decode()
    for nilai in ("Budi Contoh", "Siti Contoh", "Rahasia", "PT Contoh", "Pak Contoh"):
        assert nilai not in teks
    assert "isi dokumen" in isi
    assert "Aplikasi: Word" in teks


def test_jenis_tidak_didukung_dan_file_tidak_ada():
    with tempfile.TemporaryDirectory() as d:
        pdf = os.path.join(d, "a.pdf")
        with open(pdf, "wb") as f:
            f.write(b"%PDF-1.4")
        with pytest.raises(MetadataError) as info:
            periksa_berkas(pdf)
        assert "belum didukung" in str(info.value)
        with pytest.raises(MetadataError) as info:
            periksa_berkas(os.path.join(d, "tidak_ada.jpg"))
        assert "tidak ditemukan" in str(info.value)


def test_tujuan_tidak_boleh_sama_dengan_asli():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "foto.jpg")
        _foto_jpeg(path)
        with pytest.raises(MetadataError) as info:
            bersihkan_berkas(path, path)
        assert "tidak boleh sama" in str(info.value)


def test_foto_tanpa_pillow_memberi_saran_pemasangan():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "foto.jpg")
        _foto_jpeg(path)
        with mock.patch("antimata.metadata.importlib.util.find_spec", return_value=None):
            with pytest.raises(MetadataError) as info:
                periksa_berkas(path)
        assert "antimata[gambar]" in str(info.value)


def test_dokumen_rusak_dilaporkan():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "rusak.docx")
        with open(path, "w", encoding="utf-8") as f:
            f.write("bukan zip")
        with pytest.raises(MetadataError) as info:
            periksa_berkas(path)
        assert "bukan dokumen Office" in str(info.value)