from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from laporan import services
from laporan.models import Laporan, Lokasi


class Command(BaseCommand):
    help = "Isi data contoh untuk demo"

    def handle(self, *args, **opts):
        lokasi = {}
        for kode, nama, gedung in [
            ("r2101", "Ruang 2101", "Gedung Fasilkom"), ("toilet-l2", "Toilet lantai 2", "Gedung Fasilkom"),
            ("perpus", "Perpustakaan", "Gedung Perpustakaan"), ("lab-kom", "Lab komputer", "Gedung Fasilkom"),
            ("lift-b", "Lift", "Gedung B")]:
            lokasi[kode], _ = Lokasi.objects.get_or_create(kode=kode, defaults={"nama": nama, "gedung": gedung})
        staf = User.objects.filter(username="staf").first() or User.objects.create_user(
            "staf", password="staf12345", is_staff=True)
        rani = User.objects.filter(username="rani").first() or User.objects.create_user(
            "rani", password="rani12345")
        if Laporan.objects.exists():
            return
        contoh = [("r2101", "ac", "AC tidak dingin", 3, "dilaporkan"),
                  ("lift-b", "aksesibilitas", "Lift macet di lantai 3", 3, "diverifikasi"),
                  ("lab-kom", "listrik", "Colokan meja longgar", 1, "dikerjakan"),
                  ("toilet-l2", "air", "Keran wastafel bocor", 2, "dilaporkan"),
                  ("perpus", "lainnya", "Kursi baca patah", 1, "selesai")]
        for kode, kat, judul, urg, status in contoh:
            l = Laporan.objects.create(pelapor=rani, lokasi=lokasi[kode], kategori=kat, judul=judul,
                                       deskripsi="Contoh laporan untuk demo.", urgensi=urg)
            services.catat_status(l, "dilaporkan", rani)
            if status != "dilaporkan":
                services.catat_status(l, status, staf)
        self.stdout.write("Data contoh dibuat. Akun: staf/staf12345 dan rani/rani12345")
