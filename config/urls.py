from django.contrib import admin
from django.urls import include, path
from workspace import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", views.CustomLoginView.as_view(), name="login"),
    path("accounts/register/", views.register, name="register"),
    path("accounts/register/verify/", views.register_verify, name="register_verify"),
    path("accounts/register/resend/", views.register_resend_otp, name="register_resend_otp"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("workspace.urls")),
]
