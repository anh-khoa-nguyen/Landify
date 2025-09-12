# landifys/docs/verification_docs.py

from drf_spectacular.utils import extend_schema, OpenApiExample

# ==============================================================================
# ĐỊNH NGHĨA SCHEMA CHO VERIFICATION VIEWSET
# ==============================================================================

# Action: request_phone_verification_otp (POST /api/verification/request-otp/)
request_otp_schema = extend_schema(
    summary="Yêu cầu gửi mã OTP xác thực SĐT",
    description=(
        "Bắt đầu quy trình xác thực số điện thoại cho người dùng đang đăng nhập. "
        "Hệ thống sẽ tạo và gửi một mã OTP qua SMS đến SĐT đã đăng ký trong hồ sơ."
    ),
    request=None, # Không có request body
    responses={
        200: {
            'type': 'object',
            'properties': {'message': {'type': 'string'}}
        },
        400: {'description': 'Người dùng chưa cập nhật SĐT hoặc có lỗi khi gửi SMS.'}
    }
)

# Action: verify_phone_otp (POST /api/verification/verify-otp/)
verify_otp_schema = extend_schema(
    summary="Xác thực mã OTP",
    description="Người dùng gửi mã OTP nhận được qua SMS để hoàn tất việc xác thực số điện thoại.",
    request={
        'application/json': {
            'type': 'object',
            'properties': {'otp': {'type': 'string', 'description': 'Mã OTP gồm 6 chữ số'}},
            'required': ['otp']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {'message': {'type': 'string'}}
        },
        400: {'description': 'Mã OTP không hợp lệ hoặc đã hết hạn.'}
    },
    examples=[
        OpenApiExample('Ví dụ', value={'otp': '123456'})
    ]
)

# Action: verify_id_card (POST /api/verification/verify-id-card/)
verify_id_card_schema = extend_schema(
    summary="eKYC Bước 1: Trích xuất thông tin CCCD",
    description=(
        "Người dùng tải lên ảnh mặt trước của Căn cước công dân (CCCD). "
        "Hệ thống sẽ sử dụng AI để đọc và trích xuất thông tin từ ảnh. "
        "Đây là bước đầu tiên trong quy trình eKYC."
    ),
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'id_card_image': {'type': 'string', 'format': 'binary'}
            },
            'required': ['id_card_image']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'message': {'type': 'string'},
                'data': {
                    'type': 'object',
                    'description': 'Dữ liệu được trích xuất từ CCCD',
                    'properties': {
                        'id': {'type': 'string', 'description': 'Số CCCD'},
                        'name': {'type': 'string', 'description': 'Họ và tên'},
                        'dob': {'type': 'string', 'description': 'Ngày sinh'},
                        'sex': {'type': 'string', 'description': 'Giới tính'},
                        'nationality': {'type': 'string', 'description': 'Quốc tịch'},
                        'home': {'type': 'string', 'description': 'Quê quán'},
                        'address': {'type': 'string', 'description': 'Địa chỉ thường trú'},
                        'doe': {'type': 'string', 'description': 'Ngày hết hạn'},
                    }
                }
            }
        },
        400: {'description': 'Ảnh không hợp lệ hoặc không thể đọc được thông tin.'}
    }
)

# Action: verify_liveness (POST /api/verification/verify-liveness/)
verify_liveness_schema = extend_schema(
    summary="eKYC Bước 2: Xác thực khuôn mặt (Liveness Check)",
    description=(
        "Bước cuối cùng của eKYC. Người dùng tải lên một video ngắn quay khuôn mặt của mình. "
        "Hệ thống sẽ kiểm tra xem đây có phải người thật không (liveness) và so sánh khuôn mặt trong video "
        "với ảnh trên CCCD đã được xử lý ở Bước 1. **Endpoint này phải được gọi ngay sau Bước 1.**"
    ),
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'video': {'type': 'string', 'format': 'binary'}
            },
            'required': ['video']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {'message': {'type': 'string', 'example': 'Xác minh danh tính hoàn tất!'}}
        },
        400: {'description': 'Phiên xác thực hết hạn, không phải người thật, hoặc khuôn mặt không khớp.'}
    }
)