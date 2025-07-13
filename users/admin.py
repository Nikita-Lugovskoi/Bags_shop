from django.contrib import admin
from users.models import User


# admin.site.register(User)
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('pk', 'email', 'last_name', 'first_name', 'role', 'is_active',)
    list_filter = ('last_name', 'role')
