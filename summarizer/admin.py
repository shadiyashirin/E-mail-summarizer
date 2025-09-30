from django.contrib import admin
from .models import EmailSummary, EmailResult

class EmailResultInline(admin.TabularInline):
    model = EmailResult
    extra = 0

@admin.register(EmailSummary)
class EmailSummaryAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'processed']
    inlines = [EmailResultInline]

@admin.register(EmailResult)
class EmailResultAdmin(admin.ModelAdmin):
    list_display = ['sender', 'subject', 'email_summary']
    list_filter = ['email_summary']