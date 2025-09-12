class BusinessLogicError(Exception):
    """Lớp exception cơ sở cho các lỗi nghiệp vụ."""

    pass


class ProtestResolutionError(BusinessLogicError):
    """Exception cho các lỗi khi xử lý kháng nghị."""

    pass


class EkycError(BusinessLogicError):
    """Exception cho các lỗi trong quy trình eKYC."""

    pass
