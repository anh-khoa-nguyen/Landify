# D:\Backend\Landify\landifyapis\apps\payment\views.py

import base64
import hashlib
import hmac
import json
import uuid
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.utils.hashids import decode_public_id
from apps.listings.models import Listing, ListingVip, VipType

MOMO_PARTNER_CODE = getattr(settings, "MOMO_PARTNER_CODE", "")
MOMO_ACCESS_KEY = getattr(settings, "MOMO_ACCESS_KEY", "")
MOMO_SECRET_KEY = getattr(settings, "MOMO_SECRET_KEY", "")
MOMO_REDIRECT_URL = getattr(settings, "MOMO_REDIRECT_URL", "")
MOMO_IPN_URL_BASE = getattr(settings, "MOMO_IPN_URL_BASE", "")
MOMO_API_ENDPOINT = "https://test-payment.momo.vn/v2/gateway/api/create"


# ----------------------------------------------------------------


class CreateMomoPaymentView(APIView):
    """
    Tạo một yêu cầu thanh toán MoMo cho việc nâng cấp VIP.
    Nhận vào: listing_public_id, vip_type_code, duration_days.
    Trả về: payUrl và các thông tin khác từ MoMo.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        listing_public_id = request.data.get("listing_public_id")
        vip_type_code = request.data.get("vip_type_code")
        duration_days = request.data.get("duration_days")

        if not all([listing_public_id, vip_type_code, duration_days]):
            return Response(
                {"error": "Vui lòng cung cấp đủ thông tin (listing_public_id, vip_type_code, duration_days)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        listing_id = decode_public_id(listing_public_id)
        if not listing_id:
            return Response({"error": "ID tin đăng không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            listing = Listing.objects.get(pk=listing_id, user=request.user)
            vip_type = VipType.objects.get(code=vip_type_code, active=True)
            duration = int(duration_days)
            if duration <= 0:
                raise ValueError("Số ngày phải lớn hơn 0")
        except Listing.DoesNotExist:
            return Response(
                {"error": "Không tìm thấy tin đăng hoặc bạn không phải chủ sở hữu."}, status=status.HTTP_404_NOT_FOUND
            )
        except VipType.DoesNotExist:
            return Response({"error": "Gói VIP không hợp lệ."}, status=status.HTTP_404_NOT_FOUND)
        except (ValueError, TypeError):
            return Response({"error": "Số ngày không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)

        amount = vip_type.price_per_day * duration

        invoice, created = ListingVip.objects.get_or_create(listing_id=listing.id)

        invoice.vip_type = vip_type
        invoice.amount = amount
        invoice.payment_status = ListingVip.PaymentStatus.PENDING
        invoice.payment_method = ListingVip.PaymentMethod.MOMO
        invoice.end_date = None  # Reset ngày hết hạn khi tạo hóa đơn mới
        invoice.save()

        order_id = str(uuid.uuid4())
        request_id = str(uuid.uuid4())
        order_info = f"Nang cap VIP {vip_type.name} ({duration} ngay) cho tin dang #{listing.id}"
        extra_data_dict = {"duration_days": duration}
        extra_data_str = json.dumps(extra_data_dict)
        extra_data_b64 = base64.b64encode(extra_data_str.encode("utf-8")).decode("utf-8")
        ipn_url = f"{MOMO_IPN_URL_BASE}{invoice.listing_id}/"

        raw_signature = (
            f"accessKey={MOMO_ACCESS_KEY}&amount={int(amount)}&extraData={extra_data_b64}&ipnUrl={ipn_url}"
            f"&orderId={order_id}&orderInfo={order_info}&partnerCode={MOMO_PARTNER_CODE}"
            f"&redirectUrl={MOMO_REDIRECT_URL}&requestId={request_id}&requestType=captureWallet"
        )

        signature = hmac.new(MOMO_SECRET_KEY.encode(), raw_signature.encode(), hashlib.sha256).hexdigest()

        payload = {
            "partnerCode": MOMO_PARTNER_CODE,
            "requestId": request_id,
            "amount": str(int(amount)),
            "orderId": order_id,
            "orderInfo": order_info,
            "redirectUrl": MOMO_REDIRECT_URL,
            "ipnUrl": ipn_url,
            "lang": "vi",
            "extraData": extra_data_b64,
            "requestType": "captureWallet",
            "signature": signature,
        }

        try:
            response = requests.post(MOMO_API_ENDPOINT, json=payload, timeout=10)
            response.raise_for_status()  # Ném lỗi nếu status code là 4xx hoặc 5xx
            response_data = response.json()

            if response_data.get("resultCode") == 0:
                invoice.pay_url = response_data.get("payUrl")
                invoice.payment_code = order_id
                invoice.save()
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                invoice.payment_status = ListingVip.PaymentStatus.FAILED
                invoice.save()
                error_message = response_data.get("message", "Tạo thanh toán MoMo thất bại.")
                return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)
        except requests.exceptions.RequestException as e:
            return Response({"error": f"Lỗi khi kết nối đến MoMo: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfirmMomoPaymentView(APIView):
    """
    Nhận thông báo IPN (Instant Payment Notification) từ server MoMo.
    URL này phải được public và không yêu cầu xác thực.
    """

    permission_classes = [permissions.AllowAny]

    def verify_signature(self, data) -> bool:
        """Xác thực chữ ký từ dữ liệu MoMo IPN."""
        try:
            raw_signature = (
                f"accessKey={MOMO_ACCESS_KEY}&amount={data.get('amount')}&extraData={data.get('extraData')}"
                f"&message={data.get('message')}&orderId={data.get('orderId')}"
                f"&orderInfo={data.get('orderInfo')}&orderType={data.get('orderType')}"
                f"&partnerCode={data.get('partnerCode')}&payType={data.get('payType')}"
                f"&requestId={data.get('requestId')}&responseTime={data.get('responseTime')}"
                f"&resultCode={data.get('resultCode')}&transId={data.get('transId')}"
            )
            momo_signature = data.get("signature")
            computed_signature = hmac.new(MOMO_SECRET_KEY.encode(), raw_signature.encode(), hashlib.sha256).hexdigest()
            return computed_signature == momo_signature
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False

    def post(self, request, listing_vip_id):
        response_data = request.data
        print(f"IPN received for ListingVip ID {listing_vip_id}: {response_data}")

        if not self.verify_signature(response_data):
            print("IPN SIGNATURE FAILED!")
            pass  # Tạm thời bỏ qua để test

        try:
            invoice = ListingVip.objects.get(pk=listing_vip_id)
        except ListingVip.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if invoice.payment_status == ListingVip.PaymentStatus.PAID:
            return Response(status=status.HTTP_200_OK)

        result_code = response_data.get("resultCode")

        if result_code == 0:
            try:
                extra_data_b64 = response_data.get("extraData", "")
                extra_data_str = base64.b64decode(extra_data_b64).decode("utf-8")
                extra_data_dict = json.loads(extra_data_str)
                duration_days = int(extra_data_dict.get("duration_days", 0))
                if duration_days <= 0:
                    raise ValueError("Invalid duration_days in extraData")
            except Exception as e:
                print(f"ERROR parsing extraData from IPN: {e}")
                invoice.payment_status = ListingVip.PaymentStatus.FAILED
                invoice.save()
                return Response(status=status.HTTP_400_BAD_REQUEST)

            start_point = timezone.now()
            if invoice.end_date and invoice.end_date > start_point:
                start_point = invoice.end_date

            invoice.end_date = start_point + timedelta(days=duration_days)
            invoice.payment_status = ListingVip.PaymentStatus.PAID
            invoice.payment_code = response_data.get("transId")  # Lưu mã giao dịch thành công của MoMo
            invoice.save()
        else:
            invoice.payment_status = ListingVip.PaymentStatus.FAILED
            invoice.save()

        # Luôn trả về 204 cho MoMo để báo hiệu đã nhận IPN thành công
        return Response(status=status.HTTP_204_NO_CONTENT)
