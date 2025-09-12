# apps/interactions/consumers.py
import json
import traceback

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.prefetch import GenericPrefetch

from .models import Chat, Message, User, Appointment, Cooperation
from .serializers import MessageSerializer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat_group_name = f'chat_{self.chat_id}'
        self.user = self.scope['user']

        # Kiểm tra xem user có quyền truy cập phòng chat này không
        if not self.user.is_authenticated or not await self.user_can_access_chat():
            await self.close()
            return

        # Tham gia vào group của phòng chat
        await self.channel_layer.group_add(
            self.chat_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Rời khỏi group
        await self.channel_layer.group_discard(
            self.chat_group_name,
            self.channel_name
        )

    # Nhận tin nhắn từ WebSocket
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            print("--- DEBUG BACKEND 1: Received raw JSON:", text_data_json)

            # Lấy các thông tin từ payload
            message_content = text_data_json.get('message', '')
            message_type = text_data_json.get('message_type', 'TEXT')  # Mặc định là TEXT
            metadata = text_data_json.get('metadata', None)
            print(f"--- DEBUG BACKEND 2: Parsed data -> Type: {message_type}, Metadata: {metadata}")

            # Chỉ xử lý nếu có nội dung hoặc metadata
            if not message_content and not metadata:
                return

            # Lưu tin nhắn vào database
            new_message = await self.save_message(
                content=message_content,
                message_type=message_type,
                metadata=metadata
            )

            # Dùng hàm serialize thủ công để tránh lỗi context
            message_data = await self.build_message_dict(new_message)

            # Gửi tin nhắn đến group của phòng chat
            await self.channel_layer.group_send(
                self.chat_group_name,
                {
                    'type': 'chat_message',
                    'message': message_data
                }
            )
        except Exception as e:
            # Ghi log lỗi và đóng kết nối một cách an toàn
            print(f"Error in receive method for chat {self.chat_id}: {e}")
            traceback.print_exc()
            await self.close(code=4000)  # Gửi mã lỗi tùy chỉnh

    # Nhận tin nhắn từ group và gửi xuống WebSocket cho client
    async def chat_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))

    # --- Các hàm tương tác với Database ---
    @database_sync_to_async
    def user_can_access_chat(self):
        try:
            return Chat.objects.filter(pk=self.chat_id, participants=self.user).exists()
        except Exception:
            return False

    @database_sync_to_async
    def save_message(self, content, message_type, metadata):
        chat = Chat.objects.get(pk=self.chat_id)

        message_kwargs = {
            'chat': chat,
            'sender': self.user,
            'content': content,
            'message_type': message_type,
        }

        # Xử lý logic cho các tin nhắn có đối tượng liên kết
        if metadata and isinstance(metadata, dict) and 'object_type' in metadata and 'object_id' in metadata:
            try:
                print(f"--- DEBUG BACKEND 3: Trying to get ContentType for model: '{metadata['object_type'].lower()}'")

                content_type = ContentType.objects.get(model=metadata['object_type'].lower())

                print(f"--- DEBUG BACKEND 4: Found ContentType: {content_type}")

                # Kiểm tra xem object có tồn tại không trước khi liên kết
                if content_type.model_class().objects.filter(pk=metadata['object_id']).exists():
                    message_kwargs['content_type'] = content_type
                    message_kwargs['object_id'] = metadata['object_id']
                else:
                    print(f"--- DEBUG BACKEND: FAILED - Object with ID {metadata['object_id']} for model {content_type.model} does not exist.")

            except ContentType.DoesNotExist:
                print(f"Warning: Invalid object_type '{metadata['object_type']}' received.")
                pass

        message = Message.objects.create(**message_kwargs)

        chat.last_message_timestamp = message.created_date
        chat.save(update_fields=['last_message_timestamp'])
        return message

    @database_sync_to_async
    def build_message_dict(self, message: Message) -> dict:
        """
        Hàm này thay thế cho DRF Serializer, tạo ra một dictionary
        an toàn để gửi qua JSON.
        """
        # Đây là cách an toàn nhất để tránh lỗi context của DRF trong consumer.
        # Chúng ta sẽ build lại context một cách thủ công nếu cần.
        # Tuy nhiên, để đơn giản, chúng ta sẽ không dùng DRF serializer ở đây.

        linked_object_data = None
        if message.content_type and message.object_id:
            linked_obj = message.linked_object

            # Dùng một context giả chỉ chứa user, vì một số serializer con có thể cần
            # (mặc dù cách tốt nhất là sửa các serializer con đó để không cần request)
            fake_context = {'user': self.user}

            if isinstance(linked_obj, Appointment):
                from .serializers import LinkedAppointmentSerializer
                linked_object_data = {
                    "type": "appointment",
                    "data": LinkedAppointmentSerializer(linked_obj, context=fake_context).data
                }
            elif isinstance(linked_obj, Cooperation):
                from .serializers import LinkedCooperationSerializer
                linked_object_data = {
                    "type": "cooperation",
                    "data": LinkedCooperationSerializer(linked_obj, context=fake_context).data
                }

        return {
            'id': message.id,
            'sender_id': message.sender.id,
            'sender_name': message.sender.get_full_name() or message.sender.username,
            'content': message.content,
            'created_date': message.created_date.isoformat(),
            'message_type': message.message_type,
            'linked_object_data': linked_object_data
        }