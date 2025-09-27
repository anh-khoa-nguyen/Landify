from typing import Tuple

from apps.users.models import User

from .models import Post, Reaction

def process_post_reaction(
    *, user: User, post: Post, reaction_type: str
) -> Tuple[str, Reaction | None]:
    """
    Xử lý logic bày tỏ cảm xúc (like, love...) cho một bài đăng.
    Hàm này sẽ tạo mới, cập nhật hoặc xóa một reaction.
    """

    reaction, created = Reaction.objects.get_or_create(user=user, post=post, defaults={"type": reaction_type})

    if created:
        return "created", reaction

    if reaction.type == reaction_type:
        reaction.delete()
        return "deleted", None
    else:
        reaction.type = reaction_type
        reaction.save()
        return "updated", reaction