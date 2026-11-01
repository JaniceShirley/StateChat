import asyncio

import websockets

from statechat.server import ChatServer


async def _recv(ws):
    return await asyncio.wait_for(ws.recv(), timeout=2)


async def _scenario():
    chat = ChatServer()
    async with websockets.serve(chat.handler, "localhost", 0) as srv:
        port = srv.sockets[0].getsockname()[1]
        uri = f"ws://localhost:{port}"
        async with websockets.connect(uri) as a, websockets.connect(uri) as b:
            await _recv(a); await _recv(b)  # welcome banners

            # chatting before login is rejected by the state machine
            await a.send("hello?")
            assert "cannot say while CONNECTED" in await _recv(a)

            await a.send("/login alice")
            assert "logged in as alice" in await _recv(a)
            await a.send("/join dev")
            assert "joined #dev" in await _recv(a)

            await b.send("/login alice")                      # duplicate name
            assert "taken" in await _recv(b)
            await b.send("/login bob")
            await _recv(b)
            await b.send("/join dev")
            await _recv(b)
            assert "bob joined" in await _recv(a)

            await a.send("hi bob")
            assert await _recv(a) == "alice: hi bob"
            assert await _recv(b) == "alice: hi bob"

            await b.send("/join other")                       # already in a room
            assert "cannot join while IN_ROOM" in await _recv(b)
            await b.send("/jion x")
            assert "unknown command" in await _recv(b)

            await b.send("/leave")
            assert "left #dev" in await _recv(b)
            assert "bob left" in await _recv(a)
            await b.send("/quit")
            assert "bye" in await _recv(b)


def test_end_to_end_chat():
    asyncio.run(_scenario())
