from django.contrib import admin
from .models import Review, Wishlist, Appointment

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('property', 'user', 'rating', 'created_date')
    list_filter = ('rating',)
    raw_id_fields = ('property', 'user')

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'listing', 'created_date')
    raw_id_fields = ('user', 'listing')

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('listing', 'user', 'appointment_date', 'status')
    list_filter = ('status',)
    raw_id_fields = ('listing', 'user')