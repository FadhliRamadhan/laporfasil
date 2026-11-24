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

    def test_laporan_anonim_dan_kebersihan(self):
        self.client.login(username="rani", password="x12345678")
        resp = self.client.post(reverse("buat"), {
            "lokasi": "Kantin Kampus",
            "kategori": "Kebersihan & Sampah",
            "judul": "Sampah meluber di dekat wastafel",
            "deskripsi": "Banyak sisa makanan berceceran",
            "urgensi": 3,
            "is_anonim": "on",
        })
        self.assertEqual(resp.status_code, 302)
        lap = Laporan.objects.get(judul="Sampah meluber di dekat wastafel")
        self.assertEqual(lap.kategori, "kebersihan")
        self.assertTrue(lap.is_anonim)
        # Tampilan untuk publik adalah anonim
        self.assertEqual(lap.pelapor_display(), "Warga Kampus (Anonim)")
        # Tampilan untuk staf menampilkan username pelapor
        self.assertIn("rani", lap.pelapor_display(self.staf))

    def test_tambah_komentar(self):
        laporan = self.buat()
        self.client.login(username="rani", password="x12345678")
        resp = self.client.post(reverse("tambah_komentar", args=[laporan.pk]), {
            "isi": "Sudah mulai ditangani oleh staf tadi siang."
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(laporan.komentar.count(), 1)
        self.assertEqual(laporan.komentar.first().isi, "Sudah mulai ditangani oleh staf tadi siang.")

    def test_ekspor_csv_khusus_staf(self):
        self.buat()
        # Mahasiswa dilarang
        self.client.login(username="rani", password="x12345678")
        self.assertEqual(self.client.get(reverse("ekspor_csv")).status_code, 302)
        # Staf diizinkan dan menerima file CSV
        self.client.login(username="staf", password="x12345678")
        resp = self.client.get(reverse("ekspor_csv"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertIn("attachment", resp["Content-Disposition"])

    def test_halaman_halaman_khusus(self):
        # 1. Halaman publik mendesak & selesai
        resp_mendesak = self.client.get(reverse("mendesak"))
        self.assertEqual(resp_mendesak.status_code, 200)

        resp_selesai = self.client.get(reverse("selesai"))
        self.assertEqual(resp_selesai.status_code, 200)

        # 2. Halaman butuh login (laporan-saya, didukung-saya, profil)
        self.assertEqual(self.client.get(reverse("laporan_saya")).status_code, 302)
        self.assertEqual(self.client.get(reverse("didukung_saya")).status_code, 302)
        self.assertEqual(self.client.get(reverse("profil")).status_code, 302)

        # 3. Setelah login (mahasiswa)
        self.client.login(username="rani", password="x12345678")
        self.assertEqual(self.client.get(reverse("laporan_saya")).status_code, 200)
        self.assertEqual(self.client.get(reverse("didukung_saya")).status_code, 200)
        self.assertEqual(self.client.get(reverse("profil")).status_code, 200)

    def test_staf_langsung_ke_dashboard(self):
        # 1. Staf login dan diarahkan langsung ke dashboard
        resp_login = self.client.post(reverse("login"), {
            "username": "staf",
            "password": "x12345678"
        })
        self.assertRedirects(resp_login, reverse("dashboard"))

        # 2. Staf membuka beranda ('/') langsung diarahkan ke dashboard
        resp_beranda = self.client.get(reverse("beranda"))
        self.assertRedirects(resp_beranda, reverse("dashboard"))

        # 3. Staf membuka profil langsung diarahkan ke dashboard
        resp_profil = self.client.get(reverse("profil"))
        self.assertRedirects(resp_profil, reverse("dashboard"))

        # 4. Staf membuka laporan-saya langsung diarahkan ke dashboard
        resp_saya = self.client.get(reverse("laporan_saya"))
        self.assertRedirects(resp_saya, reverse("dashboard"))

        # 5. Staf selalu diarahkan ke dashboard kerja, tidak ada feed yang menduplikasi dashboard
        resp_publik = self.client.get(reverse("beranda"), {"publik": "1"})
        self.assertRedirects(resp_publik, reverse("dashboard"))

    def test_kelola_pengumuman_pemeliharaan(self):
        from .models import Pengumuman

        # 1. Mahasiswa tidak boleh mengakses halaman pemeliharaan
        self.client.login(username="rani", password="x12345678")
        self.assertEqual(self.client.get(reverse("kelola_pengumuman")).status_code, 302)

        # 2. Staf dapat membuka halaman pemeliharaan
        self.client.login(username="staf", password="x12345678")
        resp = self.client.get(reverse("kelola_pengumuman"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Publikasi Info Pemeliharaan")

        # 3. Staf menerbitkan info baru
        resp_post = self.client.post(reverse("kelola_pengumuman"), {
            "judul": "Pemadaman Listrik Sementara Gedung Fasilkom",
            "tipe": "pemeliharaan",
            "isi": "Pemeliharaan panel daya listrik utama pada hari Sabtu pukul 09.00-12.00.",
            "aktif": "on",
        })
        self.assertRedirects(resp_post, reverse("kelola_pengumuman"))
        p = Pengumuman.objects.get(judul="Pemadaman Listrik Sementara Gedung Fasilkom")
        self.assertEqual(p.tipe, "pemeliharaan")
        self.assertTrue(p.aktif)

        # 4. Staf mengedit info tersebut
        resp_edit_get = self.client.get(reverse("edit_pengumuman", args=[p.pk]))
        self.assertEqual(resp_edit_get.status_code, 200)
        self.assertContains(resp_edit_get, "Edit Info Pemeliharaan")

        resp_edit_post = self.client.post(reverse("edit_pengumuman", args=[p.pk]), {
            "judul": "Pemadaman Listrik Diundur ke Minggu",
            "tipe": "darurat",
            "isi": "Jadwal dialihkan ke hari Minggu pukul 13.00-15.00 WIB.",
            "aktif": "on",
        })
        self.assertRedirects(resp_edit_post, reverse("kelola_pengumuman"))
        p.refresh_from_db()
        self.assertEqual(p.judul, "Pemadaman Listrik Diundur ke Minggu")
        self.assertEqual(p.tipe, "darurat")

        # 5. Staf menghapus info pemeliharaan
        resp_hapus = self.client.post(reverse("hapus_pengumuman", args=[p.pk]))
        self.assertRedirects(resp_hapus, reverse("kelola_pengumuman"))
        self.assertFalse(Pengumuman.objects.filter(pk=p.pk).exists())
