from django.contrib import admin
from comments.models import Comment


# Register your models here.
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_display = (
        'tweet',
        'user',
        'content',
        'created_at',
        'updated_at',
    )
