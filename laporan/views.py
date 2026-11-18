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
from .forms import LaporanForm, PerbaikanForm
from .models import Laporan, Lokasi

staf_only = user_passes_test(lambda u: u.is_staff, login_url="login")


def beranda(request):
    qs = Laporan.objects.select_related("lokasi")
    kategori = request.GET.get("kategori")
    if kategori:
        qs = qs.filter(kategori=kategori)
    awal_bulan = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return render(request, "beranda.html", {
        "aktif": Laporan.objects.exclude(status="selesai").count(),
        "selesai_bulan": Laporan.objects.filter(
            status="selesai", riwayat__status="selesai", riwayat__waktu__gte=awal_bulan).distinct().count(),
        "terbaru": [services.dengan_skor(l) for l in qs[:6]],
        "kategori_list": Laporan.KATEGORI,
        "kategori": kategori,
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
    return render(request, "lapor_form.html", {"form": form, "duplikat": duplikat})


def detail(request, pk):
    laporan = services.dengan_skor(
        get_object_or_404(Laporan.objects.select_related("lokasi", "pelapor"), pk=pk))
    return render(request, "detail.html", {
        "l": laporan,
        "riwayat": laporan.riwayat.select_related("oleh"),
        "mendukung": request.user.is_authenticated and laporan.pendukung.filter(pk=request.user.pk).exists(),
        "status_list": Laporan.STATUS,
    })


@login_required
@require_POST
def dukung(request, pk):
    laporan = get_object_or_404(Laporan, pk=pk)
    if laporan.pendukung.filter(pk=request.user.pk).exists():
        laporan.pendukung.remove(request.user)
    else:
        laporan.pendukung.add(request.user)
    return redirect("detail", pk=pk)


@staf_only
@require_POST
def ubah_status(request, pk):
    laporan = get_object_or_404(Laporan, pk=pk)
    status = request.POST.get("status")
    catatan = request.POST.get("catatan_perbaikan", "").strip()
    foto = request.FILES.get("foto_perbaikan")
    if status in dict(Laporan.STATUS):
        services.catat_status(laporan, status, request.user, catatan=catatan, foto_perbaikan=foto)
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
            foto = form.cleaned_data.get("foto_perbaikan")
            services.catat_status(laporan, status, request.user, catatan=catatan, foto_perbaikan=foto)
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
    })


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
