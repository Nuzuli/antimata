from antimata.checklist import CHECKLIST, PERINGATAN_KESELAMATAN, ke_markdown, ke_teks


def test_teks_memuat_semua_kategori_dan_catatan_keselamatan():
    teks = ke_teks()
    for judul in CHECKLIST:
        assert judul.upper() in teks
    assert "CATATAN KESELAMATAN" in teks
    assert PERINGATAN_KESELAMATAN in teks


def test_markdown_memakai_kotak_centang():
    md = ke_markdown()
    assert md.startswith("# Daftar periksa keamanan")
    assert "- [ ] " in md
    assert "## Catatan keselamatan" in md


def test_tidak_ada_butir_kosong():
    for butir in CHECKLIST.values():
        assert butir and all(b.strip() for b in butir)