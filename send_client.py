import os.path, threading, configparser, grpc
from pathlib import Path
import send_message_pb2, send_message_pb2_grpc, logging
log = logging.getLogger(__file__)

class SendClient:

    def __init__(self):
        self.config = None
        self.connected = False
        self.stub = None
        self.update_config()

    def update_config(self):
        home = str(Path.home())
        cfg = os.path.join(home, '.config', 'bot_clients.rc')
        if not os.path.exists(cfg) or not os.path.isfile(cfg):
            raise FileNotFoundError('config file ~/.config/bot_clients.rc not found')
        config = configparser.ConfigParser()
        config.read(cfg)
        self.config = config

    def send(self, text, parse_mode='plaintext', profile='default'):
        if not self.connected:
            channel = grpc.insecure_channel('%s:%s' % (self.config['default']['ip'], self.config['default']['port']))
            self.stub = send_message_pb2_grpc.SendMessageStub(channel)
            self.connected = True
        chatId = send_message_pb2.ChatId(id=int(self.config[profile]['chat_id']))
        text = send_message_pb2.Text(text=text)
        parseMode = {'P':send_message_pb2.Request.PlainText, 
         'M':send_message_pb2.Request.Markdown, 
         'H':send_message_pb2.Request.HTML}[parse_mode[0].upper()]
        resp = self.stub.SendMessage(send_message_pb2.Request(chatId=chatId, text=text, parseMode=parseMode))
        return resp.success


if __name__ == '__main__':
    client = SendClient()
    for i in range(1):
        client.send('你好朱镕基！')
        import time
        time.sleep(1)
# okay decompiling pycache/send_client.cpython-36.pyc
