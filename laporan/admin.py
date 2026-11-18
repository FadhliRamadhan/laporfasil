from django.contrib import admin

from .models import Komentar, Laporan, Lokasi, Pengumuman, RiwayatStatus

admin.site.register([Lokasi, Laporan, RiwayatStatus, Komentar, Pengumuman])
