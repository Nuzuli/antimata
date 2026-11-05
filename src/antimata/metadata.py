"""Periksa dan bersihkan metadata dari foto (JPEG/PNG/WebP) dan dokumen Office (docx/xlsx/pptx).

Foto memerlukan Pillow (``pip install "antimata[gambar]"``). Dokumen Office hanya memakai pustaka standar.
PDF belum didukung.
"""
from __future__ import annotations

import importlib.util
import re
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

EKSTENSI_GAMBAR = {".jpg", ".jpeg", ".png", ".webp"}
EKSTENSI_OFFICE = {".docx", ".xlsx", ".pptx"}
PESAN_PILLOW = 'Foto butuh Pillow. Pasang dengan: pip install "antimata[gambar]"'
PESAN_JENIS = "jenis berkas belum didukung (foto JPEG/PNG/WebP, docx/xlsx/pptx)"

_TAG_EXIF = {271: "Merek kamera", 272: "Model kamera", 305: "Perangkat lunak", 306: "Waktu", 315: "Pembuat"}
_GPS_IFD = 0x8825
_CORE_MINIMAL = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>'
)


class MetadataError(Exception):
    """Berkas tidak bisa diperiksa atau dibersihkan."""


def jenis_berkas(path) -> Optional[str]:
    ekstensi = Path(path).suffix.lower()
    if ekstensi in EKSTENSI_GAMBAR:
        return "gambar"
    if ekstensi in EKSTENSI_OFFICE:
        return "office"
    return None


def _butuh_pillow() -> None:
    if importlib.util.find_spec("PIL") is None:
        raise MetadataError(PESAN_PILLOW)


def _periksa_gambar(path: Path) -> List[str]:
    _butuh_pillow()
    from PIL import Image

    temuan: List[str] = []
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            for tag, label in _TAG_EXIF.items():
                nilai = exif.get(tag)
                if nilai:
                    temuan.append(f"{label}: {nilai}")
            if exif.get_ifd(_GPS_IFD):
                temuan.append("Lokasi GPS: ADA (koordinat tersimpan di foto)")
            if getattr(img, "text", None):
                temuan.append(f"Teks tertanam: {len(img.text)} entri")
    except OSError as error:
        raise MetadataError(f"tidak bisa membuka {path}: {error}") from error
    return temuan


def _xml_teks(xml: str, tag: str) -> str:
    cocok = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", xml, re.S)
    return cocok.group(1).strip() if cocok else ""


def _periksa_office(path: Path) -> List[str]:
    try:
        with zipfile.ZipFile(path) as z:
            nama = set(z.namelist())
            core = z.read("docProps/core.xml").decode("utf-8", "replace") if "docProps/core.xml" in nama else ""
            app = z.read("docProps/app.xml").decode("utf-8", "replace") if "docProps/app.xml" in nama else ""
    except (zipfile.BadZipFile, OSError) as error:
        raise MetadataError(f"{path} bukan dokumen Office yang valid: {error}") from error
    pasangan = [
        ("Pembuat", _xml_teks(core, "dc:creator")),
        ("Terakhir diubah oleh", _xml_teks(core, "cp:lastModifiedBy")),
        ("Judul", _xml_teks(core, "dc:title")),
        ("Dibuat", _xml_teks(core, "dcterms:created")),
        ("Diubah", _xml_teks(core, "dcterms:modified")),
        ("Perusahaan", _xml_teks(app, "Company")),
        ("Manajer", _xml_teks(app, "Manager")),
        ("Aplikasi", _xml_teks(app, "Application")),
    ]
    return [f"{label}: {nilai}" for label, nilai in pasangan if nilai]


def periksa_berkas(path) -> List[str]:
    """Daftar metadata yang ditemukan (kosong bila tidak ada)."""
    p = Path(path)
    if not p.is_file():
        raise MetadataError(f"tidak bisa membaca {p}: file tidak ditemukan")
    jenis = jenis_berkas(p)
    if jenis == "gambar":
        return _periksa_gambar(p)
    if jenis == "office":
        return _periksa_office(p)
    raise MetadataError(f"{p.suffix or p.name}: {PESAN_JENIS}")


def _bersih_gambar(sumber: Path, tujuan: Path) -> None:
    _butuh_pillow()
    from PIL import Image, ImageOps

    try:
        with Image.open(sumber) as img:
            format_asli = img.format or "PNG"
            img = ImageOps.exif_transpose(img)  # simpan orientasi sebelum EXIF dibuang
            bersih = Image.new(img.mode, img.size)
            if img.mode == "P" and img.getpalette():
                bersih.putpalette(img.getpalette())
            bersih.paste(img)
            opsi: Dict[str, object] = {}
            if format_asli == "JPEG":
                opsi = {"quality": 95, "exif": b""}
            bersih.save(tujuan, format=format_asli, **opsi)
    except OSError as error:
        raise MetadataError(f"tidak bisa memproses {sumber}: {error}") from error


def _bersih_office(sumber: Path, tujuan: Path) -> None:
    try:
        with zipfile.ZipFile(sumber) as masuk, zipfile.ZipFile(tujuan, "w", zipfile.ZIP_DEFLATED) as keluar:
            for info in masuk.infolist():
                data = masuk.read(info.filename)
                if info.filename == "docProps/core.xml":
                    data = _CORE_MINIMAL.encode("utf-8")
                elif info.filename == "docProps/app.xml":
                    teks = data.decode("utf-8", "replace")
                    teks = re.sub(r"<(Company|Manager)[^>]*>.*?</\1>", "", teks, flags=re.S)
                    teks = re.sub(r"<(Company|Manager)\s*/>", "", teks)
                    data = teks.encode("utf-8")
                keluar.writestr(info.filename, data)
    except (zipfile.BadZipFile, OSError) as error:
        raise MetadataError(f"{sumber} bukan dokumen Office yang valid: {error}") from error


def bersihkan_berkas(sumber, tujuan) -> None:
    """Tulis salinan bersih ke ``tujuan`` (berkas asli tidak diubah)."""
    s, t = Path(sumber), Path(tujuan)
    if not s.is_file():
        raise MetadataError(f"tidak bisa membaca {s}: file tidak ditemukan")
    if s.resolve() == t.resolve():
        raise MetadataError("tujuan tidak boleh sama dengan berkas asli")
    jenis = jenis_berkas(s)
    if jenis == "gambar":
        _bersih_gambar(s, t)
    elif jenis == "office":
        _bersih_office(s, t)
    else:
        raise MetadataError(f"{s.suffix or s.name}: {PESAN_JENIS}")