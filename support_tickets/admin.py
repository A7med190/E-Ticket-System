from django.contrib import admin
from support_tickets.models import SupportCategory, SupportTicket, TicketComment, TicketAttachment


@admin.register(SupportCategory)
class SupportCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}


class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 0
    readonly_fields = ('created_at',)


class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 0
    readonly_fields = ('uploaded_at',)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'title', 'status', 'priority', 'category', 'reporter', 'assignee', 'created_at')
    list_filter = ('status', 'priority', 'category')
    search_fields = ('ticket_number', 'title', 'description')
    readonly_fields = ('ticket_number', 'created_at', 'updated_at', 'resolved_at')
    inlines = [TicketCommentInline, TicketAttachmentInline]


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'is_internal', 'created_at')
    list_filter = ('is_internal',)


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'uploaded_by', 'uploaded_at')
