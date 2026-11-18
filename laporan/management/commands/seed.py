from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from laporan import services
from laporan.models import Komentar, Laporan, Lokasi, Pengumuman


class Command(BaseCommand):
    help = "Isi data contoh untuk demo"

    def handle(self, *args, **opts):
        lokasi = {}
        for kode, nama, gedung in [
            ("r2101", "Ruang 2101", "Gedung Fasilkom"), ("toilet-l2", "Toilet lantai 2", "Gedung Fasilkom"),
            ("perpus", "Perpustakaan", "Gedung Perpustakaan"), ("lab-kom", "Lab komputer", "Gedung Fasilkom"),
            ("lift-b", "Lift", "Gedung B"), ("kantin", "Kantin Pusat", "Gedung Layanan Mahasiswa")]:
            lokasi[kode], _ = Lokasi.objects.get_or_create(kode=kode, defaults={"nama": nama, "gedung": gedung})
        staf = User.objects.filter(username="staf").first() or User.objects.create_user(
            "staf", password="staf12345", is_staff=True)
        rani = User.objects.filter(username="rani").first() or User.objects.create_user(
            "rani", password="rani12345")

        # Buat pengumuman contoh jika belum ada
        if not Pengumuman.objects.exists():
            Pengumuman.objects.create(
                judul="Jadwal General Cleaning & Penyemprotan AC Bersama",
                isi="Akan diadakan pembersihan menyeluruh area koridor dan pengecekan AC seluruh lantai pada hari Jumat mulai pukul 16.30 WIB.",
                tipe="pemeliharaan",
                aktif=True
            )

        # Laporan kebersihan / kenyamanan
        if not Laporan.objects.filter(kategori="kebersihan").exists():
            l_kotor = Laporan.objects.create(
                pelapor=rani, lokasi=lokasi["kantin"], kategori="kebersihan",
                judul="Tumpahan sisa makanan & tempat sampah penuh",
                deskripsi="Di dekat meja nomor 12 ada tumpahan minuman manis dan tempat sampah organik sudah meluber.",
                urgensi=2, status="dikerjakan", is_anonim=True
            )
            services.catat_status(l_kotor, "dilaporkan", rani)
            services.catat_status(l_kotor, "dikerjakan", staf, catatan="Tim cleaning service sektor kantin sudah diinstruksikan membersihkan.")
            Komentar.objects.create(laporan=l_kotor, penulis=staf, isi="Petugas sedang menuju lokasi dengan peralatan pembersih lantai.")

        if Laporan.objects.count() > 3:
            self.stdout.write("Data contoh sudah siap.")
            return

        contoh = [("r2101", "ac", "AC tidak dingin", 3, "dilaporkan"),
                  ("lift-b", "aksesibilitas", "Lift macet di lantai 3", 3, "diverifikasi"),
                  ("lab-kom", "listrik", "Colokan meja longgar", 1, "dikerjakan"),
                  ("toilet-l2", "air", "Keran wastafel bocor", 2, "dilaporkan"),
                  ("perpus", "sarana", "Kursi baca patah", 1, "selesai")]
        for kode, kat, judul, urg, status in contoh:
            l = Laporan.objects.create(pelapor=rani, lokasi=lokasi[kode], kategori=kat, judul=judul,
                                       deskripsi="Contoh laporan untuk demo.", urgensi=urg)
            services.catat_status(l, "dilaporkan", rani)
            if status != "dilaporkan":
                services.catat_status(l, status, staf)
        self.stdout.write("Data contoh dibuat. Akun: staf/staf12345 dan rani/rani12345")
