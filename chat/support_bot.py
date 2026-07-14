import re
from django.utils import timezone
from .models import Message, Conversation


FAQ_RULES = [
    (r'доставк|курьер|получ', 'Доставка: курьер, самовывоз или транспортная компания. Срок и стоимость уточняйте у продавца в чате.'),
    (r'возврат|обмен|гарант', 'Возврат и гарантия зависят от продавца — смотрите условия в объявлении или спросите в чате с продавцом.'),
    (r'оплат|кошел|карт|плат', 'Оплата: банковская карта, кошелёк MarketPlace или безопасная сделка (эскроу). Пополнить кошелёк можно в разделе «Кошелёк».'),
    (r'модерац|одобр|публик', 'Новые объявления проверяются автоматически в течение ~30 секунд. Если отклонено — исправьте название, описание или фото.'),
    (r'ищу|заявк|не наш', 'Раздел «Ищу»: оставьте заявку при пустом поиске. Продавцы предложат товары — уведомление придёт в профиль.'),
    (r'отзыв|оценк|рейтинг', 'Отзыв можно оставить только после успешной покупки (заказ со статусом «Завершён» или «Доставлен»).'),
    (r'вериф|подтвержд|email|телефон', 'Подтвердите email и телефон в профиле — код придёт в консоль сервера (тестовый режим).'),
    (r'продав|кабинет|объявлен', 'Чтобы продавать: в профиле переключитесь в режим «Продавец», затем «+ Объявление».'),
    (r'привет|здравств|добр', 'Здравствуйте! Я помощник MarketPlace. Спросите про доставку, оплату, модерацию, раздел «Ищу» или отзывы.'),
    (r'помощ|поддерж|проблем', 'Опишите проблему подробнее. Если нужен оператор — оставьте email в профиле, мы свяжемся.'),
]


def get_support_user():
    from accounts.models import User
    user, created = User.objects.get_or_create(
        username='support',
        defaults={
            'email': 'support@marketplace.local',
            'first_name': 'Поддержка',
            'is_staff': True,
        },
    )
    if created:
        user.set_unusable_password()
        user.save()
    return user


def get_or_create_support_conversation(user):
    support = get_support_user()
    conv = Conversation.objects.filter(buyer=user, is_support=True).first()
    if not conv:
        conv = Conversation.objects.create(
            buyer=user, seller=support, is_support=True, listing=None,
        )
        Message.objects.create(
            conversation=conv,
            sender=support,
            body='Здравствуйте! Я помощник MarketPlace. Спросите про доставку, оплату, модерацию или раздел «Ищу».',
        )
        conv.last_msg_at = timezone.now()
        conv.save(update_fields=['last_msg_at'])
    return conv


def support_reply(user_text: str) -> str:
    low = (user_text or '').lower().strip()
    if not low:
        return 'Напишите вопрос — например: «Как работает доставка?» или «Как оставить отзыв?»'
    for pattern, answer in FAQ_RULES:
        if re.search(pattern, low):
            return answer
    return (
        'Не нашёл точный ответ. Попробуйте спросить про: доставку, оплату, модерацию, раздел «Ищу», отзывы. '
        'Или напишите «помощь» — подскажу дальше.'
    )


def send_support_bot_reply(conversation, user_message: str):
    support = get_support_user()
    reply = support_reply(user_message)
    Message.objects.create(conversation=conversation, sender=support, body=reply)
    conversation.last_msg_at = timezone.now()
    conversation.save(update_fields=['last_msg_at'])
