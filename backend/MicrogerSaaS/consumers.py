import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class LogConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add('log_group', self.channel_name)
        print('Logger Websocket connection established')

    async def log_message(self, message):
        await self.send_json({
            'type': 'websocket.log',
            'log': message['message'],
            'color': message['color'],
        })

    async def disconnect(self, close_code):
        print('Logger Websocket Disconnected')


class ProgressConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add('progress_group', self.channel_name)
        print('Progress Websocket connection established')

    async def progress(self, percentage):
        await self.send_json({
            'type': 'websocket.progress',
            'percentage': percentage['percentage']
        })

    async def disconnect(self, close_code):
        print('Progress Websocket Disconnected')