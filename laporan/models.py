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
    KATEGORI = [
        ("kebersihan", "Kebersihan & Sampah"),
        ("ac", "AC dan Pendingin"),
        ("listrik", "Listrik & Lampu"),
        ("air", "Air & Toilet"),
        ("sarana", "Furnitur & Sarana"),
        ("keamanan", "Keamanan & Bahaya"),
        ("aksesibilitas", "Aksesibilitas"),
        ("lainnya", "Lainnya"),
    ]
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
    is_anonim = models.BooleanField("Laporkan sebagai Anonim", default=False)
    target_selesai = models.DateField("Target Selesai Perbaikan", null=True, blank=True)
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

    def pelapor_display(self, user=None):
        if self.is_anonim:
            if user and getattr(user, "is_staff", False):
                return f"{self.pelapor.username} (Anonim)"
            return "Warga Kampus (Anonim)"
        return self.pelapor.username


class RiwayatStatus(models.Model):
    laporan = models.ForeignKey(Laporan, on_delete=models.CASCADE, related_name="riwayat")
    status = models.CharField(max_length=20, choices=Laporan.STATUS)
    oleh = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    catatan = models.CharField("Catatan", max_length=255, blank=True, default="")
    foto = models.ImageField("Foto bukti", upload_to="riwayat/", blank=True, null=True)
    waktu = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["waktu", "id"]


class Komentar(models.Model):
    laporan = models.ForeignKey(Laporan, on_delete=models.CASCADE, related_name="komentar")
    penulis = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    isi = models.TextField("Isi komentar / info pembaruan")
    dibuat = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["dibuat", "id"]
        verbose_name_plural = "komentar"

    def __str__(self):
        return f"Komentar oleh {self.penulis.username} pada #{self.laporan_id}"


class Pengumuman(models.Model):
    TIPE = [
        ("info", "Informasi Umum"),
        ("pemeliharaan", "Jadwal Pemeliharaan"),
        ("darurat", "Penting / Perhatian"),
    ]
    judul = models.CharField(max_length=200)
    isi = models.TextField()
    tipe = models.CharField(max_length=20, choices=TIPE, default="info")
    aktif = models.BooleanField(default=True)
    dibuat = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-dibuat"]
        verbose_name_plural = "pengumuman"

    def __str__(self):
        return self.judul
