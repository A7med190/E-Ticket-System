from django.contrib import admin
from event_tickets.models import EventCategory, Event, TicketType, Booking, Payment


@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}


class TicketTypeInline(admin.TabularInline):
    model = TicketType
    extra = 0


class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    readonly_fields = ('created_at',)


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('created_at', 'paid_at')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'organizer', 'venue', 'start_date', 'is_published', 'capacity')
    list_filter = ('is_published', 'category')
    search_fields = ('title', 'description', 'venue')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [TicketTypeInline, BookingInline]


@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'event', 'price', 'quantity_total', 'quantity_available', 'sale_start', 'sale_end')
    list_filter = ('event',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_code', 'user', 'event', 'ticket_type', 'quantity', 'total_price', 'status', 'created_at')
    list_filter = ('status', 'event')
    search_fields = ('booking_code', 'user__email')
    readonly_fields = ('booking_code', 'created_at', 'updated_at')
    inlines = [PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'amount', 'method', 'status', 'paid_at')
    list_filter = ('method', 'status')
