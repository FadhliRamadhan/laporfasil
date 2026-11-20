import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont
from laporan.models import Laporan

MEDIA_ROOT = settings.MEDIA_ROOT
LAPORAN_DIR = MEDIA_ROOT / "laporan"
PERBAIKAN_DIR = MEDIA_ROOT / "perbaikan"

LAPORAN_DIR.mkdir(parents=True, exist_ok=True)
PERBAIKAN_DIR.mkdir(parents=True, exist_ok=True)

def generate_photo(filepath, title, desc, location, status_type="kerusakan"):
    width, height = 800, 600
    
    if status_type == "perbaikan":
        bg_color = (236, 253, 245)
        border_color = (5, 150, 105)
        header_color = (4, 120, 87)
        badge_text = "DOKUMENTASI HASIL PENANGANAN / SELESAI"
        watermark = "TERVERIFIKASI STAF SARPRAS"
        accent = (16, 185, 129)
    else:
        bg_color = (255, 241, 242)
        border_color = (225, 29, 72)
        header_color = (190, 18, 60)
        badge_text = "FOTO BUKTI KONDISI LAPANGAN (PELAPOR)"
        watermark = "BUKTI AWAL PENGADUAN"
        accent = (244, 63, 94)

    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Frame & Border
    draw.rectangle([(0, 0), (width - 1, height - 1)], fill=bg_color, outline=border_color, width=6)

    # Top Header
    draw.rectangle([(6, 6), (width - 6, 60)], fill=header_color)
    draw.text((24, 22), badge_text, fill=(255, 255, 255))
    draw.text((width - 240, 22), timezone.now().strftime("%d/%m/%Y • LaporFasil"), fill=(255, 255, 255))

    # Center Panel
    draw.rectangle([(40, 85), (width - 40, height - 90)], fill=(255, 255, 255), outline=(226, 232, 240), width=2)

    # Graphic representation box
    cx, cy = width // 2, 260
    draw.rectangle([(cx - 160, cy - 120), (cx + 160, cy + 80)], fill=(248, 250, 252), outline=accent, width=2)

    if status_type == "perbaikan":
        # Green check circle
        draw.ellipse([(cx - 45, cy - 50), (cx + 45, cy + 40)], fill=(209, 250, 229), outline=(5, 150, 105), width=4)
        draw.line([(cx - 20, cy - 5), (cx - 5, cy + 15)], fill=(5, 150, 105), width=6)
        draw.line([(cx - 5, cy + 15), (cx + 25, cy - 25)], fill=(5, 150, 105), width=6)
        draw.text((cx - 110, cy + 95), "PERBAIKAN SELESAI & TELAH DIUJI", fill=(6, 95, 70))
    else:
        # Red warning circle
        draw.ellipse([(cx - 45, cy - 50), (cx + 45, cy + 40)], fill=(254, 226, 226), outline=(225, 29, 72), width=4)
        draw.line([(cx, cy - 30), (cx, cy + 5)], fill=(225, 29, 72), width=6)
        draw.ellipse([(cx - 4, cy + 15), (cx + 4, cy + 23)], fill=(225, 29, 72))
        draw.text((cx - 100, cy + 95), "KENDALA MEMERLUKAN TINDAKAN", fill=(159, 18, 57))

    # Metadata inside Center Panel
    draw.text((60, 420), f"Fasilitas : {title}", fill=(15, 23, 42))
    draw.text((60, 450), f"Catatan   : {desc[:65]}...", fill=(71, 85, 105))
    draw.text((width - 250, 450), f"[ {watermark} ]", fill=border_color)

    # Bottom Footer
    draw.rectangle([(6, height - 55), (width - 6, height - 6)], fill=(15, 23, 42))
    draw.text((24, height - 38), f"📍 Lokasi: {location}", fill=(248, 250, 252))
    draw.text((width - 240, height - 38), "Universitas - LaporFasil 2026", fill=(148, 163, 184))

    img.save(filepath, format="JPEG", quality=90)
    print(f"Generated: {filepath.name}")

def seed_all():
    laporan_all = Laporan.objects.all().order_by("id")
    for lap in laporan_all:
        loc_str = f"{lap.lokasi.nama}, {lap.lokasi.gedung}"
        # Buat foto kerusakan (Kondisi Awal)
        filename_kerusakan = f"lap_{lap.id}_awal.jpg"
        path_kerusakan = LAPORAN_DIR / filename_kerusakan
        generate_photo(path_kerusakan, lap.judul, lap.deskripsi, loc_str, status_type="kerusakan")
        lap.foto = f"laporan/{filename_kerusakan}"

        # Jika status selesai atau dikerjakan, buat foto perbaikan juga
        if lap.status in ["selesai", "dikerjakan"]:
            filename_perbaikan = f"lap_{lap.id}_perbaikan.jpg"
            path_perbaikan = PERBAIKAN_DIR / filename_perbaikan
            generate_photo(path_perbaikan, lap.judul, f"Telah ditangani oleh teknisi fasilitas: {lap.catatan_perbaikan or 'Perbaikan selesai dan berfungsi normal'}", loc_str, status_type="perbaikan")
            lap.foto_perbaikan = f"perbaikan/{filename_perbaikan}"
            if not lap.catatan_perbaikan:
                lap.catatan_perbaikan = "Fasilitas telah diperbaiki oleh tim teknisi sarpras dan sudah berfungsi normal kembali."

        lap.save()
        print(f"Updated Laporan #{lap.id}: {lap.judul} with photos!")

if __name__ == "__main__":
    seed_all()
