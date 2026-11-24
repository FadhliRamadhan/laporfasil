from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, reverse


class CustomLoginView(auth_views.LoginView):
    template_name = "registration/login.html"

    def get_success_url(self):
        url = self.get_redirect_url()
        if self.request.user.is_authenticated and self.request.user.is_staff:
            if not url or url == reverse("beranda"):
                return reverse("dashboard")
        return url or super().get_success_url()


urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", CustomLoginView.as_view(), name="login_direct"),
    path("accounts/login/", CustomLoginView.as_view(), name="login"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("laporan.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

