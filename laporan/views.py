import csv
import datetime
import io

import qrcode
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import services
from .forms import KomentarForm, LaporanForm, PengumumanForm, PerbaikanForm
from .models import Komentar, Laporan, Lokasi, Pengumuman

staf_only = user_passes_test(lambda u: u.is_staff, login_url="login")


def _ambil_laporan_data(request, mode="semua"):
    tab = request.GET.get("tab") or mode
    kategori = request.GET.get("kategori", "")
    status_filter = request.GET.get("status", "")
    sort = request.GET.get("sort", "prioritas")
    q = request.GET.get("q", "").strip()

    qs = Laporan.objects.select_related("lokasi", "pelapor", "petugas").prefetch_related("pendukung", "komentar")

    # Tab Filter
    if tab == "saya" and request.user.is_authenticated:
        qs = qs.filter(pelapor=request.user)
    elif tab == "didukung" and request.user.is_authenticated:
        qs = qs.filter(pendukung=request.user)
    elif tab == "mendesak":
        qs = qs.exclude(status="selesai")
    elif tab == "selesai":
        qs = qs.filter(status="selesai")

    # Kategori Filter
    if kategori:
        qs = qs.filter(kategori=kategori)

    # Status Filter
    if status_filter:
        qs = qs.filter(status=status_filter)

    # Pencarian Kata Kunci
    if q:
        qs = qs.filter(
            Q(judul__icontains=q) |
            Q(deskripsi__icontains=q) |
            Q(lokasi__nama__icontains=q) |
            Q(lokasi__gedung__icontains=q)
        )

    laporan_list = [services.dengan_skor(l) for l in qs]

    # Pengurutan
    if sort == "terbaru":
        laporan_list.sort(key=lambda l: l.dibuat, reverse=True)
    elif sort == "populer":
        laporan_list.sort(key=lambda l: l.pendukung.count(), reverse=True)
    else:  # prioritas
        if tab == "mendesak":
            laporan_list.sort(key=lambda l: l.skor, reverse=True)
        else:
            laporan_list.sort(key=lambda l: (1 if l.status == "selesai" else 0, -l.skor))

    awal_bulan = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    pengumuman_list = Pengumuman.objects.filter(aktif=True)[:3]

    # User statistics (Personal Dashboard overview)
    user_stats = {}
    if request.user.is_authenticated:
        user_laporan = Laporan.objects.filter(pelapor=request.user)
        user_stats = {
            "total": user_laporan.count(),
            "proses": user_laporan.exclude(status="selesai").count(),
            "selesai": user_laporan.filter(status="selesai").count(),
            "didukung": request.user.dukungan.count(),
        }

    # Campus statistics overview
    semua_laporan_count = Laporan.objects.count()
    aktif_count = Laporan.objects.exclude(status="selesai").count()
    selesai_bulan = Laporan.objects.filter(
        status="selesai", riwayat__status="selesai", riwayat__waktu__gte=awal_bulan
    ).distinct().count()

    supported_ids = set(request.user.dukungan.values_list("id", flat=True)) if request.user.is_authenticated else set()
    show_banner = (mode == "semua" and tab == "semua")

    return {
        "laporan_list": laporan_list,
        "tab": tab,
        "mode": mode,
        "show_banner": show_banner,
        "kategori": kategori,
        "status_filter": status_filter,
        "sort": sort,
        "q": q,
        "kategori_list": Laporan.KATEGORI,
        "status_list": Laporan.STATUS,
        "pengumuman_list": pengumuman_list,
        "user_stats": user_stats,
        "aktif": aktif_count,
        "selesai_bulan": selesai_bulan,
        "total_kampus": semua_laporan_count,
        "supported_ids": supported_ids,
    }


def beranda(request):
    ctx = _ambil_laporan_data(request, mode="semua")
    return render(request, "beranda.html", ctx)


@login_required
def laporan_saya(request):
    ctx = _ambil_laporan_data(request, mode="saya")
    return render(request, "beranda.html", ctx)


@login_required
def didukung_saya(request):
    ctx = _ambil_laporan_data(request, mode="didukung")
    return render(request, "beranda.html", ctx)


def mendesak(request):
    ctx = _ambil_laporan_data(request, mode="mendesak")
    return render(request, "beranda.html", ctx)


def selesai(request):
    ctx = _ambil_laporan_data(request, mode="selesai")
    return render(request, "beranda.html", ctx)


@login_required
def profil(request):
    user_laporan = Laporan.objects.filter(pelapor=request.user).order_by("-dibuat")
    total_laporan = user_laporan.count()
    total_proses = user_laporan.exclude(status="selesai").count()
    total_selesai = user_laporan.filter(status="selesai").count()
    total_didukung = request.user.dukungan.count()
    recent_laporan = [services.dengan_skor(l) for l in user_laporan[:5]]
    return render(request, "profil.html", {
        "total_laporan": total_laporan,
        "total_proses": total_proses,
        "total_selesai": total_selesai,
        "total_didukung": total_didukung,
        "recent_laporan": recent_laporan,
    })


@login_required
def buat(request):
    awal = Lokasi.objects.filter(kode=request.GET.get("lokasi")).first()
    form = LaporanForm(request.POST or None, request.FILES or None, initial={"lokasi": awal})
    duplikat = []
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        duplikat = services.cari_duplikat(data["lokasi"], data["kategori"])
        if not duplikat or request.POST.get("tetap_kirim"):
            laporan = form.save(commit=False)
            laporan.pelapor = request.user
            laporan.save()
            services.catat_status(laporan, "dilaporkan", request.user)
            messages.success(request, "Laporan terkirim.")
            return redirect("detail", pk=laporan.pk)
    return render(request, "lapor_form.html", {
        "form": form,
        "duplikat": duplikat,
        "semua_lokasi": Lokasi.objects.all(),
        "semua_kategori": Laporan.KATEGORI,
    })


def detail(request, pk):
    laporan = services.dengan_skor(
        get_object_or_404(Laporan.objects.select_related("lokasi", "pelapor", "petugas"), pk=pk))
    return render(request, "detail.html", {
        "l": laporan,
        "riwayat": laporan.riwayat.select_related("oleh"),
        "komentar_list": laporan.komentar.select_related("penulis"),
        "komentar_form": KomentarForm(),
        "mendukung": request.user.is_authenticated and laporan.pendukung.filter(pk=request.user.pk).exists(),
        "status_list": Laporan.STATUS,
    })


@login_required
@require_POST
def tambah_komentar(request, pk):
    laporan = get_object_or_404(Laporan, pk=pk)
    isi = request.POST.get("isi", "").strip()
    if isi:
        Komentar.objects.create(laporan=laporan, penulis=request.user, isi=isi)
        messages.success(request, "Tanggapan Anda berhasil ditambahkan.")
    return redirect("detail", pk=pk)


@login_required
@require_POST
def dukung(request, pk):
    laporan = get_object_or_404(Laporan, pk=pk)
    if laporan.pendukung.filter(pk=request.user.pk).exists():
        laporan.pendukung.remove(request.user)
        messages.info(request, f"Dukungan untuk '{laporan.judul}' dibatalkan.")
    else:
        laporan.pendukung.add(request.user)
        messages.success(request, f"Dukungan Anda untuk '{laporan.judul}' telah dicatat!")
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("detail", pk=pk)


@staf_only
@require_POST
def ubah_status(request, pk):
    laporan = get_object_or_404(Laporan, pk=pk)
    status = request.POST.get("status")
    catatan = request.POST.get("catatan_perbaikan", "").strip()
    target_selesai_val = request.POST.get("target_selesai")
    target_selesai = None
    if target_selesai_val:
        try:
            target_selesai = datetime.date.fromisoformat(target_selesai_val)
        except (ValueError, TypeError):
            pass
    foto = request.FILES.get("foto_perbaikan")
    if status in dict(Laporan.STATUS):
        services.catat_status(laporan, status, request.user, catatan=catatan, foto_perbaikan=foto, target_selesai=target_selesai)
        status_label = dict(Laporan.STATUS).get(status)
        pesan = f"Status laporan '{laporan.judul}' diperbarui ke '{status_label}'."
        if foto:
            pesan += " Foto hasil perbaikan berhasil diunggah."
        messages.success(request, pesan)
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("detail", pk=pk)


@staf_only
def upload_perbaikan(request, pk):
    laporan = services.dengan_skor(get_object_or_404(Laporan.objects.select_related("lokasi", "pelapor"), pk=pk))
    if request.method == "POST":
        form = PerbaikanForm(request.POST, request.FILES, instance=laporan)
        if form.is_valid():
            laporan = form.save(commit=False)
            status = form.cleaned_data["status"]
            catatan = form.cleaned_data["catatan_perbaikan"]
            target = form.cleaned_data.get("target_selesai")
            foto = form.cleaned_data.get("foto_perbaikan")
            services.catat_status(laporan, status, request.user, catatan=catatan, foto_perbaikan=foto, target_selesai=target)
            messages.success(request, f"Hasil perbaikan laporan '{laporan.judul}' berhasil disimpan.")
            return redirect("dashboard")
    else:
        form = PerbaikanForm(instance=laporan)
    return render(request, "upload_perbaikan.html", {"laporan": laporan, "form": form})


@staf_only
def dashboard(request):
    status_filter = request.GET.get("status", "")
    kategori_filter = request.GET.get("kategori", "")
    urgensi_filter = request.GET.get("urgensi", "")
    q = request.GET.get("q", "").strip()

    qs = Laporan.objects.select_related("lokasi", "pelapor", "petugas")

    if status_filter:
        qs = qs.filter(status=status_filter)
    if kategori_filter:
        qs = qs.filter(kategori=kategori_filter)
    if urgensi_filter:
        try:
            qs = qs.filter(urgensi=int(urgensi_filter))
        except ValueError:
            pass
    if q:
        qs = qs.filter(
            Q(judul__icontains=q) |
            Q(deskripsi__icontains=q) |
            Q(lokasi__nama__icontains=q) |
            Q(lokasi__gedung__icontains=q)
        )

    laporan_list = [services.dengan_skor(l) for l in qs]
    # Urutkan: laporan yang belum selesai berdasarkan skor prioritas tertinggi, kemudian yang sudah selesai
    laporan_list.sort(key=lambda l: (1 if l.status == "selesai" else 0, -l.skor))

    semua_db = Laporan.objects.all()
    aktif_qs = semua_db.exclude(status="selesai")
    selesai_qs = semua_db.filter(status="selesai")

    aktif_n = aktif_qs.count()
    selesai_n = selesai_qs.count()
    dilaporkan_n = semua_db.filter(status="dilaporkan").count()
    diverifikasi_n = semua_db.filter(status="diverifikasi").count()
    dikerjakan_n = semua_db.filter(status="dikerjakan").count()

    per_lokasi = list(Lokasi.objects.annotate(
        n=Count("laporan", filter=~Q(laporan__status="selesai"))).filter(n__gt=0).order_by("-n")[:5])
    maks = per_lokasi[0].n if per_lokasi else 1
    for x in per_lokasi:
        x.persen = round(x.n * 100 / maks)

    mendesak_n = sum(1 for l in [services.dengan_skor(x) for x in aktif_qs] if l.skor >= 80)
    rata = services.rata_rata_hari(selesai_qs)

    galeri_selesai = Laporan.objects.filter(status="selesai", foto_perbaikan__isnull=False).exclude(foto_perbaikan="").select_related("lokasi", "petugas")[:6]
    if not galeri_selesai.exists():
        galeri_selesai = Laporan.objects.filter(status="selesai").select_related("lokasi", "petugas")[:6]

    return render(request, "dashboard.html", {
        "laporan_list": laporan_list,
        "total_n": semua_db.count(),
        "aktif_n": aktif_n,
        "selesai_n": selesai_n,
        "dilaporkan_n": dilaporkan_n,
        "diverifikasi_n": diverifikasi_n,
        "dikerjakan_n": dikerjakan_n,
        "mendesak_n": mendesak_n,
        "rata": rata,
        "per_lokasi": per_lokasi,
        "prioritas": [l for l in laporan_list if l.status != "selesai"][:5],
        "status_list": Laporan.STATUS,
        "kategori_list": Laporan.KATEGORI,
        "urgensi_list": Laporan.URGENSI,
        "status_filter": status_filter,
        "kategori_filter": kategori_filter,
        "urgensi_filter": urgensi_filter,
        "q": q,
        "galeri_selesai": galeri_selesai,
        "pengumuman_list": Pengumuman.objects.all()[:5],
        "pengumuman_form": PengumumanForm(),
    })


@staf_only
@require_POST
def tambah_pengumuman(request):
    form = PengumumanForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Pengumuman pemeliharaan / informasi kampus berhasil dipublikasikan.")
    return redirect("dashboard")


@staf_only
def ekspor_csv(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    waktu_str = timezone.now().strftime("%Y%m%d_%H%M")
    response["Content-Disposition"] = f'attachment; filename="laporfasil_{waktu_str}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "ID", "Waktu Lapor", "Judul", "Kategori", "Lokasi", "Gedung",
        "Urgensi", "Status", "Skor Prioritas", "Pelapor", "Anonim", "Pendukung",
        "Target Selesai", "Selesai Pada", "Petugas", "Catatan Perbaikan", "Deskripsi"
    ])

    for l in Laporan.objects.select_related("lokasi", "pelapor", "petugas").order_by("-dibuat"):
        l = services.dengan_skor(l)
        writer.writerow([
            l.pk,
            l.dibuat.strftime("%Y-%m-%d %H:%M"),
            l.judul,
            l.get_kategori_display(),
            l.lokasi.nama,
            l.lokasi.gedung,
            l.get_urgensi_display(),
            l.get_status_display(),
            l.skor,
            l.pelapor.username,
            "Ya" if l.is_anonim else "Tidak",
            l.pendukung.count(),
            l.target_selesai.strftime("%Y-%m-%d") if l.target_selesai else "-",
            l.selesai_pada.strftime("%Y-%m-%d %H:%M") if l.selesai_pada else "-",
            l.petugas.username if l.petugas else "-",
            l.catatan_perbaikan.replace("\n", " ") if l.catatan_perbaikan else "-",
            l.deskripsi.replace("\n", " "),
        ])
    return response


@staf_only
def qr_daftar(request):
    return render(request, "qr_daftar.html", {"lokasi": Lokasi.objects.all()})


def qr(request, kode):
    lokasi = get_object_or_404(Lokasi, kode=kode)
    url = request.build_absolute_uri(reverse("buat")) + f"?lokasi={lokasi.kode}"
    buf = io.BytesIO()
    qrcode.make(url).save(buf, format="PNG")
    return HttpResponse(buf.getvalue(), content_type="image/png")


def daftar(request):
    form = UserCreationForm(request.POST or None)
    if form.is_valid():
        login(request, form.save())
        return redirect("beranda")
    return render(request, "registration/daftar.html", {"form": form})
