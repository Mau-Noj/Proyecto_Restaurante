from django.contrib import admin

from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("user", "position", "phone", "hire_date")
    list_filter = ("position",)
    search_fields = ("user__username", "user__first_name", "user__last_name", "user__email")
