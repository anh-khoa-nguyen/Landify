from landifys.models import User, Post, Category
from django.contrib import admin
from django.utils.safestring import mark_safe
from django import forms
from ckeditor_uploader.widgets \
import CKEditorUploadingWidget

class PostForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorUploadingWidget)

    class Meta:
        model = Post
        fields = '__all__'

class MyPost(admin.ModelAdmin):
    form = PostForm

# Register your models here.
admin.site.register(User)
admin.site.register(Category)
admin.site.register(Post, MyPost)
