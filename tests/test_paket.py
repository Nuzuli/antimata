from antimata.paket import RENDAH, TINGGI, baca_daftar_paket, muat_ioc, periksa

IOC_CONTOH = """\
- name: ContohPemantau
  type: stalkerware
  packages:
  - com.contoh.pemantau
  - com.contoh.pemantau.lite
  certificates:
  - 00AA00AA
  websites:
  - contoh.example
  c2:
    ips: []
    domains:
    - c2.contoh.example
- name: ContohWatchware
  type: watchware
  packages:
  - com.contoh.watch
"""


def test_baca_daftar_paket_adb_biasa():
    teks = "package:com.android.chrome\npackage:org.contoh.app\n"
    assert baca_daftar_paket(teks) == ["com.android.chrome", "org.contoh.app"]


def test_baca_daftar_paket_opsi_f_dan_baris_polos():
    teks = "# komentar\npackage:/data/app/~~x/base.apk=com.contoh.satu\ncom.contoh.dua\n\n"
    assert baca_daftar_paket(teks) == ["com.contoh.dua", "com.contoh.satu"]


def test_baca_daftar_paket_mengabaikan_baris_tak_valid_dan_duplikat():
    teks = "package:com.a.b\npackage:com.a.b\nbukan paket\n"
    assert baca_daftar_paket(teks) == ["com.a.b"]


def test_muat_ioc_membaca_paket_dan_jenis():
    ioc = muat_ioc(IOC_CONTOH)
    assert set(ioc) == {"com.contoh.pemantau", "com.contoh.pemantau.lite", "com.contoh.watch"}
    assert ioc["com.contoh.pemantau"] == {"nama": "ContohPemantau", "jenis": "stalkerware"}
    assert ioc["com.contoh.watch"]["jenis"] == "watchware"


def test_muat_ioc_tidak_mengambil_domain_atau_sertifikat():
    ioc = muat_ioc(IOC_CONTOH)
    assert "c2.contoh.example" not in ioc
    assert "00AA00AA" not in ioc


def test_periksa_kecocokan_indikator_tingkat_tinggi():
    temuan = periksa(["com.contoh.pemantau", "com.aman.app"], muat_ioc(IOC_CONTOH))
    assert [(t.paket, t.tingkat) for t in temuan] == [("com.contoh.pemantau", TINGGI)]
    assert "ContohPemantau" in temuan[0].alasan


def test_periksa_nama_mencurigakan_tingkat_rendah():
    temuan = periksa(["com.contoh.phonespy", "com.aman.app"])
    assert [(t.paket, t.tingkat) for t in temuan] == [("com.contoh.phonespy", RENDAH)]
    assert "salah alarm" in temuan[0].alasan


def test_periksa_tanpa_temuan():
    assert periksa(["com.aman.app", "org.contoh.peta"]) == []