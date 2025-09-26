from datetime import datetime

from django.db import IntegrityError
from django.shortcuts import get_object_or_404

from rest_framework import parsers, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import services as verification_services

from apps.common.docs import verification_docs, utilities_docs
from apps.common import perms
from apps.common.services import BusinessLogicError, EkycError
from apps.properties.models import Property
from apps.interactions.serializers import ReviewSerializer
from apps.interactions import services as interactions_services
from apps.verification import services as verification_services



class VerificationViewSet(viewsets.ViewSet):
    """
    ViewSet xử lý các quy trình xác thực không CRUD: OTP và eKYC.
    """

    permission_classes = [permissions.IsAuthenticated]

    @verification_docs.request_otp_schema
    @action(methods=["post"], detail=False, url_path="request-otp")
    def request_phone_verification_otp(self, request):
        """Gửi mã OTP để xác thực SĐT của người dùng đã đăng nhập."""
        try:
            verification_services.request_phone_otp(user=request.user)
            return Response({"message": f"Đã gửi mã OTP đến {request.user.phone_number}."}, status=status.HTTP_200_OK)
        except BusinessLogicError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @verification_docs.verify_otp_schema
    @action(methods=["post"], detail=False, url_path="verify-otp")
    def verify_phone_otp(self, request):
        """Xác thực mã OTP để đăng nhập."""
        otp_code = request.data.get("otp")
        if not otp_code:
            return Response({"error": "Vui lòng cung cấp mã OTP."}, status=status.HTTP_400_BAD_REQUEST)

        is_verified = verification_services.verify_phone_otp(user=request.user, otp_code=otp_code)

        if is_verified:
            return Response({"message": "Xác thực số điện thoại thành công."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Mã OTP không hợp lệ hoặc đã hết hạn."}, status=status.HTTP_400_BAD_REQUEST)

    @verification_docs.verify_id_card_schema
    @action(methods=["post"], detail=False, url_path="verify-id-card", parser_classes=[parsers.MultiPartParser])
    def verify_id_card(self, request):
        """Bước 1 eKYC: Nhận diện và trích xuất thông tin từ CCCD."""
        id_card_image = request.FILES.get("id_card_image")
        if not id_card_image:
            return Response({"error": "Vui lòng cung cấp ảnh CCCD."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            extracted_data = verification_services.process_id_card_verification(user=request.user, id_card_image=id_card_image)
            return Response(
                {"message": "Đọc thông tin CCCD thành công.", "data": extracted_data}, status=status.HTTP_200_OK
            )
        except EkycError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:  # Catch other potential errors during API call
            return Response({"error": f"Đã có lỗi xảy ra: {str(e)}."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @verification_docs.verify_liveness_schema
    @action(methods=["post"], detail=False, url_path="verify-liveness", parser_classes=[parsers.MultiPartParser])
    def verify_liveness(self, request):
        """Bước 2 eKYC: Xác thực người thật và so khớp khuôn mặt."""
        user = request.user
        video_file = request.FILES.get("video")
        if not video_file:
            return Response({"error": "Vui lòng cung cấp video xác thực."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            verification_services.complete_ekyc_liveness_check(user=user, video_file=video_file)
            return Response({"message": "Xác minh danh tính hoàn tất!"}, status=status.HTTP_200_OK)

        except EkycError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "Đã có lỗi hệ thống xảy ra."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_property_or_404(pk):
    return get_object_or_404(Property, pk=pk)

# =================== ANALYSIS & UTILITIES ==========================

@utilities_docs.property_analysis_viewset_schema
class PropertyAnalysisViewSet(viewsets.ViewSet):
    """ViewSet cho các API phân tích, không theo mô hình CRUD."""

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["post"], url_path="feng-shui")
    def feng_shui_analysis(self, request, pk=None):
        """Phân tích phong thủy dựa trên ngày sinh và hướng nhà."""
        prop = get_property_or_404(pk)
        dob_str = request.data.get("date_of_birth")

        if not dob_str:
            return Response({"error": "Vui lòng cung cấp 'date_of_birth'."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            date_of_birth = datetime.strptime(dob_str, "%Y-%m-%d").date()
            direction_name = prop.direction.name if prop.direction else None

            result = verification_services.get_feng_shui_analysis(
                property_direction_name=direction_name, date_of_birth=date_of_birth
            )
            return Response(result, status=status.HTTP_200_OK)

        except ValueError:
            return Response(
                {"error": "Định dạng ngày sinh không hợp lệ. Vui lòng dùng 'YYYY-MM-DD'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except BusinessLogicError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@utilities_docs.agora_token_viewset_schema
class AgoraTokenViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(methods=["post"], detail=False, url_path="generate")
    def generate_token(self, request):
        channel_name = request.data.get("channelName")
        uid = request.user.id

        try:
            token_data = verification_services.generate_agora_token(
                channel_name=channel_name,
                uid=uid
            )
            # Token_data trả về từ service đã có dạng {"token": "...", "uid": ...}
            return Response(token_data, status=status.HTTP_200_OK)
        except BusinessLogicError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
