from django.contrib import admin
from .models import Member

class MemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'user')  # Show owner of the member
    list_filter = ('user',)  # Add filter by user

    # Superuser sees all members, others see only their own
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # All members
        return qs.filter(user=request.user)  # Only owner’s members

admin.site.register(Member, MemberAdmin)