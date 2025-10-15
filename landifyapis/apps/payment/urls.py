from django.urls import path

from .views import ConfirmMomoPaymentView, CreateMomoPaymentView

urlpatterns = [
    path("momo/create/", CreateMomoPaymentView.as_view(), name="create_momo_payment"),
    path("momo/confirm/<int:listing_vip_id>/", ConfirmMomoPaymentView.as_view(), name="confirm_momo_payment"),
]
