from django.urls import path

from . import views

urlpatterns = [
    path("", views.beranda, name="beranda"),
    path("lapor/", views.buat, name="buat"),
    path("laporan/<int:pk>/", views.detail, name="detail"),
    path("laporan/<int:pk>/dukung/", views.dukung, name="dukung"),
    path("laporan/<int:pk>/status/", views.ubah_status, name="ubah_status"),
    path("laporan/<int:pk>/perbaikan/", views.upload_perbaikan, name="upload_perbaikan"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("qr/", views.qr_daftar, name="qr_daftar"),
    path("qr/<slug:kode>.png", views.qr, name="qr"),
    path("daftar/", views.daftar, name="daftar"),
]
