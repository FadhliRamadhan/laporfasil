from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from . import services
from .models import Laporan, Lokasi


class LaporanTests(TestCase):
    def setUp(self):
        self.lokasi = Lokasi.objects.create(kode="r2101", nama="Ruang 2101", gedung="Fasilkom")
        self.mhs = User.objects.create_user("rani", password="x12345678")
        self.staf = User.objects.create_user("staf", password="x12345678", is_staff=True)

    def buat(self, **kw):
        data = dict(pelapor=self.mhs, lokasi=self.lokasi, kategori="ac", judul="AC mati",
                    deskripsi="d", urgensi=2)
        data.update(kw)
        return Laporan.objects.create(**data)

    def test_skor_naik_dengan_dukungan(self):
        laporan = self.buat()
        awal = services.skor_prioritas(laporan)
        laporan.pendukung.add(self.staf)
        self.assertGreater(services.skor_prioritas(laporan), awal)

    def test_duplikat_terdeteksi(self):
        self.buat()
        self.assertEqual(len(services.cari_duplikat(self.lokasi, "ac")), 1)

    def test_dashboard_khusus_staf(self):
        self.client.login(username="rani", password="x12345678")
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 302)
        self.client.login(username="staf", password="x12345678")
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

    def test_ubah_status_mencatat_riwayat(self):
        laporan = self.buat()
        self.client.login(username="staf", password="x12345678")
        self.client.post(reverse("ubah_status", args=[laporan.pk]), {
            "status": "selesai",
            "catatan_perbaikan": "Selesai diperbaiki oleh teknisi",
        })
        laporan.refresh_from_db()
        self.assertEqual(laporan.status, "selesai")
        self.assertEqual(laporan.catatan_perbaikan, "Selesai diperbaiki oleh teknisi")
        self.assertEqual(laporan.riwayat.count(), 1)
        self.assertEqual(laporan.riwayat.first().catatan, "Selesai diperbaiki oleh teknisi")

    def test_dashboard_filter_dan_pencarian(self):
        self.buat(judul="AC Ruang 2101 Bocor")
        self.client.login(username="staf", password="x12345678")
        resp = self.client.get(reverse("dashboard"), {"q": "2101"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "AC Ruang 2101 Bocor")

    def test_upload_perbaikan_view(self):
        laporan = self.buat()
        # Mahasiswa dilarang (redirect ke login)
        self.client.login(username="rani", password="x12345678")
        self.assertEqual(self.client.get(reverse("upload_perbaikan", args=[laporan.pk])).status_code, 302)
        # Staf diizinkan
        self.client.login(username="staf", password="x12345678")
        self.assertEqual(self.client.get(reverse("upload_perbaikan", args=[laporan.pk])).status_code, 200)
