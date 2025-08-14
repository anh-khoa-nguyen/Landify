#=================== Import ==========================
# Django Core
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count

# Libraries
import cloudinary
# import uuid, hmac, json, requests, random, hashlib
from rest_framework.parsers import MultiPartParser, FormParser
from geopy.distance import geodesic

# REST Framework
from rest_framework import viewsets, generics, status, parsers, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

# Modules
from landifys import serializers, paginators, perms
from landifys.models import *

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db.models import Avg
from django.core.cache import cache

# Etc
from . import utils
from . import tasks
from .func import fengshui
import requests
from datetime import datetime
from cloudinary.exceptions import Error as CloudinaryError

class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter()
    serializer_class = serializers.UserSerializer
    parser_classes = [parsers.MultiPartParser]

    # --- Basic ---
    def get_permissions(self):
        if self.action in ['disable']:
            return [perms.IsAdminOrForbidden()]
        elif self.action in ['current_user', 'follow']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @action(methods=['get'], url_path='current_user', detail=False)
    def current_user(self, request):
        user = request.user
        return Response(serializers.UserSerializer(user).data)

    # --- Admin ---
    @action(methods=['patch'], url_path='disable', detail=True)
    def disable_account(self, request, pk=None):
        try:
            user_to_toggle = self.get_object()
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if user_to_toggle == request.user:
            return Response({"error": "Admin cannot disable their own account."}, status=status.HTTP_400_BAD_REQUEST)

        user_to_toggle.is_active = not user_to_toggle.is_active
        user_to_toggle.save(update_fields=['is_active'])

        new_status = "enabled" if user_to_toggle.is_active else "disabled"
        message = f"User {user_to_toggle.username} has been {new_status}."

        serializer = self.get_serializer(user_to_toggle)
        return Response({"message": message, "data": serializer.data}, status=status.HTTP_200_OK)

    # --- User ---
    @action(methods=['post'], url_path='follow', detail=True)
    def toggle_follow(self, request, pk=None):
        try:
            user_to_toggle = self.get_object()
            print(user_to_toggle)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if user_to_toggle == request.user:
            return Response({"error": "You cannot follow yourself."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            subscription = Subscription.objects.get(
                follower=request.user,
                following=user_to_toggle
            )
            subscription.delete()
            return Response(
                {"status": "unfollowed", "message": f"Successfully unfollowed {user_to_toggle.username}."},
                status=status.HTTP_200_OK
            )

        except Subscription.DoesNotExist:
            Subscription.objects.create(
                follower=request.user,
                following=user_to_toggle
            )
            return Response(
                {"status": "followed", "message": f"Successfully followed {user_to_toggle.username}."},
                status=status.HTTP_201_CREATED
            )

    @action(methods=['patch'], url_path='change_avatar', detail=False)
    def change_avatar(self, request):
        user = request.user
        avatar_file = request.FILES.get('avatar')

        if not avatar_file:
            return Response({'message': 'Avatar file is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uploaded_avatar = cloudinary.uploader.upload(avatar_file)
            user.avatar = uploaded_avatar['secure_url']
            user.save()
            return Response({'message': 'Avatar updated successfully.', 'avatar': user.avatar},
                            status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'message': 'Avatar upload failed', 'error': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['patch'], url_path='change_password', detail=False)
    def change_password(self, request):
        user = request.user
        password = request.data.get('password')

        if not password:
            return Response({'message': 'Password is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user.set_password(password)
            user.change_password_required = False
            user.save()

            # Twilio message!
            try:
                phone_number = user.phone_number

                if not phone_number:
                    return Response({"message": "User does not have a registered phone number."},
                                    status=status.HTTP_400_BAD_REQUEST)

                message_body = "Your password has been updated successfully. If this wasn't you, please contact support."

                sms_response = utils.send_sms(phone_number, message_body)

                if sms_response.get("message") == "SMS sent successfully":
                    print(f"SMS successfully sent. SID: {sms_response.get('sid')}")
                else:
                    print(f"Failed to send SMS: {sms_response.get('error')}")

            except Exception as sms_error:
                print(f"Error sending SMS: {sms_error}")

            return Response({'message': 'Password updated successfully.'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'message': 'An error occurred while updating the password.', 'error': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# =============================================================================
# 1. ĐĂNG TIN, LỌC VÀ TÌM KIẾM NHÀ ĐẤT
# =============================================================================

class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.filter(active=True, status=Listing.Status.AVAILABLE)
    serializer_class = serializers.ListingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'search']:
            self.permission_classes = [permissions.AllowAny]
        elif self.action == 'create':
            self.permission_classes = [permissions.IsAuthenticated, perms.IsIdentityVerified]
        elif self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [permissions.IsAuthenticated, perms.IsOwnerOrAdmin]
        else:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, active=True)

    def get_queryset(self):
        queryset = self.queryset.filter(active=True)
        listing_type_name = self.request.query_params.get('listing_type__name')
        if listing_type_name:
            queryset = queryset.filter(listing_type__name__iexact=listing_type_name)
        return queryset

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        params = request.query_params
        query = params.get('q', '')
        min_price = params.get('min_price')
        max_price = params.get('max_price')
        property_type = params.get('property_type')
        min_bedrooms = params.get('min_bedrooms')
        utilities = params.get('utilities')

        # Xây dựng query phức tạp với Q objects
        filters = Q(title__icontains=query) | Q(property__location__street__icontains=query) | \
                  Q(property__location__district__name__icontains=query)

        if min_price:
            filters &= Q(price__gte=min_price)
        if max_price:
            filters &= Q(price__lte=max_price)
        if property_type:
            filters &= Q(property__property_type__name__iexact=property_type)
        if min_bedrooms:
            filters &= Q(property__bedroom_count__gte=min_bedrooms)
        if utilities:
            utility_list = [u.strip() for u in utilities.split(',')]
            filters &= Q(property__utilities__name__in=utility_list)

        queryset = Listing.objects.filter(filters).distinct()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='protest', permission_classes=[permissions.IsAuthenticated])
    def protest(self, request, pk=None):
        try:
            listing = Listing.objects.get(pk=pk)
        except Listing.DoesNotExist:
            return Response({"error": "Tin đăng không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

        # 1. Người kháng nghị phải là chủ của tin đăng
        if request.user != listing.user:
            return Response(
                {"error": "Bạn không có quyền kháng nghị cho tin đăng này."},
                status=status.HTTP_403_FORBIDDEN
            )

        # 2. Chỉ được kháng nghị các tin đăng đã bị từ chối (tức là active=False)
        if listing.active:
            return Response(
                {"error": "Bạn chỉ có thể kháng nghị các tin đăng đã bị từ chối."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Kiểm tra xem đã có kháng nghị nào đang chờ xử lý cho tin này chưa
        if Protest.objects.filter(listing=listing, status=Protest.Status.IN_PROGRESS).exists():
            return Response(
                {"error": "Tin đăng này đang chờ xử lý."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- TẠO KHÁNG NGHỊ VÀ GỬI THÔNG BÁO ---
        serializer = serializers.ProtestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            protest_instance = serializer.save(listing=listing, protester=request.user)

            tasks.notify_admins_of_new_protest.delay(
                protest_id=protest_instance.id,
                protester_username=request.user.username,
                listing_title=listing.title
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# =============================================================================
# 2. TƯƠNG TÁC NGƯỜI DÙNG: BÁO CÁO, HẸN GẶP, QUAN TÂM
# =============================================================================

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = serializers.ReportSerializer

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [perms.IsAdminOrForbidden]
        return super().get_permissions()

    def get_queryset(self):
        """Admin thấy hết, user chỉ thấy report của mình."""
        if self.request.user.role == User.Role.ADMIN:
            return super().get_queryset()
        return Report.objects.filter(reporter=self.request.user)

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user, active=True)

class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = serializers.AppointmentSerializer

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [permissions.IsAuthenticated, perms.IsIdentityVerified]
        else:
            self.permission_classes = [permissions.IsAuthenticated, perms.IsOwnerOrAdmin]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, 'role', None) == User.Role.ADMIN:
            return super().get_queryset()
        return Appointment.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, active=True)

class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, active=True)

# =============================================================================
# 3. XÁC THỰC VÀ BẢO MẬT
# =============================================================================

class AuthVerificationView(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(methods=['post'], url_path='request-otp', detail=False)
    def request_otp(self, request):
        try:
            user = request.user
            phone_number = user.phone_number

            if not phone_number:
                return Response({"error": "Người dùng chưa cập nhật số điện thoại."},
                                status=status.HTTP_400_BAD_REQUEST)

            if not phone_number.startswith('+'):
                return Response({
                                    "error": "Số điện thoại không hợp lệ. Vui lòng sử dụng định dạng có mã quốc gia (ví dụ: +84xxxxxxxxx)."},
                                status=status.HTTP_400_BAD_REQUEST)

            otp_code = utils.generate_otp()
            utils.save_otp_to_cache(user.id, otp_code)
            message_body = f"[Landify] Mã xác thực của bạn là: {otp_code}. Mã có hiệu lực trong 5 phút."

            sms_response = utils.send_sms(phone_number, message_body)

            if "error" in sms_response:
                print(f"Twilio Error: {sms_response['error']}")
                return Response({"error": "Không thể gửi mã OTP vào lúc này. Vui lòng thử lại sau."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({"message": f"Đã gửi mã OTP đến số {phone_number}."}, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Error in request_otp: {str(e)}")
            return Response({"error": "Đã có lỗi xảy ra trong quá trình yêu cầu OTP."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['post'], url_path='verify-otp', detail=False)
    def verify_otp(self, request):
        try:
            user = request.user
            otp_code = request.data.get('otp')

            if not otp_code:
                return Response({"error": "Vui lòng cung cấp mã OTP."}, status=status.HTTP_400_BAD_REQUEST)

            is_valid = utils.verify_otp_from_cache(user.id, otp_code)

            if is_valid:
                if not user.is_phone_verified:
                    user.is_phone_verified = True
                    user.save(update_fields=['is_phone_verified'])
                return Response({"message": "Xác thực số điện thoại thành công."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Mã OTP không hợp lệ hoặc đã hết hạn."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(f"Error in verify_otp: {str(e)}")
            return Response({"error": "Đã có lỗi xảy ra trong quá trình xác thực."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['post'], url_path='verify-id-card', detail=False)
    def verify_id_card(self, request):
        """
        Bước 1 của eKYC: Nhận diện và trích xuất thông tin từ CCCD.
        """
        try:
            user = request.user
            id_card_image = request.FILES.get('id_card_image')

            if not id_card_image:
                return Response({"error": "Vui lòng cung cấp ảnh CCCD."}, status=status.HTTP_400_BAD_REQUEST)

            # Gọi API ID Recognition của FPT
            idr_response = utils.call_fpt_idr_api(id_card_image)

            if idr_response.get('errorCode') != 0:
                print(f"FPT IDR Error: {idr_response.get('errorMessage')}")
                return Response({"error": "Không thể đọc thông tin từ ảnh CCCD. Vui lòng dùng ảnh rõ nét hơn."},
                                status=status.HTTP_400_BAD_REQUEST)

            # Lấy dữ liệu thành công
            extracted_data = idr_response.get('data')[0]  # API trả về list, lấy phần tử đầu

            id_card_image.seek(0)
            full_image_data = id_card_image.read()

            cache_key = f'ekyc_image_{user.id}'
            cache.set(cache_key, full_image_data, timeout=600)

            # Lưu dữ liệu đã trích xuất và cập nhật trạng thái cho user
            user.id_card_data = extracted_data
            user.is_id_card_verified = True
            user.save(update_fields=['id_card_data', 'is_id_card_verified'])

            # Trả về thông tin đã đọc được cho client để xác nhận
            return Response({
                "message": "Đọc thông tin CCCD thành công. Vui lòng tiến hành xác thực khuôn mặt.",
                "data": extracted_data
            }, status=status.HTTP_200_OK)

        except requests.exceptions.RequestException as e:
            print(f"API Connection Error: {str(e)}")
            return Response({"error": "Không thể kết nối đến dịch vụ xác minh. Vui lòng thử lại sau."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            print(f"Error in verify_id_card: {str(e)}")
            return Response({"error": "Đã có lỗi xảy ra trong quá trình xử lý CCCD."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['post'], url_path='verify-liveness', detail=False)
    def verify_liveness(self, request):
        try:
            user = request.user
            video_file = request.FILES.get('video')
            id_card_image_data = request.FILES.get('image') #Tạm thời

            if not video_file:
                return Response({"error": "Vui lòng cung cấp video xác thực."}, status=status.HTTP_400_BAD_REQUEST)

            # --- Bước 1: Lấy ảnh CCCD gốc từ cache ---
            # cache_key = f'ekyc_image_{user.id}'
            # id_card_image_data = cache.get(cache_key)

            if not id_card_image_data:
                return Response(
                    {"error": "Phiên xác thực đã hết hạn hoặc có lỗi. Vui lòng bắt đầu lại từ bước xác thực CCCD."},
                    status=status.HTTP_400_BAD_REQUEST)

            # --- Bước 2: Gọi API Liveness của FPT ---
            liveness_response = utils.call_fpt_liveness_api(video_file, id_card_image_data)

            if liveness_response.get('code') != '200':
                print(f"FPT API Top-Level Error: {liveness_response.get('message')}")
                return Response({"error": "Dịch vụ xác thực đang gặp sự cố. Vui lòng thử lại sau."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            liveness_data = liveness_response.get('liveness', {})
            face_match_data = liveness_response.get('face_match', {})

            is_live_str = liveness_data.get('is_live')
            is_match_str = face_match_data.get('isMatch')

            is_live = (is_live_str == 'true')
            is_match = (is_match_str == 'true')

            if is_live and is_match:
                user.is_id_card_verified = True
                user.id_card_data = None
                user.save(update_fields=['is_id_card_verified', 'id_card_data'])
                # cache.delete(cache_key)
                return Response({"message": "Xác minh danh tính hoàn tất!"}, status=status.HTTP_200_OK)
            else:
                error_messages = []
                if not is_live:
                    error_messages.append("Không phải người thật.")
                if not is_match:
                    error_messages.append("Khuôn mặt không khớp với CCCD.")

                # Nếu không có thông tin gì, trả về lỗi chung
                if not error_messages:
                    return Response({"error": "Xác thực thất bại. Không rõ nguyên nhân."},
                                    status=status.HTTP_400_BAD_REQUEST)

                return Response({"error": " ".join(error_messages)}, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.RequestException as e:
            # Bắt lỗi kết nối tới API của FPT
            print(f"API Connection Error: {str(e)}")
            return Response({"error": "Không thể kết nối đến dịch vụ xác minh. Vui lòng thử lại sau."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

        except Exception as e:
            print(f"Error in verify_liveness: {str(e)}")
            return Response({"error": "Đã có lỗi xảy ra trong quá trình xác thực khuôn mặt."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# =============================================================================
# BẤT ĐỘNG SẢN
# =============================================================================
class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.select_related(
        'owner', 'property_type', 'location', 'direction'
    ).prefetch_related('utilities')

    serializer_class = serializers.PropertySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.AllowAny]

        elif self.action == 'create':
            self.permission_classes = [permissions.IsAuthenticated, perms.IsIdentityVerified]

        elif self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [permissions.IsAuthenticated, perms.IsOwnerOrAdmin]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class MediaViewSet(viewsets.ModelViewSet):
    queryset = PropertyMedia.objects.all()
    serializer_class = serializers.PropertyMediaSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [permissions.IsAuthenticated, perms.IsOwnerOrAdmin]
        return super().get_permissions()

    def get_queryset(self):
        property_pk = self.kwargs.get('property_pk')
        if property_pk:
            return self.queryset.filter(property_id=property_pk)
        return self.queryset.none()

    def perform_create(self, serializer):
        property_pk = self.kwargs.get('property_pk')
        try:
            prop = Property.objects.get(pk=property_pk)
        except Property.DoesNotExist:
            raise serializers.ValidationError("Bất động sản không tồn tại.")

        media_file = self.request.FILES.get('media_file')
        if not media_file:
            raise serializers.ValidationError({"media_file": "Vui lòng cung cấp file phương tiện."})

        try:
            uploaded_media = cloudinary.uploader.upload(
                media_file,
                resource_type="auto"
            )

            media_url = uploaded_media.get('secure_url')
            if not media_url:
                raise serializers.ValidationError("Upload file thất bại, không nhận được URL.")

        except CloudinaryError as e:
            print(f"Cloudinary upload error: {e}")
            raise serializers.ValidationError({"media_file": "Upload file thất bại, vui lòng thử lại."})
        except Exception as e:
            print(f"Unexpected error during upload: {e}")
            raise serializers.ValidationError({"detail": "Có lỗi không mong muốn xảy ra."})

        serializer.save(property=prop, url=media_url, active=True)

# =============================================================================
# 4. PHÂN TÍCH DỮ LIỆU, PHONG THỦY VÀ ĐÁNH GIÁ
# =============================================================================

class PropertyAnalysisViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=['get'])
    def analysis(self, request, pk=None):
        try:
            prop = Property.objects.get(pk=pk)
        except Property.DoesNotExist:
            return Response({"error": "Bất động sản không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

        # --- Logic phân tích ---
        # Đây là phần phức tạp, cần kết hợp nhiều nguồn dữ liệu và có thể là AI.
        # 1. Vị trí, ngập úng, quy hoạch: Cần tích hợp API bản đồ (Google Maps, hoặc các API quy hoạch của nhà nước nếu có).
        # 2. Biến động giá: Cần thu thập dữ liệu lịch sử giá của các BĐS trong cùng khu vực (quận, phường).
        # 3. Dự đoán xu hướng: Sử dụng mô hình Machine Learning (ví dụ: Linear Regression, Gradient Boosting)
        #    dựa trên các đặc điểm (diện tích, số phòng, vị trí) và dữ liệu giá lịch sử.
        # 4. So sánh: Query các BĐS tương tự trong bán kính X km hoặc cùng phường/quận.

        # --- Dữ liệu giả lập để minh họa ---
        analysis_data = {
            "location_analysis": {
                "flood_risk": "Thấp", # Dữ liệu từ API bản đồ ngập úng
                "traffic_density": "Trung bình", # Dữ liệu từ Google Maps Traffic
                "planning_info": "Khu dân cư ổn định", # Dữ liệu từ API quy hoạch
                "security_level": "Cao" # Dựa trên thống kê hoặc đánh giá cộng đồng
            },
            "price_analysis": {
                "estimated_value": "5.2 tỷ VND", # Kết quả từ mô hình AI
                "price_trend": "Tăng 5% so với năm trước", # Dựa trên dữ liệu lịch sử
                "comparison": [ # So sánh với các BĐS lân cận
                    {"id": 102, "price": "5.5 tỷ VND", "area": 80},
                    {"id": 105, "price": "4.9 tỷ VND", "area": 75},
                ]
            }
        }
        return Response(analysis_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='feng-shui')
    def feng_shui_analysis(self, request, pk=None):
        """
        Phân tích phong thủy và gợi ý.
        URL: /api/properties/{id}/feng-shui/
        Body: { "birth_year": 1990 }
        """
        try:
            prop = Property.objects.get(pk=pk)
        except Property.DoesNotExist:
            return Response({"error": "Bất động sản không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

        birth_date = None

        # --- BƯỚC 1: Ưu tiên lấy năm sinh từ request body ---
        # Điều này cho phép người dùng (kể cả chưa đăng nhập) xem cho bất kỳ năm nào.
        dob_str = request.data.get('date_of_birth')
        if dob_str:
            try:
                birth_date = datetime.strptime(dob_str, '%d-%m-%y').date()
            except (ValueError, TypeError):
                return Response(
                    {"error": "Định dạng ngày tháng không hợp lệ. Vui lòng sử dụng định dạng 'YYYY-MM-DD'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        elif request.user.is_authenticated and request.user.date_of_birth:
            birth_date = request.user.date_of_birth

        if not birth_date:
            return Response(
                {
                    "error": "Vui lòng cung cấp 'birth_year' trong request hoặc đăng nhập và cập nhật ngày sinh trong hồ sơ."},
                status=status.HTTP_400_BAD_REQUEST
            )

        year = birth_date.year
        month = birth_date.month

        if month == 1:
            year -= 1

        menh = fengshui.calculate_menh(year)
        if not menh:
            return Response({"error": "Không thể tính mệnh cho năm sinh cung cấp."}, status=status.HTTP_400_BAD_REQUEST)

        if not prop.direction:
            return Response({"error": "Bất động sản này chưa có thông tin hướng nhà."},
                            status=status.HTTP_400_BAD_REQUEST)

        prop_direction_name = prop.direction.name
        prop_direction_element = prop.direction.element

        analysis_result = fengshui.analyze_feng_shui_rules(menh, prop_direction_name, prop_direction_element)

        result = {
            "user_menh": menh,
            "property_direction": prop_direction_name,
            "compatibility_score": analysis_result["score"],
            "analysis": analysis_result["analysis"]
        }

        return Response(result, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='rate',
            permission_classes=[permissions.IsAuthenticated, perms.IsIdentityVerified])
    def rate(self, request, pk=None):
        try:
            prop = Property.objects.select_related('location').get(pk=pk)
        except Property.DoesNotExist:
            return Response({"error": "Bất động sản không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

        user_lat = request.data.get('user_lat')
        user_lng = request.data.get('user_lng')

        if user_lat is None or user_lng is None:
            return Response(
                {"error": "Vui lòng cung cấp vị trí hiện tại của bạn để thực hiện đánh giá."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not prop.location or not prop.location.lat or not prop.location.lng:
            return Response({"error": "Bất động sản này không có thông tin vị trí để xác minh."},
                            status=status.HTTP_400_BAD_REQUEST)

        MAX_DISTANCE_KM = 0.5

        try:
            user_coords = (float(user_lat), float(user_lng))
            prop_coords = (float(prop.location.lat), float(prop.location.lng))
            print(user_coords)
            print(prop_coords)

            distance = geodesic(user_coords, prop_coords).kilometers

            if distance > MAX_DISTANCE_KM:
                return Response(
                    {
                        "error": f"Bạn cần ở trong phạm vi {MAX_DISTANCE_KM} km để đánh giá. Khoảng cách hiện tại của bạn là {distance:.2f} km."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response({"error": "Tọa độ cung cấp không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = serializers.ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, property=prop)
            return Response({"message": "Cảm ơn bạn đã đánh giá!"}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='heatmap', permission_classes=[permissions.AllowAny])
    def potential_heatmap(self, request):
        """
        Cung cấp dữ liệu cho bản đồ nhiệt.
        URL: /api/properties/heatmap/
        """
        # TODO:
        # 1. Tổng hợp tất cả các BĐS.
        # 2. Tính "điểm tiềm năng" cho mỗi BĐS dựa trên:
        #    - Lượt xem (view_count)
        #    - Số lượt thêm vào wishlist
        #    - Đánh giá trung bình (star_average)
        #    - Kết quả từ mô hình dự đoán giá
        # 3. Trả về danh sách các tọa độ (lat, lng) và điểm tiềm năng (weight).
        #    [ { "lat": 10.77, "lng": 106.69, "weight": 0.8 }, ... ]

        # Dữ liệu giả lập
        heatmap_data = [
            {"lat": 10.7769, "lng": 106.6954, "weight": 0.9}, # Quận 1
            {"lat": 10.8231, "lng": 106.6297, "weight": 0.6}, # Tân Bình
            {"lat": 10.7909, "lng": 106.7224, "weight": 0.8}, # Bình Thạnh
        ]
        return Response(heatmap_data, status=status.HTTP_200_OK)


# =============================================================================
# 5. MẠNG XÃ HỘI, CHAT VÀ THEO DÕI
# =============================================================================

class PostViewSet(viewsets.ModelViewSet):
    """ViewSet cho các bài đăng chia sẻ kinh nghiệm."""
    queryset = Post.objects.filter(active=True)
    serializer_class = serializers.PostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.AllowAny]
        elif self.action in ['create', 'react']: # Thêm các action mới vào đây
            self.permission_classes = [permissions.IsAuthenticated]
        else:  # update, partial_update, destroy
            self.permission_classes = [permissions.IsAuthenticated, perms.IsOwnerOrAdmin]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, active=True)

    @action(detail=True, methods=['post'], url_path='react')
    def react(self, request, pk=None):
        try:
            post = self.get_object()
        except Post.DoesNotExist:
            return Response({"error": "Bài đăng không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

        reaction_type = request.data.get('type')

        if not reaction_type:
            return Response({"error": "Vui lòng cung cấp 'type' của cảm xúc."}, status=status.HTTP_400_BAD_REQUEST)

        valid_types = [t[0] for t in Reaction.Type.choices]
        if reaction_type not in valid_types:
            return Response({"error": f"Loại cảm xúc không hợp lệ. Chỉ chấp nhận: {valid_types}"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            existing_reaction = Reaction.objects.get(user=request.user, post=post)

            if existing_reaction.type == reaction_type:
                existing_reaction.delete()
                return Response({"message": "Đã xóa cảm xúc."}, status=status.HTTP_204_NO_CONTENT)
            else:
                existing_reaction.type = reaction_type
                existing_reaction.save()
                serializer = serializers.ReactionSerializer(existing_reaction)
                return Response({"message": "Đã cập nhật cảm xúc.", "data": serializer.data}, status=status.HTTP_200_OK)

        except Reaction.DoesNotExist:
            new_reaction = Reaction.objects.create(
                user=request.user,
                post=post,
                type=reaction_type
            )
            serializer = serializers.ReactionSerializer(new_reaction)
            return Response({"message": "Đã thêm cảm xúc.", "data": serializer.data}, status=status.HTTP_201_CREATED)

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = serializers.CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [permissions.IsAuthenticated, perms.IsOwnerOrAdmin]
        return super().get_permissions()

    def get_queryset(self):
        """
        Ghi đè để chỉ trả về các comment của một post cụ thể
        khi truy cập qua nested route.
        """
        # Lấy post_pk từ URL (ví dụ: /posts/123/comments/)
        post_pk = self.kwargs.get('post_pk')
        if post_pk:
            return self.queryset.filter(post_id=post_pk)
        return self.queryset.none()

    def perform_create(self, serializer):
        post_pk = self.kwargs.get('post_pk')
        try:
            post = Post.objects.get(pk=post_pk)
        except Post.DoesNotExist:
            raise serializers.ValidationError("Bài đăng không tồn tại.")

        serializer.save(user=self.request.user, post=post, active=True)

class ProtestViewSet(viewsets.ModelViewSet):
    """
    ViewSet dành cho Admin để quản lý và xử lý các kháng nghị.
    """
    queryset = Protest.objects.all().order_by('status', '-created_date')
    serializer_class = serializers.ProtestSerializer
    permission_classes = [perms.IsAdminOrForbidden]

    @action(detail=True, methods=['patch'], url_path='resolve')
    def resolve(self, request, pk=None):
        try:
            protest = self.get_object()
        except Protest.DoesNotExist:
            return Response({"error": "Kháng nghị không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        note = request.data.get('resolution_note')

        if not new_status or not note:
            return Response(
                {"error": "Vui lòng cung cấp cả 'status' và 'resolution_note'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_statuses = [Protest.Status.RESOLVED, Protest.Status.REJECTED]
        if new_status not in valid_statuses:
            return Response(
                {"error": f"Trạng thái không hợp lệ. Chỉ chấp nhận: {valid_statuses}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        protest.status = new_status
        protest.resolution_note = note
        protest.admin = request.user
        protest.save()

        if new_status == Protest.Status.RESOLVED:
            listing = protest.listing
            listing.active = True
            listing.save(update_fields=['active'])


        protester = protest.protester
        protest_status_display = protest.get_status_display()

        tasks.notify_user_of_protest_resolution.delay(
            user_id=protester.id,
            listing_title=protest.listing.title,
            protest_status=protest.get_status_display(),
            resolution_note=note
        )

        sms_sent_successfully = False
        if protester.phone_number and protester.is_phone_verified:
            try:
                sms_message = (
                    f"[Landify] Kháng nghị của bạn cho tin {protest.listing.title} đã được xử lý. "
                    f"Kết quả qua: {protest_status_display}. Vui lòng kiểm tra ứng dụng để xem chi tiết."
                )

                sms_response = utils.send_sms(protester.phone_number, sms_message)

                if "error" not in sms_response:
                    sms_sent_successfully = True
                    print(f"Đã gửi SMS thành công đến {protester.phone_number}")
                else:
                    print(f"Lỗi khi gửi SMS đến {protester.phone_number}: {sms_response['error']}")

            except Exception as e:
                print(f"Lỗi không xác định khi cố gắng gửi SMS: {e}")

        serializer = self.get_serializer(protest)
        response_data = serializer.data
        response_data['sms_sent'] = sms_sent_successfully # Thêm key mới vào response
        return Response(response_data, status=status.HTTP_200_OK)

# --- Chat riêng giữa bên bán và bên mua ---
# LƯU Ý QUAN TRỌNG: Chat real-time không nên được xây dựng trên HTTP request/response thông thường.
# Giải pháp tốt nhất là sử dụng WebSockets. Thư viện Django Channels là lựa chọn tiêu chuẩn cho việc này.
# Dưới đây là một API skeleton để lấy lịch sử và gửi tin nhắn, nhưng nó sẽ không real-time.

# =============================================================================
# 6. HỆ THỐNG GỢI Ý VÀ PHÁT HIỆN SPAM
# =============================================================================

# Phát hiện spam/scam và đẩy bài viết tiềm năng không phải là một API endpoint,
# mà là một hệ thống chạy ngầm.
#
# HƯỚNG TRIỂN KHAI:
#
# 1.  **Phát hiện Spam/Scam:**
#     -   Sử dụng **Django Signals**: Tạo một signal `post_save` cho model `Listing` và `Comment`.
#     -   Khi một đối tượng mới được tạo, signal sẽ được kích hoạt.
#     -   Trong hàm xử lý signal, gửi nội dung (`title`, `content`) đến một **hàng đợi tác vụ (Task Queue)** như **Celery**.
#     -   Worker của Celery sẽ chạy một tác vụ nền để:
#         -   Phân tích văn bản, tìm các từ khóa bị cấm (spam, lừa đảo).
#         -   Kiểm tra tần suất đăng bài của người dùng.
#         -   Sử dụng một mô hình AI/ML đơn giản để phân loại văn bản.
#         -   Nếu phát hiện vi phạm, tự động gắn cờ bài viết hoặc thông báo cho admin.
#
# 2.  **Đẩy bài viết tiềm năng (Recommendation System):**
#     -   Đây là một hệ thống gợi ý (Collaborative Filtering hoặc Content-Based Filtering).
#     -   **Content-Based**: Gợi ý các BĐS tương tự với những gì người dùng đã xem/thích.
#         -   Phân tích các thuộc tính: `property_type`, `location`, `price`, `area`.
#         -   Tìm các BĐS có thuộc tính giống nhất.
#     -   **Collaborative Filtering**: "Những người dùng giống bạn cũng thích những BĐS này".
#         -   Phân tích ma trận tương tác (user-item matrix) từ `Wishlist`, `Review`, `Appointment`.
#         -   Tìm những người dùng có hành vi tương tự và gợi ý các BĐS mà họ đã thích.
#     -   Hệ thống này thường được chạy định kỳ (ví dụ: mỗi đêm) bằng Celery để tính toán và lưu lại các gợi ý cho từng người dùng.

def index(request):
    return HttpResponse('Hello, World!')