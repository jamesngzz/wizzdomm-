import json
from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Accept first to minimize handshake failures
        await self.accept()
        try:
            await self.channel_layer.group_add("notifications", self.channel_name)
        except Exception:
            # If group add fails (e.g., Redis hiccup), close gracefully
            await self.close()

    async def disconnect(self, code):
        try:
            await self.channel_layer.group_discard("notifications", self.channel_name)
        except Exception:
            pass

    async def notify(self, event):
        await self.send(text_data=json.dumps(event.get("payload", {})))


