from typing import Tuple

from apps.users.models import User

from .models import Post, Reaction

def process_post_reaction(
    *, user: User, post: Post, reaction_type: str
) -> Tuple[str, Reaction | None]:
    """
    Xử lý logic bày tỏ cảm xúc (like, love...) cho một bài đăng.
    Hàm này sẽ tạo mới, cập nhật hoặc xóa một reaction.

    Args:
        user (User): Người bày tỏ cảm xúc.
        post (Post): Bài đăng được tương tác.
        reaction_type (str): Loại cảm xúc (ví dụ: 'like', 'love').
    """

    reaction, created = Reaction.objects.get_or_create(user=user, post=post, defaults={"type": reaction_type})

    if created:
        # Nếu được tạo mới, trả về trạng thái 'created'
        return "created", reaction

    # Nếu reaction đã tồn tại:
    if reaction.type == reaction_type:
        # Người dùng bấm lại vào cảm xúc cũ -> Xóa reaction
        reaction.delete()
        return "deleted", None
    else:
        # Người dùng bấm vào cảm xúc khác -> Cập nhật reaction
        reaction.type = reaction_type
        reaction.save()
        return "updated", reaction