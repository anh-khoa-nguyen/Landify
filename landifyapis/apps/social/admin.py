from django import forms
from django.contrib import admin

from ckeditor_uploader.widgets import CKEditorUploadingWidget

from .models import Post, Comment, Reaction

# =======================================================================
# == ADMIN CONFIGURATIONS
# =======================================================================

class CommentInline(admin.TabularInline):
    """
    Hiển thị các bình luận liên quan ngay trên trang chi tiết của một Bài đăng.
    """
    model = Comment
    extra = 0  # Không hiển thị dòng trống để thêm mới, chỉ hiển thị các comment đã có
    fields = ('user', 'content', 'created_date', 'active')
    readonly_fields = ('user', 'content', 'created_date')
    can_delete = True
    show_change_link = True # Cho phép nhấn vào để đi đến trang sửa chi tiết của comment


class PostForm(forms.ModelForm):
    """
    Form tùy chỉnh để tích hợp CKEditor vào trường 'content' của model Post.
    """
    content = forms.CharField(
        label="Nội dung chi tiết",
        widget=CKEditorUploadingWidget()
    )

    class Meta:
        model = Post
        fields = "__all__"


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """
    Tùy chỉnh trang quản trị cho model Post.
    """
    form = PostForm
    list_display = ("title", "user", "comment_count", "reaction_count", "created_date", "active")
    list_filter = ("active", "created_date")
    search_fields = ("title", "user__username", "content")
    readonly_fields = ("created_date", "updated_date")
    # Tối ưu hóa việc chọn User, đặc biệt khi có hàng nghìn user
    raw_id_fields = ('user',)
    inlines = [CommentInline] # Nhúng danh sách comment vào trang chi tiết Post

    def get_queryset(self, request):
        # Tối ưu hóa truy vấn bằng cách tính toán sẵn số lượng comment và reaction
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _comment_count=Comment.Count('comments', distinct=True),
            _reaction_count=Reaction.Count('reactions', distinct=True)
        )
        return queryset

    @admin.display(description="Số bình luận", ordering='_comment_count')
    def comment_count(self, obj):
        return obj._comment_count

    @admin.display(description="Số cảm xúc", ordering='_reaction_count')
    def reaction_count(self, obj):
        return obj._reaction_count


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """
    Tùy chỉnh trang quản trị cho model Comment.
    """
    list_display = ('__str__', 'post_link', 'user', 'created_date', 'active')
    list_filter = ('active', 'created_date')
    search_fields = ('content', 'user__username', 'post__title')
    readonly_fields = ('created_date', 'updated_date')
    raw_id_fields = ('post', 'user')

    @admin.display(description="Bài đăng")
    def post_link(self, obj):
        # Tạo một link để dễ dàng di chuyển đến trang sửa bài đăng liên quan
        from django.urls import reverse
        from django.utils.html import format_html
        link = reverse("admin:social_post_change", args=[obj.post.id])
        return format_html('<a href="{}">{}</a>', link, obj.post.title)


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    """
    Tùy chỉnh trang quản trị cho model Reaction.
    """
    list_display = ('post', 'user', 'type', 'created_date')
    list_filter = ('type', 'created_date')
    # Không cho phép thêm/sửa reaction từ trang admin, chỉ xem
    readonly_fields = ('post', 'user', 'type')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False