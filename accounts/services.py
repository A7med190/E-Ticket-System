from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings


def send_html_email(to_email, subject, template_name, context):
    context['frontend_url'] = settings.FRONTEND_URL
    html_content = render_to_string(f'emails/{template_name}.html', context)
    from_email = settings.DEFAULT_FROM_EMAIL

    email = EmailMultiAlternatives(
        subject=subject,
        body=html_content,
        from_email=from_email,
        to=[to_email],
    )
    email.attach_alternative(html_content, 'text/html')
    email.send()
