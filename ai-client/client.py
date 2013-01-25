#!/usr/bin/env python
#
# This client connects to the centralized game server
# via websocket. After creating a new game on the game
# server, it spaws an AI subprocess called "ntris_ai."
# For each turn, this client passes in the current game
# state to a new instance of ntris_ai, waits ten seconds
# for a response, then kills the AI process and sends
# back the move list.
#

import traceback
import threading
import cherrypy
import config
import time
import json
import sys
import os

from ws4py.client.threadedclient import WebSocketClient
from subprocess import Popen, PIPE, STDOUT

# Remote server to connect to:
#SERVER_URL = 'http://ec2-107-20-18-153.compute-1.amazonaws.com/'
#WEBSOCKET_URL = 'ws://ec2-107-20-18-153.compute-1.amazonaws.com/ws'
SERVER_URL = 'http://localhost/'
WEBSOCKET_URL = 'ws://localhost/ws'

# Subprocess
LEFT_CMD = 'left'
RIGHT_CMD = 'right'
UP_CMD = 'up'
DOWN_CMD = 'down'
DROP_CMD = 'drop'
ROTATE_CMD = 'rotate'
VALID_CMDS = [LEFT_CMD, RIGHT_CMD, UP_CMD, DOWN_CMD, DROP_CMD, ROTATE_CMD]
AI_PROCESS_PATH = './ntris_ai'
AI_PROCESS_TIMEOUT = 10 # This is enforced server-side so don't change ;)

# Messaging protocol
CREATE_NEW_GAME_MSG = 'CREATE_NEW_GAME'
NEW_GAME_CREATED_MSG = 'NEW_GAME_CREATED'
AWAITING_NEXT_MOVE_MSG = 'AWAITING_NEXT_MOVE'
SUBMIT_MOVE_MSG = 'SUBMIT_MOVE'
DO_NOT_RECONNECT = 1001

# Printing utilities
colorred = "\033[01;31m{0}\033[00m"
colorgrn = "\033[1;36m{0}\033[00m"

# Logging AI actions for debug webserver
LOGGING_DIR = os.path.join(os.getcwd(), 'history')

class Command(object):
    def __init__(self, cmd):
        self.cmd = cmd
        self.process = None

    def run(self, timeout):
        cmds = []
        def target():
            self.process = Popen(self.cmd, stdout=PIPE, shell=True)
            for line in iter(self.process.stdout.readline, ''):
                line = line.rstrip('\n')
                if line not in VALID_CMDS:
                    print line # Forward debug output to terminal
                elif line != DROP_CMD:
                    cmds.append(line)

        thread = threading.Thread(target=target)
        thread.start()

        thread.join(timeout)
        if thread.is_alive():
            print colorred.format('Terminating process')
            self.process.terminate()
            thread.join()
        print colorgrn.format('commands received: %s' % cmds)
        return cmds

class SubscriberThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        ws = Subscriber(WEBSOCKET_URL)
        ws.connect()

class GameStateLogger(object):
    log_dir = None
    turn_num = 0

    def __init__(self, game_id):
        self.log_dir = os.path.join(LOGGING_DIR, '%s_%s' % (game_id, int(time.time())))
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def log_game_state(self, game_state):
        fname = os.path.join(self.log_dir, 'state%s' % (self.turn_num,))
        with open(fname, 'w+') as f:
            f.write(game_state)

    def log_ai_move(self, move_list):
        fname = os.path.join(self.log_dir, 'move%s' % (self.turn_num,))
        with open(fname, 'w+') as f:
            f.write(move_list)
        self.turn_num += 1

def catch_exceptions(f):
    def wrapped(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception, e:
            print traceback.format_exc()
    return wrapped

class Subscriber(WebSocketClient):
    game_id = -1
    logger = None

    @catch_exceptions
    def handshake_ok(self):
        self._th.start()
        self._th.join()

    @catch_exceptions
    def send_msg(self, msg):
        msg['team_name'] = config.team_name
        msg['team_password'] = config.team_password
        msg['entry_mode'] = entry_mode
        self.send(json.dumps(msg))

    @catch_exceptions
    def opened(self):
        msg = {
            'type' : CREATE_NEW_GAME_MSG,
        }
        self.send_msg(msg)

    @catch_exceptions
    def received_message(self, msg):
        msg = json.loads(str(msg))
        if msg['type'] == NEW_GAME_CREATED_MSG:
            if 'game_id' in msg:
                self.game_id = msg['game_id']
                self.logger = GameStateLogger(self.game_id)
                print colorgrn.format("New game started at %sgame.html#%s" % (SERVER_URL, msg['game_id']))
            else:
                print colorgrn.format("Waiting for competition to begin")
        elif msg['type'] == AWAITING_NEXT_MOVE_MSG:
            ai_arg = json.dumps(msg['game_state'])
            if self.logger:
                self.logger.log_game_state(ai_arg)
            command = Command(AI_PROCESS_PATH + (" '%s'" % ai_arg))
            ai_cmds = command.run(timeout=AI_PROCESS_TIMEOUT)
            if self.logger:
                self.logger.log_ai_move(json.dumps(ai_cmds))
            response = {
                'type' : SUBMIT_MOVE_MSG,
                'move_list' : ai_cmds,
            }
            self.send_msg(response)
        else:
            print colorred.format("Received unsupported message type")

    def closed(self, code, reason=None):
        print colorred.format("Connection to server closed. Code=%s, Reason=%s" % (code, reason))

        if code != DO_NOT_RECONNECT and entry_mode == 'compete':
            # Attempt to re-connect
            ws = Subscriber(WEBSOCKET_URL)
            ws.connect()
        else:
            os._exit(0)

if __name__ == '__main__':
    if config.team_name == "TEAM_NAME_HERE" or config.team_password == "TEAM_PASSWORD_HERE":
        print colorred.format("Please specify a team name and password in config.py")
        sys.exit(0)

    if len(sys.argv) != 2:
        print colorred.format("Usage: client.py [compete|test]")
        sys.exit(0)

    if sys.argv[1] != "compete" and sys.argv[1] != "test":
        print colorred.format("Usage: client.py [compete|test]")
        sys.exit(0)

    entry_mode = sys.argv[1]

    subscriber = SubscriberThread()
    subscriber.daemon = True
    subscriber.start()

    while (True):
        # For some reason, KeyboardInterrupts are only allowed
        # when the websocket subscriber is on a background thread.
        time.sleep(1)
