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

    def test_buat_laporan_ketik_lokasi(self):
        self.client.login(username="rani", password="x12345678")
        # 1. Ketik lokasi baru
        resp = self.client.post(reverse("buat"), {
            "lokasi": "Ruang Rapat Dekanat, Gedung A",
            "kategori": "listrik",
            "judul": "Lampu kedip-kedip",
            "deskripsi": "Lampu di ruang rapat berkedip terus",
            "urgensi": 2,
        })
        self.assertEqual(resp.status_code, 302)
        laporan_baru = Laporan.objects.get(judul="Lampu kedip-kedip")
        self.assertEqual(laporan_baru.lokasi.nama, "Ruang Rapat Dekanat")
        self.assertEqual(laporan_baru.lokasi.gedung, "Gedung A")

        # 2. Ketik lokasi lama yang sudah ada
        resp2 = self.client.post(reverse("buat"), {
            "lokasi": "Ruang 2101",
            "kategori": "air",
            "judul": "Bocor di ruang 2101",
            "deskripsi": "Ada rembesan air",
            "urgensi": 1,
        })
        self.assertEqual(resp2.status_code, 302)
        laporan_lama = Laporan.objects.get(judul="Bocor di ruang 2101")
        self.assertEqual(laporan_lama.lokasi, self.lokasi)

    def test_buat_laporan_ketik_kategori(self):
        self.client.login(username="rani", password="x12345678")
        # 1. Ketik teks label kategori (misal: "AC dan pendingin")
        self.client.post(reverse("buat"), {
            "lokasi": "Ruang 2101",
            "kategori": "AC dan pendingin",
            "judul": "Filter AC Kotor",
            "deskripsi": "Filter perlu dibersihkan",
            "urgensi": 1,
        })
        lap = Laporan.objects.get(judul="Filter AC Kotor")
        self.assertEqual(lap.kategori, "ac")

        # 2. Ketik sinonim / kata kunci umum (misal: "Toilet")
        self.client.post(reverse("buat"), {
            "lokasi": "Ruang 2101",
            "kategori": "Toilet",
            "judul": "Kloset Rusak",
            "deskripsi": "Kloset mampet",
            "urgensi": 2,
        })
        lap2 = Laporan.objects.get(judul="Kloset Rusak")
        self.assertEqual(lap2.kategori, "air")

        # 3. Ketik kategori baru (kustom)
        self.client.post(reverse("buat"), {
            "lokasi": "Ruang 2101",
            "kategori": "Jaringan Internet",
            "judul": "Wifi Lemah",
            "deskripsi": "Koneksi sering putus",
            "urgensi": 2,
        })
        lap3 = Laporan.objects.get(judul="Wifi Lemah")
        self.assertEqual(lap3.kategori, "jaringan-internet")
