class DynamicFieldsMixin:
    """
    Một Mixin cho phép serializer có thể tùy chỉnh các trường (fields)
    được trả về một cách linh hoạt thông qua tham số 'fields' hoặc 'exclude'
    khi khởi tạo.
    """

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        exclude = kwargs.pop("exclude", None)

        super().__init__(*args, **kwargs)

        if fields is not None:
            # Logic để chỉ giữ lại các trường trong 'fields'
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)

        elif exclude is not None:
            # Logic để loại bỏ các trường trong 'exclude'
            excluded_fields = set(exclude)
            for field_name in excluded_fields:
                self.fields.pop(field_name, None)