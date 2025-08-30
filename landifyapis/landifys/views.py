# =================== Import ==========================
# Django Core
import agora_token_builder.RtcTokenBuilder
from django.http import HttpResponse, JsonResponse

# Libraries
import cloudinary

# REST Framework
from rest_framework import viewsets, generics, status, parsers, permissions, authentication, exceptions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

# Modules
from landifys import serializers  # Giả sử serializers đã được viết lại với serializers.Serializer

from django.conf import settings
from django.core.cache import cache

# Firebase Admin SDK
from firebase_admin import firestore
from .utils import db

# Etc
from . import utils
from . import tasks
from .func import fengshui
from . import perms
import requests
from datetime import datetime, time
import time
from django.core.signing import Signer, BadSignature, SignatureExpired
from geographiclib import geodesic

# Khởi tạo client Firestore để sử dụng trong toàn bộ file
# Việc khởi tạo app nên được thực hiện một lần duy nhất khi ứng dụng khởi động (ví dụ trong utils.py)
db = firestore.client()
from agora_token_builder import RtcTokenBuilder
from pymongo import MongoClient

# =============================================================================
# LƯU Ý VỀ AUTHENTICATION:
# Lớp FirebaseAuthentication cần được sửa đổi để không tương tác với User.objects
# mà chỉ xác thực token và gắn payload vào request.
# Ví dụ: request.firebase_user = decoded_token
# =============================================================================
from .authentication import FirebaseAuthentication  # Giả định lớp này đã được sửa


class UserViewSet(viewsets.ViewSet):
    # queryset và serializer_class không còn cần thiết ở cấp ViewSet nữa
    parser_classes = [parsers.MultiPartParser]
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    # --- Basic ---
    # Việc kiểm tra quyền giờ sẽ được thực hiện thủ công bên trong mỗi action
    # vì không còn `get_object()` của DRF để tự động kiểm tra.

    # User creation trong Firebase thường được xử lý ở client.
    # Endpoint này giờ đây có thể dùng để tạo một "profile" trong Firestore
    # sau khi user đã được tạo trong Firebase Authentication.
    def create(self, request, *args, **kwargs):
        # Lấy thông tin từ Firebase ID token
        uid = request.firebase_user.get('uid')
        phone_number = request.firebase_user.get('phone_number')

        if not uid:
            return Response({"error": "Token không hợp lệ, không có UID."}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = serializers.UserSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_ref = db.collection('users').document(uid)
        if user_ref.get().exists:
            return Response({"error": "User profile đã tồn tại."}, status=status.HTTP_409_CONFLICT)

        user_data = serializer.validated_data
        user_data['phone_number'] = phone_number
        user_data['is_phone_verified'] = True
        user_data['is_id_card_verified'] = False
        user_data['is_identity_verified'] = False
        user_data['id_card_scan_status'] = 'not_started'
        user_data['role'] = 'user'
        user_data['is_active'] = True
        user_data['created_at'] = firestore.SERVER_TIMESTAMP

        try:
            user_ref.set(user_data)

            return Response({
                "message": "Tạo hồ sơ người dùng thành công.",
                "user": user_data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": f"Lỗi khi tạo hồ sơ: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['get'], url_path='current_user', detail=False)
    def current_user(self, request):
        uid = request.firebase_user.get('uid')
        try:
            user_doc = db.collection('users').document(uid).get()
            if user_doc.exists:
                return Response(user_doc.to_dict())
            else:
                return Response({"error": "Không tìm thấy người dùng."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # --- Admin ---
    # Cần một cơ chế để xác định vai trò admin, ví dụ: custom claims trong Firebase token
    # hoặc một trường 'role' trong document user
    @action(methods=['patch'], url_path='disable', detail=True)
    def disable_account(self, request, pk=None):
        # Giả sử pk ở đây là UID của user cần disable
        admin_uid = request.firebase_user.get('uid')
        admin_doc = db.collection('users').document(admin_uid).get()
        if not admin_doc.exists or admin_doc.to_dict().get('role') != 'admin':
            return Response({"error": "Không có quyền truy cập."}, status=status.HTTP_403_FORBIDDEN)

        if pk == admin_uid:
            return Response({"error": "Admin không thể tự vô hiệu hóa tài khoản."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_ref = db.collection('users').document(pk)
            user_doc = user_ref.get()
            if not user_doc.exists:
                return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

            current_status = user_doc.to_dict().get('is_active', True)
            new_status = not current_status
            user_ref.update({'is_active': new_status})

            status_text = "enabled" if new_status else "disabled"
            message = f"User {pk} has been {status_text}."
            return Response({"message": message}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['patch'], url_path='complete-profile', detail=False)
    def complete_profile(self, request):
        uid = request.firebase_user.get('uid')

        # Validate dữ liệu đầu vào
        serializer = serializers.UserSerializer(data=request.data,
                                                       partial=True)  # Tạo serializer riêng cho profile
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        clean_data_for_firestore = utils.convert_data_for_firestore(validated_data)

        try:
            user_ref = db.collection('users').document(uid)
            user_ref.update(clean_data_for_firestore)
            updated_doc = user_ref.get()
            return Response(updated_doc.to_dict(), status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # --- User ---
    @action(methods=['post'], url_path='follow', detail=True)
    def toggle_follow(self, request, pk=None):
        # pk là uid của user cần follow/unfollow
        follower_uid = request.firebase_user.get('uid')

        if pk == follower_uid:
            return Response({"error": "Bạn không thể tự theo dõi chính mình."}, status=status.HTTP_400_BAD_REQUEST)

        # Sử dụng transaction của Firestore để đảm bảo tính nhất quán
        transaction = db.transaction()
        follower_ref = db.collection('users').document(follower_uid).collection('following').document(pk)
        following_ref = db.collection('users').document(pk).collection('followers').document(follower_uid)

        try:
            @firestore.transactional
            def update_in_transaction(transaction, follower_ref, following_ref):
                snapshot = follower_ref.get(transaction=transaction)
                if snapshot.exists:
                    # Nếu đã follow -> Unfollow
                    transaction.delete(follower_ref)
                    transaction.delete(following_ref)
                    return "unfollowed"
                else:
                    # Nếu chưa follow -> Follow
                    # Có thể lưu thêm thông tin nếu cần, ví dụ: timestamp
                    transaction.set(follower_ref, {'followed_at': firestore.SERVER_TIMESTAMP})
                    transaction.set(following_ref, {'follower_since': firestore.SERVER_TIMESTAMP})
                    return "followed"

            result = update_in_transaction(transaction, follower_ref, following_ref)
            message = f"Successfully {result} user {pk}."
            return Response({"status": result, "message": message}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Lỗi transaction: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['patch'], url_path='change_avatar', detail=False)
    def change_avatar(self, request):
        uid = request.firebase_user.get('uid')
        avatar_file = request.FILES.get('avatar')

        if not avatar_file:
            return Response({'message': 'Avatar file is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Upload lên Cloudinary
            upload_result = cloudinary.uploader.upload(avatar_file)
            avatar_url = upload_result.get('secure_url')

            if not avatar_url:
                return Response({'message': 'Upload thất bại.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Cập nhật URL vào document user trong Firestore
            db.collection('users').document(uid).update({'avatar': avatar_url})

            return Response({
                'message': 'Avatar updated successfully.',
                'avatar': avatar_url
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'message': 'Avatar upload failed', 'error': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['patch'], url_path='change_password', detail=False)
    def change_password(self, request):
        # LƯU Ý: Thay đổi mật khẩu nên được thực hiện qua Firebase Auth SDK ở client.
        # Backend không nên xử lý mật khẩu trực tiếp.
        # Endpoint này có thể dùng để đánh dấu là user cần đổi mật khẩu.
        uid = request.firebase_user.get('uid')
        password = request.data.get('password')  # Vẫn nhận nhưng không xử lý

        if not password:
            return Response({'message': 'Password is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Ghi nhận hành động, nhưng không đổi password
            user_ref = db.collection('users').document(uid)
            user_ref.update({
                'change_password_required': False,
                'password_last_updated': firestore.SERVER_TIMESTAMP
            })

            # Gửi SMS thông báo
            # (Giữ nguyên logic Twilio của bạn)

            return Response({'message': 'Yêu cầu đổi mật khẩu đã được ghi nhận. Vui lòng thực hiện trên client.'},
                            status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'message': 'An error occurred.', 'error': str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# 1. ĐĂNG TIN, LỌC VÀ TÌM KIẾM NHÀ ĐẤT
# =============================================================================

class ListingViewSet(viewsets.ViewSet):
    authentication_classes = [FirebaseAuthentication]  # Cần xác thực cho hầu hết các action

    # Thay thế cho get_queryset
    def list(self, request):
        PAGE_SIZE = 10  # Định nghĩa kích thước trang

        try:
            # Bắt đầu xây dựng query
            query = db.collection('listings').where('active', '==', True).order_by('created_at',
                                                                                   direction=firestore.Query.DESCENDING)

            # Lấy con trỏ (cursor) từ query params của client
            last_doc_id = request.query_params.get('last_doc_id')

            if last_doc_id:
                # Nếu client gửi lên ID của document cuối cùng của trang trước...
                last_doc_snapshot = db.collection('listings').document(last_doc_id).get()
                if last_doc_snapshot.exists:
                    # ...thì bắt đầu query từ sau document đó.
                    query = query.start_after(last_doc_snapshot)

            # Giới hạn số lượng kết quả trả về
            docs = query.limit(PAGE_SIZE).stream()

            results = []
            last_visible_id = None
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                results.append(data)
                last_visible_id = doc.id  # Lưu lại ID của doc cuối cùng trong trang này

            # Trả về response có chứa cả dữ liệu và con trỏ cho trang tiếp theo
            response_data = {
                'results': results,
                'next_page_cursor': last_visible_id  # Client sẽ dùng ID này để yêu cầu trang kế
            }

            return Response(response_data)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        try:
            doc = db.collection('listings').document(pk).get()
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return Response(data)
            else:
                return Response({"error": "Tin đăng không tồn tại."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        uid = request.firebase_user.get('uid')
        user_doc = db.collection('users').document(uid).get()
        if not user_doc.exists or not user_doc.to_dict().get('is_id_card_verified'):
            return Response({"error": "Cần xác thực danh tính để đăng tin."}, status=status.HTTP_403_FORBIDDEN)

        serializer = serializers.ListingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        listing_data = serializer.validated_data
        listing_data['user_id'] = uid
        listing_data['active'] = True
        listing_data['created_at'] = firestore.SERVER_TIMESTAMP
        listing_data['status'] = 'AVAILABLE'

        try:
            # add() tự tạo ID
            update_time, new_ref = db.collection('listings').add(listing_data)
            listing_data['id'] = new_ref.id
            return Response(listing_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, pk=None):
        uid = request.firebase_user.get('uid')

        try:
            listing_ref = db.collection('listings').document(pk)
            doc = listing_ref.get()
            if not doc.exists:
                return Response({"error": "Tin đăng không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

            # Kiểm tra quyền sở hữu
            if doc.to_dict().get('user_id') != uid:
                return Response({"error": "Không có quyền chỉnh sửa tin này."}, status=status.HTTP_403_FORBIDDEN)

            # Validate dữ liệu cập nhật
            serializer = serializers.ListingSerializer(data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            listing_ref.update(serializer.validated_data)
            return Response(serializer.validated_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        params = request.query_params

        # --- LƯU Ý QUAN TRỌNG VỀ TÌM KIẾM TRONG FIRESTORE ---
        # 1. Firestore KHÔNG hỗ trợ tìm kiếm text (LIKE, __icontains).
        #    Để tìm kiếm theo 'q', bạn BẮT BUỘC phải dùng dịch vụ của bên thứ ba như Algolia, Elasticsearch.
        # 2. Firestore có thể query trên nhiều điều kiện 'where', nhưng có giới hạn.
        #    Ví dụ: Bạn không thể query range (>, <) trên nhiều hơn một trường.

        # Đoạn code dưới đây chỉ minh họa cách query trên các trường có giá trị chính xác
        # và một trường range duy nhất (price).
        try:
            query_ref = db.collection('listings')

            # Lọc theo các trường có giá trị bằng
            property_type = params.get('property_type')
            if property_type:
                query_ref = query_ref.where('property.property_type_name', '==', property_type)

            min_bedrooms = params.get('min_bedrooms')
            if min_bedrooms:
                # Firestore không có '>=', nhưng có thể kết hợp
                query_ref = query_ref.where('property.bedroom_count', '>=', int(min_bedrooms))

            # Lọc theo giá (chỉ có thể có một trường range)
            min_price = params.get('min_price')
            if min_price:
                query_ref = query_ref.where('price', '>=', float(min_price))

            max_price = params.get('max_price')
            if max_price:
                query_ref = query_ref.where('price', '<=', float(max_price))

            # Để tìm kiếm theo 'q', bạn sẽ gọi API của Algolia ở đây
            # query_text = params.get('q', '')
            # if query_text:
            #    algolia_results = search_in_algolia(query_text)
            #    listing_ids = [res['objectID'] for res in algolia_results]
            #    ... fetch listings from firestore using these IDs ...

            docs = query_ref.stream()
            results = [doc.to_dict() for doc in docs]
            return Response(results, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Query error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ... Các action khác như protest, apply_broker sẽ được viết lại tương tự,
    # tạo document trong collection tương ứng (`protests`, `broker_applications`...)
    # và luôn kiểm tra quyền hạn trước khi thực hiện.

    @action(detail=True, methods=['post'], url_path='protest', permission_classes=[permissions.IsAuthenticated])
    def protest(self, request, pk=None):
        uid = request.firebase_user.get('uid')

        try:
            listing_doc = db.collection('listings').document(pk).get()
            if not listing_doc.exists:
                return Response({"error": "Tin đăng không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

            listing_data = listing_doc.to_dict()

            if listing_data.get('user_id') != uid:
                return Response({"error": "Bạn không có quyền kháng nghị cho tin đăng này."},
                                status=status.HTTP_403_FORBIDDEN)

            if listing_data.get('active', False):
                return Response({"error": "Bạn chỉ có thể kháng nghị các tin đăng đã bị từ chối."},
                                status=status.HTTP_400_BAD_REQUEST)

            # Kiểm tra xem có kháng nghị nào đang chờ không
            protests_query = db.collection('protests').where('listing_id', '==', pk).where('status', '==',
                                                                                           'IN_PROGRESS').limit(1)
            if len(list(protests_query.stream())) > 0:
                return Response({"error": "Tin đăng này đang chờ xử lý."}, status=status.HTTP_400_BAD_REQUEST)

            serializer = serializers.ProtestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            protest_data = serializer.validated_data
            protest_data['listing_id'] = pk
            protest_data['protester_id'] = uid
            protest_data['status'] = 'IN_PROGRESS'
            protest_data['created_at'] = firestore.SERVER_TIMESTAMP

            _, new_ref = db.collection('protests').add(protest_data)

            # Gọi Celery task
            tasks.notify_admins_of_new_protest.delay(
                protest_id=new_ref.id,
                protester_username=request.firebase_user.get('name', uid),  # Giả sử có 'name'
                listing_title=listing_data.get('title')
            )

            return Response(protest_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =============================================================================
# ... CÁC VIEWSET KHÁC ...
# Do giới hạn độ dài, tôi sẽ tóm tắt logic cho các ViewSet còn lại.
# Nguyên tắc chung là giống hệt như trên:
# 1. Bỏ `ModelViewSet` và các thuộc tính liên quan (queryset, serializer_class).
# 2. Viết lại các phương thức `list`, `retrieve`, `create`, `update`, `destroy`.
# 3. Sử dụng `db.collection('...').document('...')` để tham chiếu.
# 4. Dùng `.get()`, `.add()`, `.set()`, `.update()`, `.delete()` để thao tác.
# 5. Luôn kiểm tra quyền (ownership, role) một cách thủ công.
# 6. Dùng `serializers.Serializer` để validate `request.data`.
# 7. Đối với tài nguyên lồng nhau (nested), dùng subcollection.
#    Ví dụ: `db.collection('posts').document(post_id).collection('comments').add(...)`
# =============================================================================


class ReportViewSet(viewsets.ViewSet):
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [permissions.IsAuthenticated]  # Yêu cầu đăng nhập cho mọi action

    def create(self, request):
        """Tạo một báo cáo mới."""
        uid = request.firebase_user.get('uid')

        serializer = serializers.ReportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        report_data = serializer.validated_data
        report_data['reporter_id'] = uid
        report_data['status'] = 'pending'  # Trạng thái ban đầu
        report_data['created_at'] = firestore.SERVER_TIMESTAMP

        try:
            _, new_ref = db.collection('reports').add(report_data)
            report_data['id'] = new_ref.id
            return Response(report_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": f"Lỗi khi tạo báo cáo: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request):
        """
        Lấy danh sách báo cáo. Admin thấy hết, user chỉ thấy report của mình.
        """
        uid = request.firebase_user.get('uid')

        try:
            # Kiểm tra vai trò admin
            is_admin = perms._is_admin(request)  # Dùng hàm helper từ perms.py

            query = db.collection('reports').order_by('created_at', direction=firestore.Query.DESCENDING)

            if not is_admin:
                # Nếu không phải admin, chỉ lấy các report do chính user đó tạo
                query = query.where('reporter_id', '==', uid)

            # Triển khai phân trang cơ bản
            docs = query.limit(20).stream()
            results = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                results.append(data)

            return Response(results)
        except Exception as e:
            return Response({"error": f"Lỗi khi lấy danh sách báo cáo: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Các phương thức retrieve, update, destroy sẽ cần kiểm tra quyền admin
    # Ví dụ:
    def partial_update(self, request, pk=None):
        """Admin cập nhật trạng thái của một báo cáo."""
        if not perms._is_admin(request):
            return Response({"error": "Không có quyền truy cập."}, status=status.HTTP_403_FORBIDDEN)

        new_status = request.data.get('status')
        if not new_status:
            return Response({"error": "Vui lòng cung cấp 'status'."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            report_ref = db.collection('reports').document(pk)
            report_ref.update({'status': new_status})
            return Response({"message": "Cập nhật trạng thái thành công."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProtestViewSet(viewsets.ViewSet):
    """
    ViewSet dành cho Admin để quản lý và xử lý các kháng nghị.
    """
    authentication_classes = [FirebaseAuthentication]
    # Yêu cầu quyền admin cho tất cả các hành động trong ViewSet này
    permission_classes = [perms.IsAdminOrForbidden]

    def list(self, request):
        """Lấy danh sách các kháng nghị."""
        try:
            # Lọc theo trạng thái và sắp xếp theo ngày tạo
            query = db.collection('protests').order_by('status').order_by('created_at',
                                                                          direction=firestore.Query.DESCENDING)

            # Phân trang cơ bản
            docs = query.limit(20).stream()
            results = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                # TODO: Cần "join" thêm thông tin về listing và protester nếu cần hiển thị chi tiết
                results.append(data)

            return Response(results)
        except Exception as e:
            return Response({"error": f"Lỗi khi lấy danh sách kháng nghị: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        """Lấy chi tiết một kháng nghị."""
        try:
            doc = db.collection('protests').document(pk).get()
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return Response(data)
            else:
                return Response({"error": "Kháng nghị không tồn tại."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['patch'], url_path='resolve')
    def resolve(self, request, pk=None):
        """
        Admin xử lý một kháng nghị (chấp thuận hoặc từ chối).
        """
        admin_uid = request.firebase_user.get('uid')

        new_status = request.data.get('status')
        note = request.data.get('resolution_note')

        if not new_status or not note:
            return Response({"error": "Vui lòng cung cấp 'status' và 'resolution_note'."},
                            status=status.HTTP_400_BAD_REQUEST)

        valid_statuses = ['RESOLVED', 'REJECTED']  # Trạng thái hợp lệ khi xử lý xong
        if new_status not in valid_statuses:
            return Response({"error": f"Trạng thái không hợp lệ. Chỉ chấp nhận: {valid_statuses}"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            protest_ref = db.collection('protests').document(pk)
            protest_doc = protest_ref.get()
            if not protest_doc.exists:
                return Response({"error": "Kháng nghị không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

            protest_data = protest_doc.to_dict()

            # Cập nhật thông tin kháng nghị
            protest_ref.update({
                'status': new_status,
                'resolution_note': note,
                'admin_id': admin_uid,  # Lưu lại admin đã xử lý
                'resolved_at': firestore.SERVER_TIMESTAMP
            })

            # Nếu kháng nghị được chấp thuận, kích hoạt lại tin đăng
            if new_status == 'RESOLVED':
                listing_id = protest_data.get('listing_id')
                if listing_id:
                    listing_ref = db.collection('listings').document(listing_id)
                    listing_ref.update({'active': True})

            # Gửi thông báo cho người dùng
            protester_id = protest_data.get('protester_id')
            listing_title = protest_data.get('listing_title', 'Không rõ')  # Giả sử có lưu title
            if protester_id:
                tasks.notify_user_of_protest_resolution.delay(
                    user_id=protester_id,
                    listing_title=listing_title,
                    protest_status=new_status,
                    resolution_note=note
                )

            return Response({"message": "Xử lý kháng nghị thành công."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AppointmentViewSet(viewsets.ViewSet):
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [perms.IsFirebaseAuthenticated]

    def create(self, request):
        """Tạo một lịch hẹn mới."""
        uid = request.firebase_user.get('uid')

        # Kiểm tra quyền: Yêu cầu user phải xác minh danh tính
        permission = perms.IsIdentityVerified()
        if not permission.has_permission(request, self):
            return Response({"error": permission.message}, status=status.HTTP_403_FORBIDDEN)

        serializer = serializers.AppointmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        appointment_data = serializer.validated_data
        appointment_data['user_id'] = uid
        appointment_data['status'] = 'pending'
        appointment_data['created_at'] = firestore.SERVER_TIMESTAMP

        try:
            _, new_ref = db.collection('appointments').add(appointment_data)
            appointment_data['id'] = new_ref.id
            return Response(appointment_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": f"Lỗi khi tạo lịch hẹn: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request):
        """
        Lấy danh sách lịch hẹn của người dùng hiện tại.
        (Giả định admin có thể xem qua một giao diện khác).
        """
        uid = request.firebase_user.get('uid')
        try:
            query = db.collection('appointments').where('user_id', '==', uid).order_by('appointment_date',
                                                                                       direction=firestore.Query.DESCENDING)
            docs = query.limit(20).stream()
            results = [doc.to_dict() for doc in docs]
            return Response(results)
        except Exception as e:
            return Response({"error": f"Lỗi khi lấy danh sách lịch hẹn: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WishlistViewSet(viewsets.ViewSet):
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        """Thêm một tin đăng vào danh sách yêu thích."""
        uid = request.firebase_user.get('uid')

        serializer = serializers.WishlistSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        listing_id = serializer.validated_data['listing_id']

        try:
            # Kiểm tra xem đã tồn tại chưa để tránh trùng lặp
            query = db.collection('wishlists').where('user_id', '==', uid).where('listing_id', '==', listing_id).limit(
                1)
            if list(query.stream()):
                return Response({"message": "Tin đăng đã có trong danh sách yêu thích."}, status=status.HTTP_OK)

            wishlist_data = {
                'user_id': uid,
                'listing_id': listing_id,
                'added_at': firestore.SERVER_TIMESTAMP
            }
            db.collection('wishlists').add(wishlist_data)
            return Response(wishlist_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": f"Lỗi khi thêm vào wishlist: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request):
        """Lấy danh sách yêu thích của người dùng."""
        uid = request.firebase_user.get('uid')
        try:
            query = db.collection('wishlists').where('user_id', '==', uid).order_by('added_at',
                                                                                    direction=firestore.Query.DESCENDING)
            docs = query.limit(20).stream()
            # TODO: Cần thêm một bước nữa để lấy thông tin chi tiết của listing từ listing_id
            # Đây là một ví dụ về việc cần "join" dữ liệu ở phía client hoặc server.
            results = [doc.to_dict() for doc in docs]
            return Response(results)
        except Exception as e:
            return Response({"error": f"Lỗi khi lấy wishlist: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk=None):
        """Xóa một tin đăng khỏi danh sách yêu thích."""
        # pk ở đây là ID của document trong collection 'wishlists'
        uid = request.firebase_user.get('uid')
        try:
            wishlist_ref = db.collection('wishlists').document(pk)
            doc = wishlist_ref.get()
            if not doc.exists:
                return Response(status=status.HTTP_404_NOT_FOUND)

            # Kiểm tra quyền sở hữu
            if doc.to_dict().get('user_id') != uid:
                return Response({"error": "Không có quyền xóa mục này."}, status=status.HTTP_403_FORBIDDEN)

            wishlist_ref.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AuthVerificationView(viewsets.ViewSet):
    """
    ViewSet xử lý các quy trình xác thực không yêu cầu session,
    bao gồm kiểm tra SĐT, OTP, và quy trình eKYC.
    """
    # Hầu hết các endpoint ở đây cho phép mọi người truy cập
    # trừ các bước eKYC yêu cầu token đã đăng nhập.
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):
        """
        Ghi đè quyền cho các action eKYC, yêu cầu người dùng phải được xác thực.
        """
        if self.action in ['verify_id_card', 'verify_liveness']:
            # Sử dụng FirebaseAuthentication để xác thực token
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    @action(methods=['post'], url_path='check-phone', detail=False)
    def check_phone_status(self, request):
        phone_number = request.data.get('phone_number')
        if not phone_number:
            return Response({"error": "Vui lòng cung cấp số điện thoại."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # THAY THẾ ORM: Query Firestore để tìm user bằng SĐT
            # Lưu ý: Cần tạo một index trên trường 'phone_number' trong Firestore Console.
            users_ref = db.collection('users')
            query = users_ref.where('phone_number', '==', phone_number).limit(1)
            results = list(query.stream())

            if results:
                # Tìm thấy user
                user_data = results[0].to_dict()
                return Response({
                    "status": "registered",
                    "is_active": user_data.get('is_active', False)  # Mặc định là False nếu không có trường
                })
            else:
                # Không tìm thấy user
                return Response({"status": "not_registered"})
        except Exception as e:
            return Response({"error": f"Lỗi hệ thống: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['post'], url_path='request-otp', detail=False)
    def request_otp(self, request):
        phone_number = request.data.get('phone_number')
        if not phone_number:
            return Response({"error": "Vui lòng cung cấp số điện thoại."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # THAY THẾ ORM: Kiểm tra SĐT đã tồn tại hay chưa
            users_ref = db.collection('users')
            query = users_ref.where('phone_number', '==', phone_number).limit(1)
            if list(query.stream()):
                return Response({"error": "Số điện thoại này đã được đăng ký."}, status=status.HTTP_400_BAD_REQUEST)

            # LOGIC KHÔNG ĐỔI: Giữ nguyên logic tạo OTP, cache và gửi SMS
            otp_code = utils.generate_otp()
            utils.save_otp_to_cache(phone_number, otp_code)  # Dùng SĐT làm key cache
            message_body = f"[Landify] Mã xác thực của bạn là: {otp_code}. Mã có hiệu lực trong 5 phút."
            sms_response = utils.send_sms(phone_number, message_body)

            if "error" in sms_response:
                return Response({"error": "Không thể gửi mã OTP."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({"message": f"Đã gửi mã OTP đến số {phone_number}."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Lỗi hệ thống: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['post'], url_path='verify-otp', detail=False)
    def verify_otp(self, request):
        phone_number = request.data.get('phone_number')
        otp_code = request.data.get('otp')

        if not phone_number or not otp_code:
            return Response({"error": "Vui lòng cung cấp SĐT và mã OTP."}, status=status.HTTP_400_BAD_REQUEST)

        # LOGIC KHÔNG ĐỔI: Logic xác thực OTP từ cache và tạo token đăng ký giữ nguyên
        is_valid = utils.verify_otp_from_cache(phone_number, otp_code)

        if is_valid:
            # Tạo một token tạm thời có chữ ký số, chứng minh SĐT đã được xác thực.
            # Token này sẽ được sử dụng ở bước tạo user để đảm bảo an toàn.
            signer = Signer()
            data_to_sign = f"{phone_number}:{int(time.time())}"
            registration_token = signer.sign(data_to_sign)

            return Response({
                "message": "Xác thực OTP thành công.",
                "registration_token": registration_token
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Mã OTP không hợp lệ hoặc đã hết hạn."}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], url_path='verify-id-card', detail=False)
    def verify_id_card(self, request):
        """
        Bước 1 của eKYC: Nhận diện và trích xuất thông tin từ CCCD.
        Yêu cầu người dùng phải đăng nhập (đã có token).
        """
        # Lấy UID từ token đã được xác thực
        uid = request.firebase_user.get('uid')
        if not uid:
            return Response({"error": "Yêu cầu không hợp lệ, thiếu thông tin xác thực."},
                            status=status.HTTP_401_UNAUTHORIZED)

        try:
            id_card_image = request.FILES.get('id_card_image')
            if not id_card_image:
                return Response({"error": "Vui lòng cung cấp ảnh CCCD."}, status=status.HTTP_400_BAD_REQUEST)

            # LOGIC KHÔNG ĐỔI: Gọi API của FPT
            idr_response = utils.call_fpt_idr_api(id_card_image)
            if idr_response.get('errorCode') != 0:
                return Response({"error": "Không thể đọc thông tin từ ảnh CCCD."}, status=status.HTTP_400_BAD_REQUEST)

            extracted_data = idr_response.get('data')[0]

            full_name = extracted_data.get('name', '').strip()
            first_name = ''
            last_name = ''

            if ' ' in full_name:
                parts = full_name.split(' ')
                first_name = parts[0]  # "Nguyễn"
                last_name = ' '.join(parts[1:])  # "Anh Khoa"
            else:
                # Trường hợp tên chỉ có một từ
                last_name = full_name

            dob_str = extracted_data.get('dob')
            date_of_birth = None
            if dob_str:
                try:
                    date_of_birth = datetime.strptime(dob_str, '%d/%m/%Y').strftime('%Y-%m-%d')
                except ValueError:
                    pass

            update_data = {
                'first_name': first_name,
                'last_name': last_name,
                'date_of_birth': date_of_birth,
                'address': extracted_data.get('address'),
            }

            update_data = {k: v for k, v in update_data.items() if v is not None}
            update_data['is_id_card_verified'] = True

            user_ref = db.collection('users').document(uid)
            user_ref.update(update_data)

            # LOGIC KHÔNG ĐỔI: Lưu ảnh gốc vào cache để dùng cho bước 2 (liveness)
            id_card_image.seek(0)
            full_image_data = id_card_image.read()
            cache_key = f'ekyc_image_{uid}'
            cache.set(cache_key, full_image_data, timeout=6000)  # 10 phút

            return Response({
                "message": "Đọc thông tin CCCD và cập nhật hồ sơ thành công.",
                "data": extracted_data
            }, status=status.HTTP_200_OK)

        except requests.exceptions.RequestException as e:
            return Response({"error": "Không thể kết nối đến dịch vụ xác minh."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            return Response({"error": f"Đã có lỗi xảy ra trong quá trình xử lý CCCD: {str(e)}."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['post'], url_path='verify-liveness', detail=False)
    def verify_liveness(self, request):
        """
        Bước 2 của eKYC: Xác thực người thật và so khớp khuôn mặt.
        """
        uid = request.firebase_user.get('uid')
        if not uid:
            return Response({"error": "Yêu cầu không hợp lệ, thiếu thông tin xác thực."},
                            status=status.HTTP_401_UNAUTHORIZED)

        try:
            video_file = request.FILES.get('video')
            if not video_file:
                return Response({"error": "Vui lòng cung cấp video xác thực."}, status=status.HTTP_400_BAD_REQUEST)

            # LOGIC KHÔNG ĐỔI: Lấy ảnh CCCD gốc từ cache
            cache_key = f'ekyc_image_{uid}'
            id_card_image_data = cache.get(cache_key)
            if not id_card_image_data:
                return Response({"error": "Phiên xác thực đã hết hạn. Vui lòng bắt đầu lại."},
                                status=status.HTTP_400_BAD_REQUEST)

            # LOGIC KHÔNG ĐỔI: Gọi API Liveness của FPT
            liveness_response = utils.call_fpt_liveness_api(video_file, id_card_image_data)

            is_live = liveness_response.get('liveness', {}).get('is_live') == 'true'
            is_match = liveness_response.get('face_match', {}).get('isMatch') == 'true'

            if is_live and is_match:
                # THAY THẾ ORM: Cập nhật trạng thái xác minh và xóa dữ liệu tạm
                user_ref = db.collection('users').document(uid)
                user_ref.update({
                    'is_identity_verified': True,
                })
                cache.delete(cache_key)  # Dọn dẹp cache
                return Response({"message": "Xác minh danh tính hoàn tất!"}, status=status.HTTP_200_OK)
            else:
                # Xử lý lỗi
                error_messages = []
                if not is_live: error_messages.append("Không phải người thật.")
                if not is_match: error_messages.append("Khuôn mặt không khớp với CCCD.")
                return Response({"error": " ".join(error_messages)}, status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.RequestException as e:
            return Response({"error": "Không thể kết nối đến dịch vụ xác minh."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            return Response({"error": "Đã có lỗi xảy ra trong quá trình xác thực khuôn mặt."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PostViewSet(viewsets.ViewSet):
    authentication_classes = [FirebaseAuthentication]

    def get_permissions(self):
        # Cho phép đọc bài post mà không cần đăng nhập
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.AllowAny]
        else:  # Các action khác yêu cầu đăng nhập
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    def list(self, request):
        """Lấy danh sách các bài post."""
        try:
            # Phân trang bằng con trỏ
            PAGE_SIZE = 10
            query = db.collection('posts').where('active', '==', True).order_by('created_at',
                                                                                direction=firestore.Query.DESCENDING)

            last_doc_id = request.query_params.get('cursor')
            if last_doc_id:
                last_doc = db.collection('posts').document(last_doc_id).get()
                if last_doc.exists:
                    query = query.start_after(last_doc)

            docs = query.limit(PAGE_SIZE).stream()
            results = []
            cursor = None
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                # LƯU Ý: Không lấy reactions/comments ở đây để tối ưu hiệu năng.
                # Client sẽ gọi API riêng để lấy chúng.
                results.append(data)
                cursor = doc.id

            return Response({'results': results, 'cursor': cursor})
        except Exception as e:
            return Response({"error": f"Lỗi khi lấy danh sách bài đăng: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """Tạo một bài post mới."""
        uid = request.firebase_user.get('uid')
        serializer = serializers.PostSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        post_data = serializer.validated_data
        post_data['user_id'] = uid
        post_data['active'] = True
        post_data['created_at'] = firestore.SERVER_TIMESTAMP
        post_data['comment_count'] = 0  # Thêm các trường count để dễ query
        post_data['reaction_count'] = 0

        try:
            _, new_ref = db.collection('posts').add(post_data)
            post_data['id'] = new_ref.id
            return Response(post_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": f"Lỗi khi tạo bài đăng: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='react')
    def react(self, request, pk=None):
        """Thêm/sửa/xóa một cảm xúc cho bài post."""
        uid = request.firebase_user.get('uid')
        serializer = serializers.ReactionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        reaction_type = serializer.validated_data['type']

        try:
            # Tham chiếu đến document reaction của user cho bài post này.
            # Dùng UID làm ID document để đảm bảo mỗi user chỉ có 1 reaction.
            reaction_ref = db.collection('posts').document(pk).collection('reactions').document(uid)

            doc = reaction_ref.get()

            if doc.exists:
                # Nếu đã react
                if doc.to_dict().get('type') == reaction_type:
                    # Cùng loại -> Xóa (un-react)
                    reaction_ref.delete()
                    # TODO: Giảm reaction_count của post đi 1 (dùng transaction hoặc cloud function)
                    return Response({"message": "Đã xóa cảm xúc."}, status=status.HTTP_204_NO_CONTENT)
                else:
                    # Khác loại -> Cập nhật
                    reaction_ref.update({'type': reaction_type})
                    return Response({"message": "Đã cập nhật cảm xúc."}, status=status.HTTP_200_OK)
            else:
                # Chưa react -> Tạo mới
                reaction_ref.set({'type': reaction_type, 'user_id': uid})
                # TODO: Tăng reaction_count của post lên 1 (dùng transaction hoặc cloud function)
                return Response({"message": "Đã thêm cảm xúc."}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CommentViewSet(viewsets.ViewSet):
    # Đây là một nested resource, nên URL sẽ là /posts/{post_pk}/comments/
    # ViewSet cần nhận `post_pk` từ URL.

    def list(self, request, post_pk=None):
        # Query comments từ subcollection
        comments_ref = db.collection('posts').document(post_pk).collection('comments')
        docs = comments_ref.order_by('created_at').stream()
        results = [doc.to_dict() for doc in docs]
        return Response(results)

    def create(self, request, post_pk=None):
        uid = request.firebase_user.get('uid')
        # Validate data
        # ...
        comment_data = {
            'content': request.data.get('content'),
            'user_id': uid,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        # Thêm comment vào subcollection
        db.collection('posts').document(post_pk).collection('comments').add(comment_data)
        return Response(comment_data, status=status.HTTP_201_CREATED)


class PropertyViewSet(viewsets.ViewSet):
    authentication_classes = [FirebaseAuthentication]

    def get_permissions(self):
        """
        Thiết lập quyền hạn dựa trên hành động (action).
        """
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.AllowAny]
        elif self.action == 'create':
            self.permission_classes = [permissions.IsAuthenticated, perms.IsIdentityVerified]
        elif self.action in ['partial_update', 'destroy']:
            # Quyền sở hữu sẽ được kiểm tra thủ công bên trong action
            self.permission_classes = [permissions.IsAuthenticated]
        else:
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    def list(self, request):
        """Lấy danh sách các bất động sản."""
        try:
            # Phân trang cơ bản
            query = db.collection('properties').order_by('created_at', direction=firestore.Query.DESCENDING)
            docs = query.limit(20).stream()

            results = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                results.append(data)

            return Response(results)
        except Exception as e:
            return Response({"error": f"Lỗi khi lấy danh sách BĐS: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        """Lấy chi tiết một bất động sản."""
        try:
            doc = db.collection('properties').document(pk).get()
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return Response(data)
            else:
                return Response({"error": "Bất động sản không tồn tại."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """Tạo một bất động sản mới."""
        uid = request.firebase_user.get('uid')

        # Validate dữ liệu đầu vào
        serializer = serializers.PropertySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        property_data = serializer.validated_data

        # THAY THẾ ORM: Gán các thông tin cần thiết
        property_data['owner_id'] = uid
        property_data['created_at'] = firestore.SERVER_TIMESTAMP

        # Logic xử lý location và utilities đã được đơn giản hóa
        # vì chúng là dữ liệu lồng nhau trong serializer

        try:
            _, new_ref = db.collection('properties').add(property_data)
            property_data['id'] = new_ref.id
            return Response(property_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": f"Lỗi khi tạo BĐS: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, pk=None):
        """Cập nhật một phần thông tin bất động sản."""
        uid = request.firebase_user.get('uid')

        try:
            prop_ref = db.collection('properties').document(pk)
            doc = prop_ref.get()
            if not doc.exists:
                return Response({"error": "Bất động sản không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

            # THAY THẾ PERMS: Kiểm tra quyền sở hữu hoặc admin thủ công
            is_admin = perms._is_admin(request)
            owner_id = doc.to_dict().get('owner_id')
            if owner_id != uid and not is_admin:
                return Response({"error": "Bạn không có quyền chỉnh sửa BĐS này."}, status=status.HTTP_403_FORBIDDEN)

            # Validate dữ liệu cập nhật
            serializer = serializers.PropertySerializer(data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            prop_ref.update(serializer.validated_data)
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk=None):
        """Xóa một bất động sản."""
        uid = request.firebase_user.get('uid')

        try:
            prop_ref = db.collection('properties').document(pk)
            doc = prop_ref.get()
            if not doc.exists:
                return Response(status=status.HTTP_404_NOT_FOUND)

            # THAY THẾ PERMS: Kiểm tra quyền sở hữu hoặc admin thủ công
            is_admin = perms._is_admin(request)
            owner_id = doc.to_dict().get('owner_id')
            if owner_id != uid and not is_admin:
                return Response({"error": "Bạn không có quyền xóa BĐS này."}, status=status.HTTP_403_FORBIDDEN)

            # TODO: Cần có logic để xóa các tài nguyên liên quan (listings, media, reviews...)
            # Đây có thể là một tác vụ phức tạp, thường được xử lý bằng Cloud Functions.
            prop_ref.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MediaViewSet(viewsets.ViewSet):
    """
    ViewSet để quản lý media (ảnh, video) cho một Bất động sản cụ thể.
    Đây là một nested resource, hoạt động trên URL dạng:
    /api/properties/{property_pk}/media/
    """
    authentication_classes = [FirebaseAuthentication]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]  # Để xử lý file upload

    def _check_permission(self, request, property_pk):
        """Hàm helper để kiểm tra quyền sở hữu hoặc vai trò admin trên BĐS cha."""
        uid = request.firebase_user.get('uid')
        prop_doc = db.collection('properties').document(property_pk).get()
        if not prop_doc.exists:
            # Trả về lỗi nếu BĐS cha không tồn tại
            raise exceptions.NotFound("Bất động sản không tồn tại.")

        is_admin = perms._is_admin(request)
        owner_id = prop_doc.to_dict().get('owner_id')

        if owner_id != uid and not is_admin:
            # Trả về lỗi nếu không có quyền
            raise exceptions.PermissionDenied("Bạn không có quyền thực hiện hành động này trên BĐS này.")

        # Nếu không có lỗi, trả về True
        return True

    def list(self, request, property_pk=None):
        """Lấy danh sách media của một BĐS."""
        try:
            # Sử dụng subcollection 'media' bên trong document 'property'
            media_ref = db.collection('properties').document(property_pk).collection('media')
            docs = media_ref.order_by('uploaded_at', direction=firestore.Query.DESCENDING).stream()

            results = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                results.append(data)

            return Response(results)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, property_pk=None):
        """Upload một file media mới cho BĐS."""
        try:
            # 1. Kiểm tra quyền hạn trước khi làm bất cứ điều gì
            self._check_permission(request, property_pk)

            # 2. Lấy file từ request
            media_file = request.FILES.get('media_file')
            if not media_file:
                return Response({"error": "Vui lòng cung cấp file phương tiện (media_file)."},
                                status=status.HTTP_400_BAD_REQUEST)

            # 3. Upload file lên Cloudinary (logic không đổi)
            uploaded_media = cloudinary.uploader.upload(
                media_file,
                resource_type="auto"  # Tự động nhận diện ảnh/video
            )
            media_url = uploaded_media.get('secure_url')
            if not media_url:
                raise Exception("Upload file lên Cloudinary thất bại.")

            # 4. Lưu thông tin vào Firestore
            media_data = {
                'url': media_url,
                'public_id': uploaded_media.get('public_id'),  # Lưu lại để có thể xóa trên Cloudinary sau này
                'media_type': uploaded_media.get('resource_type'),
                'uploaded_at': firestore.SERVER_TIMESTAMP
            }

            media_collection_ref = db.collection('properties').document(property_pk).collection('media')
            _, new_ref = media_collection_ref.add(media_data)

            media_data['id'] = new_ref.id
            return Response(media_data, status=status.HTTP_201_CREATED)

        except (exceptions.NotFound, exceptions.PermissionDenied) as e:
            # Bắt các lỗi đã được raise từ _check_permission
            return Response({"error": str(e)}, status=e.status_code)
        except Exception as e:
            return Response({"error": f"Lỗi không mong muốn: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, property_pk=None, pk=None):
        """Xóa một file media."""
        # pk là ID của document media, property_pk là ID của BĐS cha
        try:
            # 1. Kiểm tra quyền hạn
            self._check_permission(request, property_pk)

            # 2. Tham chiếu đến document media cần xóa
            media_ref = db.collection('properties').document(property_pk).collection('media').document(pk)
            media_doc = media_ref.get()
            if not media_doc.exists:
                return Response(status=status.HTTP_404_NOT_FOUND)

            # 3. (Tùy chọn nhưng khuyến khích) Xóa file trên Cloudinary
            public_id = media_doc.to_dict().get('public_id')
            if public_id:
                cloudinary.uploader.destroy(public_id)

            # 4. Xóa document trong Firestore
            media_ref.delete()

            return Response(status=status.HTTP_204_NO_CONTENT)

        except (exceptions.NotFound, exceptions.PermissionDenied) as e:
            return Response({"error": str(e)}, status=e.status_code)
        except Exception as e:
            return Response({"error": f"Lỗi không mong muốn: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PropertyAnalysisViewSet(viewsets.ViewSet):
    # Hầu hết các action ở đây cho phép mọi người truy cập
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):
        """Ghi đè, yêu cầu xác thực cho action 'rate'."""
        if self.action == 'rate':
            self.authentication_classes = [FirebaseAuthentication]
            # Yêu cầu cả xác thực token và xác minh danh tính
            self.permission_classes = [permissions.IsAuthenticated, perms.IsIdentityVerified]
        return super().get_permissions()

    @action(detail=False, methods=['get'], url_path='listings-by-city')
    def listings_by_city(self, request):
        """
        Một ví dụ về API phân tích: Đếm số tin đăng theo thành phố.
        """
        client = None
        try:
            # Kết nối đến MongoDB Atlas
            client = MongoClient(settings.MONGO_URI)
            db = client.landify_analytics

            # Thực hiện một truy vấn Aggregation
            pipeline = [
                {
                    '$group': {
                        '_id': '$location.city',  # Nhóm theo trường city trong location
                        'count': {'$sum': 1}  # Đếm số lượng document trong mỗi nhóm
                    }
                },
                {
                    '$sort': {'count': -1}  # Sắp xếp giảm dần
                }
            ]

            results = list(db.listings.aggregate(pipeline))

            return Response(results, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            if client:
                client.close()

    @action(detail=True, methods=['get'])
    def analysis(self, request, pk=None):
        """
        Phân tích tổng quan về bất động sản.
        Hiện tại trả về dữ liệu giả lập như code gốc.
        """
        try:
            # THAY THẾ ORM: Lấy document từ Firestore
            prop_ref = db.collection('properties').document(pk)
            prop_doc = prop_ref.get()
            if not prop_doc.exists:
                return Response({"error": "Bất động sản không tồn tại."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # --- Logic phân tích (giữ nguyên dữ liệu giả lập như code gốc) ---
        # Trong thực tế, bạn sẽ tích hợp API bản đồ, quy hoạch, và các mô hình ML ở đây.
        analysis_data = {
            "location_analysis": {
                "flood_risk": "Thấp",
                "traffic_density": "Trung bình",
                "planning_info": "Khu dân cư ổn định",
                "security_level": "Cao"
            },
            "price_analysis": {
                "estimated_value": "5.2 tỷ VND",
                "price_trend": "Tăng 5% so với năm trước",
                "comparison": [
                    {"id": "some_other_prop_id_1", "price": "5.5 tỷ VND", "area": 80},
                    {"id": "some_other_prop_id_2", "price": "4.9 tỷ VND", "area": 75},
                ]
            }
        }
        return Response(analysis_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='feng-shui')
    def feng_shui_analysis(self, request, pk=None):
        """
        Phân tích phong thủy và gợi ý.
        URL: /api/properties/{id}/feng-shui/
        Body: { "date_of_birth": "1990-01-25" } (Ví dụ)
        """
        try:
            prop_doc = db.collection('properties').document(pk).get()
            if not prop_doc.exists:
                return Response({"error": "Bất động sản không tồn tại."}, status=status.HTTP_404_NOT_FOUND)
            prop_data = prop_doc.to_dict()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        birth_date = None
        dob_str = request.data.get('date_of_birth')
        if dob_str:
            try:
                birth_date = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return Response({"error": "Định dạng ngày tháng không hợp lệ. Vui lòng sử dụng 'YYYY-MM-DD'."},
                                status=status.HTTP_400_BAD_REQUEST)

        # THAY THẾ ORM: Nếu không có ngày sinh trong request, thử lấy từ user đã đăng nhập
        elif hasattr(request, 'firebase_user') and request.firebase_user:
            uid = request.firebase_user.get('uid')
            user_doc = db.collection('users').document(uid).get()
            if user_doc.exists:
                # Giả sử ngày sinh được lưu dưới dạng chuỗi 'YYYY-MM-DD' trong Firestore
                user_dob_str = user_doc.to_dict().get('date_of_birth')
                if user_dob_str:
                    birth_date = datetime.strptime(user_dob_str, '%Y-%m-%d').date()

        if not birth_date:
            return Response({"error": "Vui lòng cung cấp 'date_of_birth' hoặc đăng nhập và cập nhật hồ sơ."},
                            status=status.HTTP_400_BAD_REQUEST)

        # LOGIC NGHIỆP VỤ (giữ nguyên)
        year = birth_date.year
        month = birth_date.month
        if month == 1: year -= 1
        menh = fengshui.calculate_menh(year)

        # THAY THẾ ORM: Lấy thông tin hướng nhà từ document BĐS
        # Giả định dữ liệu hướng được denormalize vào document
        prop_direction = prop_data.get('direction', {})
        prop_direction_name = prop_direction.get('name')
        prop_direction_element = prop_direction.get('element')

        if not prop_direction_name:
            return Response({"error": "Bất động sản này chưa có thông tin hướng nhà."},
                            status=status.HTTP_400_BAD_REQUEST)

        analysis_result = fengshui.analyze_feng_shui_rules(menh, prop_direction_name, prop_direction_element)
        result = {
            "user_menh": menh,
            "property_direction": prop_direction_name,
            "compatibility_score": analysis_result["score"],
            "analysis": analysis_result["analysis"]
        }
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='rate')
    def rate(self, request, pk=None):
        """
        Cho phép người dùng đã xác minh danh tính đánh giá một BĐS
        sau khi xác minh vị trí.
        """
        uid = request.firebase_user.get('uid')

        try:
            prop_doc = db.collection('properties').document(pk).get()
            if not prop_doc.exists:
                return Response({"error": "Bất động sản không tồn tại."}, status=status.HTTP_404_NOT_FOUND)
            prop_data = prop_doc.to_dict()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # LOGIC XÁC MINH VỊ TRÍ (giữ nguyên)
        user_lat = request.data.get('user_lat')
        user_lng = request.data.get('user_lng')
        if user_lat is None or user_lng is None:
            return Response({"error": "Vui lòng cung cấp vị trí hiện tại."}, status=status.HTTP_400_BAD_REQUEST)

        prop_location = prop_data.get('location', {})
        if not prop_location.get('lat') or not prop_location.get('lng'):
            return Response({"error": "BĐS không có thông tin vị trí để xác minh."}, status=status.HTTP_400_BAD_REQUEST)

        MAX_DISTANCE_KM = 0.5
        try:
            user_coords = (float(user_lat), float(user_lng))
            prop_coords = (float(prop_location['lat']), float(prop_location['lng']))
            distance = geodesic(user_coords, prop_coords).kilometers
            if distance > MAX_DISTANCE_KM:
                return Response({"error": f"Bạn cần ở trong phạm vi {MAX_DISTANCE_KM} km để đánh giá."},
                                status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({"error": "Tọa độ cung cấp không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)

        # THAY THẾ ORM: Validate và lưu review vào collection 'reviews'
        serializer = serializers.ReviewSerializer(data=request.data)
        if serializer.is_valid():
            review_data = serializer.validated_data
            review_data['user_id'] = uid
            review_data['property_id'] = pk
            review_data['created_at'] = firestore.SERVER_TIMESTAMP

            db.collection('reviews').add(review_data)
            # TODO: Cần một cơ chế (Cloud Function) để cập nhật rating trung bình cho BĐS
            return Response({"message": "Cảm ơn bạn đã đánh giá!"}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='heatmap', permission_classes=[permissions.AllowAny])
    def potential_heatmap(self, request):
        """
        Cung cấp dữ liệu cho bản đồ nhiệt.
        Hiện tại trả về dữ liệu giả lập như code gốc.
        """
        # Logic tính toán thực tế sẽ cần query nhiều collection trong Firestore
        # và có thể được thực hiện bởi một Cloud Function chạy định kỳ.
        heatmap_data = [
            {"lat": 10.7769, "lng": 106.6954, "weight": 0.9},  # Quận 1
            {"lat": 10.8231, "lng": 106.6297, "weight": 0.6},  # Tân Bình
            {"lat": 10.7909, "lng": 106.7224, "weight": 0.8},  # Bình Thạnh
        ]
        return Response(heatmap_data, status=status.HTTP_200_OK)


class AgoraTokenViewSet(viewsets.ViewSet):
    """
    Một View đơn giản để tạo token Agora.
    Yêu cầu người dùng phải được xác thực.
    """
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @action(methods=['post'], detail=False, url_path='generate')
    def generate_token(self, request):
        # 1. Lấy dữ liệu từ request gửi lên từ Flutter
        channel_name = request.data.get('channelName')
        # Agora SDK yêu cầu uid là số nguyên
        uid = request.data.get('uid')

        if not channel_name or uid is None:
            return Response(
                {"error": "channelName and uid are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Lấy thông tin bí mật từ settings.py
        app_id = settings.AGORA_APP_ID
        app_certificate = settings.AGORA_APP_CERTIFICATE

        # 3. Thiết lập các thông số cho token
        # Token có hiệu lực trong 1 giờ (3600 giây)
        expire_time_in_seconds = 3600
        current_timestamp = int(time.time())
        privilege_expired_ts = current_timestamp + expire_time_in_seconds

        # Người dùng trong cuộc gọi có vai trò là người xuất bản (publisher)
        ROLE_PUBLISHER = 1
        role = ROLE_PUBLISHER

        try:
            # 4. Tạo token
            token = RtcTokenBuilder.buildTokenWithUid(
                app_id,
                app_certificate,
                channel_name,
                uid,
                role,
                privilege_expired_ts
            )

            # 5. Trả token về cho client
            return Response({'token': token}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Error generating token: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

def index(request):
    return HttpResponse('Hello, World! This is the Firestore version.')
#mongodb+srv://doraspeed:<db_password>@clusterlandify.zzl8fiy.mongodb.net/?retryWrites=true&w=majority&appName=ClusterLandify