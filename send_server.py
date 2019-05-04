import os.path
#import telepot
import telegram
import time
from pathlib import Path
import grpc
from concurrent import futures
import send_message_pb2
import send_message_pb2_grpc

import logging, logging.handlers
script_dir = os.path.dirname(os.path.realpath(__file__))
log = logging.getLogger()
log.setLevel(logging.DEBUG)
logHandler = logging.handlers.TimedRotatingFileHandler(os.path.join(script_dir, 'logs', 'send_server.log'), 'D', 1, 5)
logFormat = logging.Formatter('%(levelname)-5s - %(filename)s:%(lineno)d - %(message)s')
logHandler.setFormatter(logFormat)
logHandler.setLevel(logging.DEBUG)
log.addHandler(logHandler)



class SendMessageService(send_message_pb2_grpc.SendMessageServicer):
    def __init__(self):
        self.config = self.get_config()
        #self.bot = telepot.Bot("%s:%s" % (self.config['account'], self.config['secret']))
        self.bot = telegram.Bot("%s:%s" % (self.config['account'], self.config['secret']))

    def get_config(self):
        home = str(Path.home())
        cfg = os.path.join(home, ".config", "bot_service.rc")
        if not os.path.exists(cfg) or not os.path.isfile(cfg):
            raise FileNotFoundError("config file ~/.config/bot_service.rc not found")

        config = {}
        with open(cfg) as input:
            for line in input:
                line = line.strip()
                eqidx = line.find("=")
                if eqidx < 0 or line[:eqidx].strip() == "" or line[eqidx+1:].strip() == "":
                    continue
                config[line[:eqidx].strip()] = line[eqidx+1:].strip()

        return config

    def SendMessage(self, request, context):
        chat_id = request.chatId.id
        text = request.text.text
        parse_mode = request.parseMode
        try:
            parseMode = {
                    send_message_pb2.Request.PlainText: None,
                    send_message_pb2.Request.Markdown: "markdown",
                    send_message_pb2.Request.HTML: "html"
                    }[parse_mode]
            #sent = self.bot.sendMessage(chat_id=chat_id, text=text, parse_mode=parseMode)
            sent = self.bot.send_message(chat_id=chat_id, text=text, parse_mode=parseMode)
            return send_message_pb2.Response(success=(sent is not None))
        except:
            return send_message_pb2.Response(success=False)

    def serve(self):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
        send_message_pb2_grpc.add_SendMessageServicer_to_server(self, server)
        server.add_insecure_port('%s:%s' % (self.config['bindip'], self.config['bindport']))
        server.start()

        try:
            while True:
                time.sleep(60 * 60)
        except KeyboardInterrupt:
            server.stop(grace=True)

if __name__ == "__main__":
    SendMessageService().serve()


