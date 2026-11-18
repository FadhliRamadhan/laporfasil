from django.conf import settings
from django.db import models


class Lokasi(models.Model):
    kode = models.SlugField(unique=True)
    nama = models.CharField(max_length=100)
    gedung = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "lokasi"

    def __str__(self):
        return f"{self.nama}, {self.gedung}"


class Laporan(models.Model):
    KATEGORI = [("ac", "AC dan pendingin"), ("listrik", "Listrik"), ("air", "Air dan toilet"),
                ("aksesibilitas", "Aksesibilitas"), ("lainnya", "Lainnya")]
    URGENSI = [(1, "Rendah"), (2, "Sedang"), (3, "Tinggi")]
    STATUS = [("dilaporkan", "Dilaporkan"), ("diverifikasi", "Diverifikasi"),
              ("dikerjakan", "Dikerjakan"), ("selesai", "Selesai")]

    pelapor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="laporan")
    lokasi = models.ForeignKey(Lokasi, on_delete=models.PROTECT)
    kategori = models.CharField("Kategori fasilitas", max_length=50)
    judul = models.CharField("Judul singkat", max_length=120)
    deskripsi = models.TextField()
    foto = models.ImageField("Foto kerusakan", upload_to="laporan/", blank=True)
    urgensi = models.PositiveSmallIntegerField("Tingkat urgensi", choices=URGENSI, default=2)
    status = models.CharField(max_length=20, choices=STATUS, default="dilaporkan")
    dibuat = models.DateTimeField(auto_now_add=True)
    pendukung = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="dukungan", blank=True)
    foto_perbaikan = models.ImageField("Foto hasil perbaikan", upload_to="perbaikan/", blank=True, null=True)
    catatan_perbaikan = models.TextField("Catatan perbaikan", blank=True, default="")
    petugas = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="tindakan_perbaikan")
    selesai_pada = models.DateTimeField("Waktu selesai perbaikan", null=True, blank=True)

    class Meta:
        ordering = ["-dibuat"]
        verbose_name_plural = "laporan"

    def __str__(self):
        return self.judul

    def get_kategori_display(self):
        return dict(self.KATEGORI).get(self.kategori, self.kategori.replace("-", " ").title())


class RiwayatStatus(models.Model):
    laporan = models.ForeignKey(Laporan, on_delete=models.CASCADE, related_name="riwayat")
    status = models.CharField(max_length=20, choices=Laporan.STATUS)
    oleh = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    catatan = models.CharField("Catatan", max_length=255, blank=True, default="")
    foto = models.ImageField("Foto bukti", upload_to="riwayat/", blank=True, null=True)
    waktu = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["waktu", "id"]
