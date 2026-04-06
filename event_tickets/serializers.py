from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from event_tickets.models import EventCategory, Event, TicketType, Booking, Payment


class EventCategorySerializer(serializers.ModelSerializer):
    event_count = serializers.IntegerField(source='events.count', read_only=True)

    class Meta:
        model = EventCategory
        fields = ('id', 'name', 'slug', 'description', 'event_count', 'created_at')
        read_only_fields = ('id', 'event_count', 'created_at')


class TicketTypeSerializer(serializers.ModelSerializer):
    is_on_sale = serializers.BooleanField(read_only=True)

    class Meta:
        model = TicketType
        fields = ('id', 'event', 'name', 'price', 'quantity_total', 'quantity_available', 'sale_start', 'sale_end', 'description', 'is_on_sale')
        read_only_fields = ('id', 'is_on_sale')


class EventListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    organizer_name = serializers.CharField(source='organizer.get_full_name', read_only=True)
    tickets_sold = serializers.IntegerField(read_only=True)
    is_sold_out = serializers.BooleanField(read_only=True)

    class Meta:
        model = Event
        fields = ('id', 'title', 'slug', 'category_name', 'organizer_name', 'venue', 'start_date', 'end_date', 'image', 'is_published', 'capacity', 'tickets_sold', 'is_sold_out', 'created_at')
        read_only_fields = ('id', 'tickets_sold', 'is_sold_out', 'created_at')


class EventSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    organizer_name = serializers.CharField(source='organizer.get_full_name', read_only=True)
    ticket_types = TicketTypeSerializer(many=True, read_only=True)
    tickets_sold = serializers.IntegerField(read_only=True)
    is_sold_out = serializers.BooleanField(read_only=True)

    class Meta:
        model = Event
        fields = ('id', 'title', 'slug', 'description', 'category', 'category_name', 'organizer', 'organizer_name', 'venue', 'venue_address', 'start_date', 'end_date', 'image', 'is_published', 'capacity', 'tickets_sold', 'is_sold_out', 'ticket_types', 'created_at', 'updated_at')
        read_only_fields = ('id', 'organizer', 'tickets_sold', 'is_sold_out', 'created_at', 'updated_at')


class EventCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ('title', 'slug', 'description', 'category', 'venue', 'venue_address', 'start_date', 'end_date', 'image', 'capacity')

    def create(self, validated_data):
        validated_data['organizer'] = self.context['request'].user
        return super().create(validated_data)


class BookingListSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    ticket_type_name = serializers.CharField(source='ticket_type.name', read_only=True)
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = ('id', 'booking_code', 'event_title', 'ticket_type_name', 'quantity', 'total_price', 'status', 'qr_code_url', 'created_at')
        read_only_fields = ('id', 'booking_code', 'created_at')

    def get_qr_code_url(self, obj):
        if obj.qr_code:
            return obj.qr_code.url
        return None


class BookingSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    ticket_type_name = serializers.CharField(source='ticket_type.name', read_only=True)
    qr_code_url = serializers.SerializerMethodField()
    payments = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = ('id', 'booking_code', 'user', 'event', 'event_title', 'ticket_type', 'ticket_type_name', 'quantity', 'total_price', 'status', 'qr_code', 'qr_code_url', 'payments', 'created_at', 'updated_at')
        read_only_fields = ('id', 'booking_code', 'user', 'total_price', 'status', 'qr_code', 'created_at', 'updated_at')

    def get_qr_code_url(self, obj):
        if obj.qr_code:
            return obj.qr_code.url
        return None

    def get_payments(self, obj):
        from event_tickets.serializers import PaymentSerializer
        return PaymentSerializer(obj.payments.all(), many=True).data


class BookingCreateSerializer(serializers.Serializer):
    ticket_type_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        try:
            ticket_type = TicketType.objects.select_related('event').get(id=attrs['ticket_type_id'])
        except TicketType.DoesNotExist:
            raise serializers.ValidationError({'ticket_type_id': 'Ticket type not found.'})

        if not ticket_type.is_on_sale:
            raise serializers.ValidationError({'ticket_type_id': 'This ticket type is not currently on sale.'})

        if ticket_type.quantity_available < attrs['quantity']:
            raise serializers.ValidationError({'quantity': f'Only {ticket_type.quantity_available} tickets available.'})

        attrs['ticket_type'] = ticket_type
        attrs['total_price'] = ticket_type.price * attrs['quantity']
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        ticket_type = validated_data['ticket_type']
        quantity = validated_data['quantity']

        ticket_type.quantity_available -= quantity
        ticket_type.save(update_fields=['quantity_available'])

        from common.utils import generate_booking_code
        booking = Booking.objects.create(
            user=self.context['request'].user,
            event=ticket_type.event,
            ticket_type=ticket_type,
            quantity=quantity,
            total_price=validated_data['total_price'],
            booking_code=generate_booking_code(),
        )
        return booking


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('id', 'booking', 'amount', 'method', 'status', 'transaction_id', 'paid_at', 'created_at')
        read_only_fields = ('id', 'paid_at', 'created_at')


class PaymentCreateSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=Payment.Method.choices)
    transaction_id = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        booking = self.context.get('booking')
        if booking and booking.status == Booking.Status.CANCELLED:
            raise serializers.ValidationError({'booking': 'Cannot pay for a cancelled booking.'})
        if booking and booking.status == Booking.Status.CONFIRMED:
            raise serializers.ValidationError({'booking': 'Booking is already confirmed.'})
        return attrs
