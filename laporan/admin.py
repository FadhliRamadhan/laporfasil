from django.contrib import admin

from .models import Laporan, Lokasi, RiwayatStatus

admin.site.register([Lokasi, Laporan, RiwayatStatus])
