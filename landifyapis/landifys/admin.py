from landifys.models import User, Post, ListingType, Listing, Property, PropertyType, Location, District, City \
    , Ward, Report, Utility
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
admin.site.register(Post, MyPost)
admin.site.register(ListingType)
admin.site.register(Listing)
admin.site.register(PropertyType)
admin.site.register(Property)

# Location

admin.site.register(Location)

# Report
admin.site.register(Report)

# Property
admin.site.register(Utility)