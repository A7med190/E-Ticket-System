import csv
import io
import uuid
from rest_framework.response import Response
from rest_framework import status


def generate_ticket_number():
    from support_tickets.models import SupportTicket
    last = SupportTicket.objects.order_by('-id').first()
    num = (last.id + 1) if last else 1
    return f'SUP-{num:06d}'


def generate_booking_code():
    while True:
        code = 'EVT-' + uuid.uuid4().hex[:6].upper()
        from event_tickets.models import Booking
        if not Booking.objects.filter(booking_code=code).exists():
            return code


def export_to_csv(queryset, field_names, filename='export'):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(field_names)
    for obj in queryset:
        row = []
        for field in field_names:
            value = getattr(obj, field, None)
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            elif hasattr(value, 'name'):
                value = str(value)
            row.append(value)
        writer.writerow(row)
    output.seek(0)
    response = Response(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    return response


def generate_qr_code(booking):
    import qrcode
    from io import BytesIO
    from django.core.files.base import ContentFile
    from PIL import Image

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f'{booking.booking_code}|{booking.event.title}|{booking.ticket_type.name}')
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    filename = f'qr_{booking.booking_code}.png'
    booking.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
