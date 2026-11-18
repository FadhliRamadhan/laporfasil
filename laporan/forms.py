from django import forms

from .models import Laporan


class LaporanForm(forms.ModelForm):
    class Meta:
        model = Laporan
        fields = ["lokasi", "kategori", "judul", "deskripsi", "foto", "urgensi"]
        widgets = {"deskripsi": forms.Textarea(attrs={"rows": 3})}


class PerbaikanForm(forms.ModelForm):
    class Meta:
        model = Laporan
        fields = ["status", "foto_perbaikan", "catatan_perbaikan"]
        widgets = {
            "status": forms.Select(attrs={"class": "input-field"}),
            "foto_perbaikan": forms.ClearableFileInput(attrs={"class": "input-field", "accept": "image/*"}),
            "catatan_perbaikan": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Jelaskan tindakan yang sudah dilakukan, suku cadang yang diganti, atau kondisi terkini fasilitas...",
                "class": "input-field"
            }),
        }
        labels = {
            "status": "Status Penanganan",
            "foto_perbaikan": "Upload Foto Hasil Perbaikan",
            "catatan_perbaikan": "Catatan / Tindakan Petugas",
        }
