from drf_spectacular.utils import OpenApiResponse

NOT_FOUND_RESPONSE = {
    '404': OpenApiResponse(description='Đối tượng không tồn tại.')
}

UNAUTHORIZED_RESPONSE = {
    '401': OpenApiResponse(description='Xác thực thất bại.')
}