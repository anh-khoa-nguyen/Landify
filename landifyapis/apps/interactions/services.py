from datetime import datetime

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone
from typing import Tuple

from apps.users.models import User
from apps.listings.models import Listing, Property
from .models import Appointment, Review, Cooperation, Chat, Wishlist
from .serializers import ReviewSerializer

from apps.common.tasks import notifications
from apps.common.services import BusinessLogicError

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance

from ..common.utils import firebase


# ==============================================================================
# APPOINTMENT SERVICES (DỊCH VỤ LỊCH HẸN)
# ==============================================================================
# Các hàm xử lý logic nghiệp vụ liên quan đến việc tạo và quản lý Lịch hẹn.

def create_appointment(
    *, user: User, listing: Listing, appointment_date: datetime, note: str
) -> Appointment:
    """Tạo một lịch hẹn mới và thông báo cho chủ tin đăng."""
    if appointment_date < timezone.now():
        raise BusinessLogicError("Không thể đặt lịch hẹn trong quá khứ.")

    appointment = Appointment.objects.create(
        user=user,
        listing=listing,
        appointment_date=appointment_date,
        note=note,
        status=Appointment.Status.PENDING,
    )

    # Gửi thông báo cho chủ tin đăng
    # notifications.notify_listing_owner_of_new_appointment.delay(appointment.id)

    return appointment


def update_appointment_status(
*, appointment: Appointment, new_status: str, actor: User
) -> Appointment:
    """
    Cập nhật trạng thái của một lịch hẹn.
    Hàm này kiểm tra quyền của người thực hiện hành động.
    """

    # 1. Lấy các đối tượng liên quan
    listing_owner = appointment.listing.user
    requester = appointment.user

    # 2. Kiểm tra các quy tắc nghiệp vụ
    if appointment.status in [Appointment.Status.COMPLETED, Appointment.Status.CANCELLED]:
        raise BusinessLogicError(
            f"Không thể thay đổi trạng thái của lịch hẹn đã {appointment.get_status_display().lower()}."
        )

    # 3. Kiểm tra quyền (Authorization)
    can_confirm_or_complete = actor == listing_owner or actor.role == User.Role.ADMIN
    can_cancel = actor == listing_owner or actor == requester or actor.role == User.Role.ADMIN

    if new_status == Appointment.Status.CONFIRMED and not can_confirm_or_complete:
        raise BusinessLogicError("Chỉ chủ tin đăng hoặc quản trị viên mới có thể xác nhận lịch hẹn.")

    if new_status == Appointment.Status.COMPLETED and not can_confirm_or_complete:
        raise BusinessLogicError("Chỉ chủ tin đăng hoặc quản trị viên mới có thể hoàn thành lịch hẹn.")

    if new_status == Appointment.Status.CANCELLED and not can_cancel:
        raise BusinessLogicError("Bạn không có quyền hủy lịch hẹn này.")

    appointment.status = new_status
    appointment.save(update_fields=["status"])

    # 5. Kích hoạt các tác dụng phụ (Side Effects) - Gửi thông báo
    # Ví dụ: Gửi thông báo cho người đặt hẹn khi chủ nhà xác nhận/hủy lịch
    if actor == listing_owner and new_status in [
        Appointment.Status.CONFIRMED,
        Appointment.Status.CANCELLED,
    ]:
        # notifications.notify_user_of_appointment_status_change.delay(appointment.id, actor.id)
        print(
            f"Kích hoạt thông báo cho người dùng {requester.id} về việc lịch hẹn {appointment.id} đã được {new_status}"
        )

    # Ví dụ: Gửi thông báo cho chủ nhà khi người đặt hẹn tự hủy lịch
    if actor == requester and new_status == Appointment.Status.CANCELLED:
        # notifications.notify_owner_of_appointment_cancellation.delay(appointment.id, actor.id)
        print(f"Kích hoạt thông báo cho chủ nhà {listing_owner.id} về việc lịch hẹn {appointment.id} đã bị hủy")

    return appointment

# ==============================================================================
# REVIEW & WISHLIST SERVICES (DỊCH VỤ ĐÁNH GIÁ & YÊU THÍCH)
# ==============================================================================
# Các hàm xử lý logic nghiệp vụ cho việc Đánh giá và thêm vào Danh sách yêu thích.

def rate_property_and_update_score(
    *, user: User, prop: Property, serializer: ReviewSerializer,
    user_latitude: float, user_longitude: float
) -> Review:
    """Tạo một đánh giá và cập nhật điểm trung bình, sau khi đã xác minh vị trí."""
    # 1. Kiểm tra xem bất động sản có tọa độ không
    if not prop.location or not prop.location.point:
        # Nếu BĐS không có tọa độ, chúng ta không thể xác minh.
        # Tùy vào yêu cầu, bạn có thể cho qua hoặc chặn lại. Ở đây, chúng ta sẽ chặn.
        raise BusinessLogicError("Không thể xác minh vị trí do bất động sản này chưa được ghim trên bản đồ.")

    # 2. Tạo đối tượng Point từ tọa độ của người dùng
    user_location = Point(user_longitude, user_latitude, srid=4326)

    # 3. Lấy tọa độ của bất động sản
    property_location = prop.location.point

    # 4. Tính khoảng cách
    distance_in_meters = property_location.distance(user_location) * 100000 # Chuyển đổi từ độ sang mét (ước lượng)

    VERIFICATION_RADIUS_METERS = 5000

    # 5. So sánh với ngưỡng 5km
    if distance_in_meters > VERIFICATION_RADIUS_METERS:
        raise BusinessLogicError(
            f"Bạn phải ở trong bán kính {VERIFICATION_RADIUS_METERS / 1000}km của bất động sản để có thể gửi đánh giá."
        )

    with transaction.atomic():
        review = serializer.save(user=user, property=prop, point=user_location)

        owner_profile = prop.owner.profile

        # Cập nhật điểm trung bình dựa trên tất cả các đánh giá nhắm vào các BĐS của chủ sở hữu.
        agg_result = Review.objects.filter(property__owner=prop.owner).aggregate(
            total_rating=Sum("rating"), total_count=Count("id")
        )

        if agg_result["total_count"] > 0:
            owner_profile.rating_score = agg_result["total_rating"] / agg_result["total_count"]
            owner_profile.rating_count = agg_result["total_count"]
            owner_profile.save(update_fields=["rating_score", "rating_count"])

        return review

def toggle_wishlist_item(*, user: User, listing: Listing) -> Tuple[str, Wishlist | None]:
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=user,
        listing=listing
    )

    if created:
        return "added", wishlist_item
    else:
        wishlist_item.delete()
        return "removed", None

# ==============================================================================
# CHAT SERVICES (DỊCH VỤ TRÒ CHUYỆN)
# ==============================================================================
# Các hàm xử lý việc tạo và truy vấn các Cuộc trò chuyện.

def get_or_create_private_chat(*, user1: User, user2: User, listing: Listing = None) -> tuple[Chat, bool]:
    """
    Tìm hoặc tạo một cuộc trò chuyện RIÊNG TƯ giữa 2 người.
    VÀ đồng bộ lên Firestore nếu một cuộc trò chuyện MỚI được tạo.
    """
    # Tìm một chat có type=PRIVATE, có đúng 2 người tham gia,
    # và 2 người đó chính là user1 và user2.
    chat_qs = Chat.objects.annotate(
        num_participants=Count('participants')
    ).filter(
        chat_type=Chat.ChatType.PRIVATE,
        num_participants=2,
        participants=user1
    ).filter(
        participants=user2
    )

    # Lọc thêm theo listing nếu có
    if listing:
        chat_qs = chat_qs.filter(listing=listing)

    # Nếu tìm thấy, trả về chat đó
    chat = chat_qs.first()
    if chat:
        return chat, False

    # Nếu không, tạo chat mới trong một transaction
    with transaction.atomic():
        new_chat = Chat.objects.create(
            chat_type=Chat.ChatType.PRIVATE,
            listing=listing
        )
        new_chat.participants.add(user1, user2)

        transaction.on_commit(
            lambda: firebase.create_firestore_chat_session(
                postgres_chat_id=new_chat.id,
                user1=user1,
                user2=user2,
                listing_title=listing.title if listing else "cuộc trò chuyện"
            )
        )
        # ======================================

    return new_chat, True

def create_group_chat(*, owner: User, participants: list[User], name: str, listing: Listing = None) -> Chat:
    """
    Tạo một cuộc trò chuyện NHÓM mới.
    """
    chat = Chat.objects.create(
        chat_type=Chat.ChatType.GROUP,
        name=name,
        listing=listing
    )

    # Thêm người tạo và tất cả những người tham gia khác vào phòng
    all_participants = [owner] + participants
    chat.participants.set(all_participants)
    return chat

# Hàm để lấy tất cả chat của một người dùng (cả riêng và nhóm)
def get_all_chats_for_user(user: User):
    return user.chats.all().order_by('-last_message_timestamp')

#========================================================
class CooperationActionError(BusinessLogicError):
    pass

def respond_to_cooperation_request(
    *,
    cooperation: Cooperation,
    actor: User,
    action: str,
    reason: str = None
) -> Cooperation:
    """
    Xử lý hành động chấp nhận hoặc từ chối một yêu cầu hợp tác.
    """
        # 1. Kiểm tra quyền: Chỉ chủ tin đăng (owner) mới được phản hồi
    with transaction.atomic():
        if cooperation.owner != actor:
            raise CooperationActionError("Bạn không có quyền phản hồi yêu cầu này.")

        # 2. Kiểm tra trạng thái: Chỉ có thể xử lý các yêu cầu đang chờ
        if cooperation.status != Cooperation.Status.PENDING:
            raise CooperationActionError("Yêu cầu này đã được xử lý trước đó.")

        # 3. Cập nhật trạng thái dựa trên hành động
        if action == 'accept':
            cooperation.status = Cooperation.Status.ACCEPTED
            cooperation.rejection_reason = None # Xóa lý do từ chối cũ nếu có
        elif action == 'reject':
            cooperation.status = Cooperation.Status.REJECTED
            cooperation.rejection_reason = reason
        else:
            raise CooperationActionError("Hành động không hợp lệ. Chỉ chấp nhận 'accept' hoặc 'reject'.")

        cooperation.save()

        title = f"Yêu cầu hợp tác của bạn đã được {cooperation.get_status_display()}"
        content = f"Chủ tin '{cooperation.owner.username}' đã {cooperation.get_status_display().lower()} yêu cầu hợp tác cho tin '{cooperation.listing.title}'."
        related_item = {"type": "cooperation", "id": cooperation.id}

        # Task chỉ được đưa vào hàng đợi SAU KHI cooperation.save() thành công
        transaction.on_commit(lambda: notifications.send_notification_to_user.delay(
            user_id=cooperation.agent.id,
            category="cooperation_update",
            title=title,
            content=content,
            related_item=related_item
        ))

    return cooperation