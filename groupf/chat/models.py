from django.db import models
from django.conf import settings

# ==========================================
# メインモデル定義
# ==========================================

class ChatRoom(models.Model):
    name = models.CharField(max_length=100, blank=True, verbose_name="ルーム名")
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chat_rooms', verbose_name="参加者")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="最終更新日時")

    def __str__(self):
        return self.name or "チャットルーム"

class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_chat_messages')
    content = models.TextField(verbose_name="メッセージ内容")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
