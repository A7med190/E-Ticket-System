import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def process_outbox_messages():
    from common.outbox.models import outbox_manager, OutboxStatus, OutboxMessage
    
    settings_config = getattr(settings, 'OUTBOX_SETTINGS', {})
    batch_size = settings_config.get('BATCH_SIZE', 100)
    
    messages = outbox_manager.get_pending_messages(batch_size=batch_size)
    processed = 0
    failed = 0

    for message in messages:
        outbox_manager.mark_processing(message)
        
        try:
            success, result = send_message(message)
            if success:
                outbox_manager.mark_sent(message)
                processed += 1
                logger.info(f'Outbox message {message.id} sent successfully')
            else:
                outbox_manager.mark_failed(message, result.get('error', 'Unknown error'))
                failed += 1
                logger.warning(f'Outbox message {message.id} failed: {result.get("error")}')
        except Exception as e:
            outbox_manager.mark_failed(message, str(e))
            failed += 1
            logger.error(f'Outbox message {message.id} error: {e}')

    logger.info(f'Outbox processing complete: {processed} sent, {failed} failed')
    return {'processed': processed, 'failed': failed}


def send_message(message) -> tuple[bool, dict]:
    webhook_settings = getattr(settings, 'WEBHOOK_SETTINGS', {})
    timeout = webhook_settings.get('TIMEOUT', 30)
    
    import json
    import hashlib
    import hmac
    import time
    
    payload = json.dumps(message.payload, separators=(',', ':'))
    timestamp = str(int(time.time()))
    
    secret = webhook_settings.get('SECRET_KEY', settings.SECRET_KEY)
    signature = hmac.new(
        secret.encode(),
        f'{timestamp}.{payload}'.encode(),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        'Content-Type': 'application/json',
        'X-Webhook-Signature': f'sha256={signature}',
        'X-Webhook-Timestamp': timestamp,
        'X-Outbox-Message-Id': str(message.id),
        'X-Event-Type': message.event_type,
    }
    headers.update(message.headers or {})

    try:
        response = requests.post(
            message.destination,
            data=payload,
            headers=headers,
            timeout=timeout,
        )
        success = 200 <= response.status_code < 300
        return success, {
            'status_code': response.status_code,
            'response': response.text[:500] if response.text else '',
        }
    except requests.Timeout:
        return False, {'error': 'Request timeout'}
    except requests.RequestException as e:
        return False, {'error': str(e)}


def cleanup_old_outbox_messages(days: int = 30):
    from django.utils import timezone
    from datetime import timedelta
    from common.outbox.models import OutboxMessage, OutboxStatus
    
    cutoff = timezone.now() - timedelta(days=days)
    deleted_count = OutboxMessage.objects.filter(
        status__in=[OutboxStatus.SENT, OutboxStatus.FAILED],
        processed_at__lt=cutoff,
    ).delete()[0]
    
    logger.info(f'Cleaned up {deleted_count} old outbox messages')
    return deleted_count
