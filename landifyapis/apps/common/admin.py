from django.contrib import admin
from .models import SiteStatistic

@admin.register(SiteStatistic)
class SiteStatisticAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'last_updated')
    readonly_fields = ('last_updated',)