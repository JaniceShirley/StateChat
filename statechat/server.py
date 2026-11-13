"""WebSocket chat server whose protocol is enforced by two DFAs.

  * lexer.py   - decides what each incoming line is (text / command / malformed)
  * session.py - decides whether that action is legal in the client's state
"""
import asyncio
import os
import sys

import websockets

from .dfa import InvalidTransition
from .lexer import LexError, tokenize
from .session import (AUTHENTICATED, CLOSED, CONNECTED, IN_ROOM, JOIN, LEAVE,
                      LOGIN, QUIT, SAY, SESSION_DFA, Session)

HELP = "Commands: /login <name>, /join <room>, /leave, /quit. Plain text chats once you are in a room."
ARG_COUNT = {LOGIN: 1, JOIN: 1, LEAVE: 0, QUIT: 0}


class ChatServer:
    def __init__(self):
        self.users = {}   # name -> websocket
        self.rooms = {}   # room -> set of websockets

    async def broadcast(self, room, message, skip=None):
        for peer in list(self.rooms.get(room, ())):
            if peer is not skip:
                try:
                    await peer.send(message)
                except websockets.ConnectionClosed:
                    # The peer dropped mid-broadcast; its own handler cleans it up.
                    pass

    def _leave_room(self, ws, sess):
        members = self.rooms.get(sess.room)
        if members:
            members.discard(ws)
            if not members:
                del self.rooms[sess.room]

    async def handle_line(self, ws, sess, raw):
        try:
            token = tokenize(raw)
        except LexError as e:
            return await ws.send(f"ERROR: malformed input ({e}). {HELP}")

        if token[0] == "text":
            event, args = SAY, [token[1]]
        else:
            _, event, args = token
            if event not in ARG_COUNT:
                return await ws.send(f"ERROR: unknown command /{event}. {HELP}")
            if len(args) != ARG_COUNT[event]:
                return await ws.send(f"ERROR: /{event} takes {ARG_COUNT[event]} argument(s)")

        # Ask the state machine first, so illegal actions have no side effects.
        try:
            SESSION_DFA.step(sess.state, event)
        except InvalidTransition:
            return await ws.send(f"ERROR: cannot {event} while {sess.state}")

        if event == LOGIN:
            if args[0] in self.users:
                return await ws.send(f"ERROR: name {args[0]!r} is taken")
            self.users[args[0]] = ws
            sess.name = args[0]
            sess.fire(event)
            await ws.send(f"OK: logged in as {sess.name} [{sess.state}]")
        elif event == JOIN:
            sess.room = args[0]
            self.rooms.setdefault(sess.room, set()).add(ws)
            sess.fire(event)
            await ws.send(f"OK: joined #{sess.room} [{sess.state}]")
            await self.broadcast(sess.room, f"* {sess.name} joined", skip=ws)
        elif event == SAY:
            await self.broadcast(sess.room, f"{sess.name}: {args[0]}")
        elif event == LEAVE:
            self._leave_room(ws, sess)
            await self.broadcast(sess.room, f"* {sess.name} left", skip=ws)
            sess.fire(event)
            await ws.send(f"OK: left #{sess.room} [{sess.state}]")
            sess.room = None
        elif event == QUIT:
            await self.disconnect(ws, sess)
            await ws.send("OK: bye")

    async def disconnect(self, ws, sess):
        if sess.state == IN_ROOM:
            self._leave_room(ws, sess)
            await self.broadcast(sess.room, f"* {sess.name} disconnected", skip=ws)
        if sess.name and self.users.get(sess.name) is ws:
            del self.users[sess.name]
        sess.state = CLOSED

    async def handler(self, ws):
        sess = Session()
        await ws.send(f"Welcome [{sess.state}]. {HELP}")
        try:
            async for raw in ws:
                await self.handle_line(ws, sess, raw)
                if sess.state == CLOSED:
                    break
        except websockets.ConnectionClosed:
            pass
        finally:
            if sess.state != CLOSED:
                await self.disconnect(ws, sess)
            await ws.close()


async def serve(host=None, port=8765):
    host = host or os.environ.get("HOST", "localhost")
    server = ChatServer()
    async with websockets.serve(server.handler, host, port):
        print(f"StateChat listening on ws://{host}:{port}")
        await asyncio.Future()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    try:
        asyncio.run(serve(port=port))
    except KeyboardInterrupt:
        pass
