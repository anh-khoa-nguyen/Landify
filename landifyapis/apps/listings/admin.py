from django import forms
from django.contrib import admin
from ckeditor_uploader.widgets import CKEditorUploadingWidget

from .models import Listing, ListingPropertyFeatureValue, ListingType, UnitPrice, VipType
from apps.social.models import Post

class ListingPropertyFeatureValueInline(admin.TabularInline):
    model = ListingPropertyFeatureValue
    extra = 1
    readonly_fields = ("display_value",)
    fields = ("feature", "value", "display_value")
    raw_id_fields = ('feature',)

@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "listing_type", "status", "spam_check_status", "created_date", "active")
    list_filter = ("active", "status", "spam_check_status", "listing_type")
    search_fields = ("title", "user__username", "property__location__street")
    readonly_fields = ("created_date", "updated_date")
    raw_id_fields = ("user", "property")
    inlines = [ListingPropertyFeatureValueInline]

@admin.register(VipType)
class VipTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "price_per_day", "sort_priority", "active")
    search_fields = ("name", "code")

admin.site.register(ListingType)
admin.site.register(UnitPrice)