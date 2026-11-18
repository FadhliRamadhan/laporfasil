# LaporFasil

Aplikasi web (Python + Django) untuk melaporkan fasilitas kampus yang rusak, memantau statusnya,
dan membantu staf menentukan prioritas perbaikan.

## Fitur
- Form laporan dengan foto, lokasi (input teks & autocomplete), kategori (input teks & autocomplete), dan urgensi
- Alur status: Dilaporkan, Diverifikasi, Dikerjakan, Selesai (dengan riwayat)
- "Saya juga mengalami" (dukungan) dan peringatan laporan duplikat
- Skor prioritas otomatis (urgensi, jumlah dukungan, lama menunggu, bonus aksesibilitas)
- Kode QR per ruangan: scan membuka form dengan lokasi terisi
- Dashboard staf: ringkasan statistik, filter/pencarian laporan, upload dokumentasi bukti hasil perbaikan (foto & catatan)
- Role: mahasiswa, staf (`is_staff`), admin

## Menjalankan
```
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed          # data contoh + akun demo
python manage.py runserver
```
Akun demo:
- **Admin**: `admin` / `admin12345` (Akses penuh & Django admin di `/admin/`)
- **Staf**: `staf` / `staf12345` (Dashboard staf, ubah status, cetak QR, upload perbaikan)
- **Mahasiswa/Umum**: `rani` / `rani12345` (Buat laporan, dukung laporan)

Cara cepat menjalankan di Windows:
Cukup klik ganda file `run.bat`.

## Tes
```
python manage.py test
```

## Struktur
- `config/` pengaturan dan URL proyek
- `laporan/models.py` Lokasi, Laporan, RiwayatStatus
- `laporan/services.py` logika bisnis (skor prioritas, duplikat, status)
- `laporan/views.py` tampilan & API (dashboard staf, upload perbaikan, laporan)
- `templates/` halaman HTML responsif
