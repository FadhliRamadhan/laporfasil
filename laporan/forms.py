from django import forms
from django.utils.text import slugify

from .models import Laporan, Lokasi


class LaporanForm(forms.ModelForm):
    lokasi = forms.CharField(
        label="Lokasi",
        widget=forms.TextInput(attrs={
            "placeholder": "Ketik lokasi ruangan / fasilitas (contoh: Ruang 2101, Gedung Fasilkom)",
            "list": "daftar-lokasi",
            "autocomplete": "off",
        }),
        help_text="Ketik nama lokasi atau pilih dari saran yang muncul saat Anda mengetik."
    )
    kategori = forms.CharField(
        label="Kategori",
        widget=forms.TextInput(attrs={
            "placeholder": "Ketik kategori kerusakan (contoh: AC, Listrik, Air/Toilet, Aksesibilitas...)",
            "list": "daftar-kategori",
            "autocomplete": "off",
        }),
        help_text="Ketik kategori kerusakan atau pilih dari saran yang muncul saat Anda mengetik."
    )

    class Meta:
        model = Laporan
        fields = ["lokasi", "kategori", "judul", "deskripsi", "foto", "urgensi"]
        widgets = {"deskripsi": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        initial = kwargs.get("initial", {})
        if "lokasi" in initial and isinstance(initial["lokasi"], Lokasi):
            initial["lokasi"] = str(initial["lokasi"])
        elif kwargs.get("instance") and getattr(kwargs["instance"], "lokasi", None):
            initial["lokasi"] = str(kwargs["instance"].lokasi)

        if "kategori" in initial:
            dict_kat = dict(Laporan.KATEGORI)
            initial["kategori"] = dict_kat.get(initial["kategori"], initial["kategori"])
        elif kwargs.get("instance") and getattr(kwargs["instance"], "kategori", None):
            kat_val = kwargs["instance"].kategori
            dict_kat = dict(Laporan.KATEGORI)
            initial["kategori"] = dict_kat.get(kat_val, kat_val)

        super().__init__(*args, **kwargs)

    def clean_kategori(self):
        val = self.cleaned_data.get("kategori", "").strip()
        if not val:
            raise forms.ValidationError("Kategori wajib diisi.")

        val_lower = val.lower()

        mapping = {
            "ac": "ac",
            "pendingin": "ac",
            "ac dan pendingin": "ac",
            "listrik": "listrik",
            "lampu": "listrik",
            "colokan": "listrik",
            "stopkontak": "listrik",
            "saklar": "listrik",
            "air": "air",
            "toilet": "air",
            "air dan toilet": "air",
            "wastafel": "air",
            "keran": "air",
            "kran": "air",
            "aksesibilitas": "aksesibilitas",
            "lift": "aksesibilitas",
            "ramp": "aksesibilitas",
            "disabilitas": "aksesibilitas",
            "kursi roda": "aksesibilitas",
            "lainnya": "lainnya",
        }

        if val_lower in mapping:
            return mapping[val_lower]

        for code, label in Laporan.KATEGORI:
            if val_lower == code.lower() or val_lower == label.lower():
                return code

        slug = slugify(val)[:50]
        return slug if slug else "lainnya"

    def clean_lokasi(self):
        val = self.cleaned_data.get("lokasi", "").strip()
        if not val:
            raise forms.ValidationError("Lokasi wajib diisi.")

        # Cari lokasi yang sudah ada (cocokkan string, nama, atau kode)
        for l in Lokasi.objects.all():
            if val.lower() == str(l).lower() or val.lower() == l.nama.lower() or val.lower() == l.kode.lower():
                return l

        # Jika mengetik lokasi baru yang belum terdaftar, buat otomatis
        if "," in val:
            parts = [p.strip() for p in val.split(",", 1)]
            nama = parts[0]
            gedung = parts[1] if parts[1] else "Kampus"
        else:
            nama = val
            gedung = "Kampus"

        base_slug = slugify(nama)[:40] or "lokasi"
        slug = base_slug
        counter = 1
        while Lokasi.objects.filter(kode=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return Lokasi.objects.create(kode=slug, nama=nama, gedung=gedung)


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
