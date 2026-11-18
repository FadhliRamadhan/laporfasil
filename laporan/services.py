"""Logika bisnis: skor prioritas, deteksi duplikat, pencatatan status."""
from django.utils import timezone

from .models import Laporan, RiwayatStatus


def skor_prioritas(laporan):
    """Urgensi (20/tingkat) + dukungan (5 each) + lama menunggu (3/hari), maks 100.
    Fasilitas aksesibilitas mendapat tambahan 15."""
    hari = (timezone.now() - laporan.dibuat).days
    skor = laporan.urgensi * 20 + laporan.pendukung.count() * 5 + hari * 3
    if laporan.kategori == "aksesibilitas":
        skor += 15
    return min(skor, 100)


def dengan_skor(laporan):
    laporan.skor = skor_prioritas(laporan)
    return laporan


def cari_duplikat(lokasi, kategori):
    return list(Laporan.objects.filter(lokasi=lokasi, kategori=kategori).exclude(status="selesai"))


def catat_status(laporan, status, oleh, catatan="", foto_perbaikan=None):
    laporan.status = status
    update_fields = ["status"]
    if foto_perbaikan:
        laporan.foto_perbaikan = foto_perbaikan
        update_fields.append("foto_perbaikan")
    if catatan:
        laporan.catatan_perbaikan = catatan
        update_fields.append("catatan_perbaikan")
    if status == "selesai":
        laporan.selesai_pada = timezone.now()
        laporan.petugas = oleh
        update_fields.extend(["selesai_pada", "petugas"])
    elif oleh and getattr(oleh, "is_staff", False):
        laporan.petugas = oleh
        update_fields.append("petugas")
    laporan.save(update_fields=list(set(update_fields)))
    return RiwayatStatus.objects.create(
        laporan=laporan,
        status=status,
        oleh=oleh,
        catatan=catatan,
        foto=foto_perbaikan
    )


def rata_rata_hari(queryset):
    total, n = 0, 0
    for laporan in queryset:
        selesai = laporan.riwayat.filter(status="selesai").order_by("-waktu").first()
        if selesai:
            total += (selesai.waktu - laporan.dibuat).total_seconds() / 86400
            n += 1
    return round(total / n, 1) if n else 0
