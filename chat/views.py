from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponseForbidden
from listings.models import Listing
from accounts.notifications import notify
from .models import Conversation, Message
from .support_bot import get_or_create_support_conversation, send_support_bot_reply


def _detect_attachment_type(uploaded_file) -> str:
    ct = getattr(uploaded_file, 'content_type', '') or ''
    name = (uploaded_file.name or '').lower()
    if ct.startswith('video/') or name.endswith(('.mp4', '.webm', '.mov')):
        return Message.AttachmentType.VIDEO
    if ct.startswith('image/') or name.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
        return Message.AttachmentType.IMAGE
    return Message.AttachmentType.FILE


def _notify_chat_message(conv, sender, preview: str):
    recipient = conv.other_user(sender)
    if conv.is_support and sender == conv.seller:
        return
    title = 'Новое сообщение'
    if conv.is_support:
        title = 'Ответ поддержки'
        link = f'/messages/support/'
    else:
        link = f'/messages/{conv.pk}/'
        title = f'Сообщение по «{conv.listing.title}»' if conv.listing else title
    notify(recipient, 'message', title, preview[:200], link)


@login_required
def conversation_list(request):
    convs = Conversation.objects.filter(
        Q(buyer=request.user) | Q(seller=request.user),
        is_support=False,
    ).select_related('listing', 'buyer', 'seller').annotate(
        unread=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user) & Q(messages__is_deleted=False))
    )
    support = Conversation.objects.filter(buyer=request.user, is_support=True).annotate(
        unread=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user) & Q(messages__is_deleted=False))
    ).first()
    return render(request, 'chat/index.html', {
        'title': 'Сообщения',
        'conversations': convs,
        'support_conv': support,
    })


@login_required
def support_chat(request):
    conv = get_or_create_support_conversation(request.user)
    conv = Conversation.objects.select_related('buyer', 'seller').get(pk=conv.pk)
    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        attachment = request.FILES.get('attachment')
        if body or attachment:
            msg = Message(conversation=conv, sender=request.user, body=body)
            if attachment:
                msg.attachment = attachment
                msg.attachment_type = _detect_attachment_type(attachment)
                msg.attachment_name = attachment.name
            msg.save()
            conv.last_msg_at = timezone.now()
            conv.save(update_fields=['last_msg_at'])
            if body:
                send_support_bot_reply(conv, body)
        return redirect('chat:support')
    conv.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    return render(request, 'chat/show.html', {
        'title': 'Поддержка',
        'conv': conv,
        'listing': None,
        'chat_messages': conv.messages.select_related('sender').all(),
        'is_support': True,
    })


@login_required
def conversation_start(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    if listing.user == request.user:
        return redirect('listings:detail', slug=listing.slug)
    conv, _ = Conversation.objects.get_or_create(
        listing=listing, buyer=request.user, seller=listing.user, is_support=False,
    )
    listing.chat_clicks += 1
    listing.save(update_fields=['chat_clicks'])
    return redirect('chat:detail', pk=conv.pk)


@login_required
def conversation_detail(request, pk):
    conv = get_object_or_404(
        Conversation.objects.select_related('listing', 'buyer', 'seller'),
        pk=pk, is_support=False,
    )
    if request.user not in (conv.buyer, conv.seller):
        return render(request, 'errors/403.html', {'title': 'Доступ запрещён'}, status=403)
    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        attachment = request.FILES.get('attachment')
        if body or attachment:
            msg = Message(conversation=conv, sender=request.user, body=body)
            if attachment:
                msg.attachment = attachment
                msg.attachment_type = _detect_attachment_type(attachment)
                msg.attachment_name = attachment.name
            msg.save()
            conv.last_msg_at = timezone.now()
            conv.save(update_fields=['last_msg_at'])
            preview = body or f'Вложение: {attachment.name}' if attachment else ''
            _notify_chat_message(conv, request.user, preview)
        return redirect('chat:detail', pk=pk)
    conv.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    return render(request, 'chat/show.html', {
        'title': f'Чат — {conv.listing.title}' if conv.listing else 'Чат',
        'conv': conv,
        'listing': conv.listing,
        'chat_messages': conv.messages.select_related('sender').all(),
        'is_support': False,
    })


@login_required
@require_POST
def message_edit(request, pk):
    msg = get_object_or_404(Message, pk=pk, sender=request.user, is_deleted=False)
    if msg.attachment:
        return JsonResponse({'ok': False, 'error': 'Нельзя редактировать сообщение с вложением'}, status=400)
    body = request.POST.get('body', '').strip()
    if not body:
        return JsonResponse({'ok': False, 'error': 'Пустое сообщение'}, status=400)
    msg.body = body
    msg.edited_at = timezone.now()
    msg.save(update_fields=['body', 'edited_at'])
    return JsonResponse({'ok': True, 'body': body, 'edited': True})


@login_required
@require_POST
def message_delete(request, pk):
    msg = get_object_or_404(Message, pk=pk, sender=request.user)
    msg.is_deleted = True
    msg.body = ''
    msg.save(update_fields=['is_deleted', 'body'])
    return JsonResponse({'ok': True})

