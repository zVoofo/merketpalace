import random
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from .models import SmsCode, EmailVerificationCode


def normalize_phone(phone: str) -> str:
    digits = ''.join(c for c in phone if c.isdigit())
    if len(digits) == 11 and digits[0] == '8':
        digits = '7' + digits[1:]
    return '+' + digits if digits else phone


def generate_code() -> str:
    return str(random.randint(100000, 999999))


def send_email_verification(user, email: str) -> str:
    code = generate_code()
    EmailVerificationCode.objects.filter(user=user, email=email, used=False).update(used=True)
    EmailVerificationCode.objects.create(
        user=user, email=email, code=code,
        expires_at=timezone.now() + timedelta(minutes=15),
    )
    subject = 'Код подтверждения email — MarketPlace'
    body = f'Ваш код подтверждения: {code}\n\nКод действует 15 минут.'
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
    return code


def verify_email_code(user, email: str, code: str) -> bool:
    row = EmailVerificationCode.objects.filter(
        user=user, email=email, code=code, used=False,
        expires_at__gt=timezone.now(),
    ).order_by('-created_at').first()
    if not row:
        return False
    row.used = True
    row.save()
    user.email = email
    user.email_verified = True
    user.save(update_fields=['email', 'email_verified'])
    return True


def send_phone_verification(user, phone: str) -> str:
    phone = normalize_phone(phone)
    code = generate_code()
    SmsCode.objects.filter(phone=phone, purpose='verify', used=False).update(used=True)
    SmsCode.objects.create(
        phone=phone, code=code, purpose='verify',
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    if settings.DEBUG:
        print(f'[SMS TEST] Phone {phone} code: {code}')
    return code


def verify_phone_code(user, phone: str, code: str) -> bool:
    phone = normalize_phone(phone)
    row = SmsCode.objects.filter(
        phone=phone, code=code, purpose='verify', used=False,
        expires_at__gt=timezone.now(),
    ).order_by('-created_at').first()
    if not row:
        return False
    row.used = True
    row.save()
    user.phone = phone
    user.phone_verified = True
    user.save(update_fields=['phone', 'phone_verified'])
    return True
