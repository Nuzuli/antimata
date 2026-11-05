import json

from antimata.izin import SEDANG, TINGGI, audit, baca_izin

DUMPSYS = """\
Packages:
  Package [com.contoh.pemantau] (a1b2c3):
    userId=10123
    requested permissions:
      android.permission.INTERNET
      android.permission.RECORD_AUDIO
    install permissions:
      android.permission.INTERNET: granted=true
    User 0: ceDataInode=1 installed=true
      runtime permissions:
        android.permission.RECORD_AUDIO: granted=true
        android.permission.ACCESS_FINE_LOCATION: granted=true
        android.permission.READ_SMS: granted=true
        android.permission.CAMERA: granted=false
  Package [com.contoh.peta] (d4e5f6):
    install permissions:
      android.permission.INTERNET: granted=true
    User 0: ceDataInode=2 installed=true
      runtime permissions:
        android.permission.ACCESS_FINE_LOCATION: granted=true
        android.permission.CAMERA: granted=true
  Package [com.contoh.kalkulator] (778899):
    install permissions:
      android.permission.INTERNET: granted=true
"""


def test_baca_izin_hanya_yang_diberikan():
    izin = baca_izin(DUMPSYS)
    assert set(izin) == {"com.contoh.pemantau", "com.contoh.peta", "com.contoh.kalkulator"}
    assert "android.permission.CAMERA" not in izin["com.contoh.pemantau"]
    assert "android.permission.READ_SMS" in izin["com.contoh.pemantau"]


def test_baca_izin_format_json():
    teks = json.dumps({"com.x.y": ["android.permission.CAMERA"]})
    assert baca_izin(teks) == {"com.x.y": {"android.permission.CAMERA"}}


def test_audit_tingkat_tinggi_dan_sedang():
    temuan = audit(baca_izin(DUMPSYS))
    peta = {t.paket: t.tingkat for t in temuan}
    assert peta == {"com.contoh.pemantau": TINGGI, "com.contoh.peta": SEDANG}


def test_audit_menjelaskan_kategori():
    temuan = audit(baca_izin(DUMPSYS))
    pemantau = next(t for t in temuan if t.paket == "com.contoh.pemantau")
    assert pemantau.kategori == ["mikrofon/kamera", "lokasi", "pesan/panggilan/kontak"]
    assert "android.permission.READ_SMS" in pemantau.izin


def test_audit_abaikan_paket_tepercaya():
    temuan = audit(baca_izin(DUMPSYS), abaikan=["com.contoh.pemantau"])
    assert [t.paket for t in temuan] == ["com.contoh.peta"]


def test_audit_hanya_paket_tertentu():
    temuan = audit(baca_izin(DUMPSYS), hanya=["com.contoh.kalkulator", "com.contoh.peta"])
    assert [t.paket for t in temuan] == ["com.contoh.peta"]


def test_audit_izin_tambahan_dilaporkan():
    izin = {"com.x.y": {
        "android.permission.INTERNET", "android.permission.CAMERA",
        "android.permission.ACCESS_FINE_LOCATION", "android.permission.SYSTEM_ALERT_WINDOW",
    }}
    temuan = audit(izin)
    assert temuan[0].tingkat == SEDANG
    assert "bisa menampilkan lapisan di atas aplikasi lain" in temuan[0].kategori