import re
from django.db import models
from django.conf import settings


class Conversation(models.Model):
    listing = models.ForeignKey(
        'listings.Listing', on_delete=models.CASCADE,
        null=True, blank=True,
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='buyer_conversations',
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='seller_conversations',
    )
    is_support = models.BooleanField(default=False)
    last_msg_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-last_msg_at', '-created_at']

    def other_user(self, user):
        return self.seller if user == self.buyer else self.buyer


class Message(models.Model):
    class AttachmentType(models.TextChoices):
        IMAGE = 'image', 'Фото'
        VIDEO = 'video', 'Видео'
        FILE = 'file', 'Файл'

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField(blank=True)
    attachment = models.FileField(upload_to='chat/', blank=True, null=True)
    attachment_type = models.CharField(max_length=10, choices=AttachmentType.choices, blank=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    @property
    def is_editable(self):
        return not self.is_deleted and not self.sender_id == 0
