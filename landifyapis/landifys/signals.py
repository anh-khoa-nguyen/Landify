from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Listing
from .tasks import check_listing_for_spam

#celery -A landifyapis worker -l info --pool=solo

@receiver(post_save, sender=Listing)
def listing_post_save_handler(sender, instance, created, **kwargs):
    if created:
        print(f"Signal nhận được: Listing mới (ID: {instance.id}) đã được tạo. Gửi tác vụ kiểm tra spam...")
        # Gọi tác vụ Celery chạy nền.
        # .delay() là cách để thực thi tác vụ một cách bất đồng bộ.
        # Luôn truyền ID hoặc các kiểu dữ liệu cơ bản, không truyền cả object 'instance'.
        check_listing_for_spam.delay(instance.id)
