"""Per-connection state machine.

Every WebSocket connection owns one Session. A client may only perform an
action that is legal in its current state, e.g. you cannot chat before you
have logged in and joined a room. Illegal events raise InvalidTransition.
"""
from .dfa import DFA

# States
CONNECTED, AUTHENTICATED, IN_ROOM, CLOSED = "CONNECTED", "AUTHENTICATED", "IN_ROOM", "CLOSED"
# Events (the DFA's input alphabet)
LOGIN, JOIN, SAY, LEAVE, QUIT = "login", "join", "say", "leave", "quit"

TRANSITIONS = {
    (CONNECTED, LOGIN): AUTHENTICATED,
    (AUTHENTICATED, JOIN): IN_ROOM,
    (IN_ROOM, SAY): IN_ROOM,
    (IN_ROOM, LEAVE): AUTHENTICATED,
    # a client can quit from any live state
    (CONNECTED, QUIT): CLOSED,
    (AUTHENTICATED, QUIT): CLOSED,
    (IN_ROOM, QUIT): CLOSED,
}

SESSION_DFA = DFA(TRANSITIONS, start=CONNECTED, accepting={CLOSED})


class Session:
    def __init__(self):
        self.state = SESSION_DFA.start
        self.name = None
        self.room = None

    def fire(self, event):
        """Advance the state machine or raise InvalidTransition."""
        self.state = SESSION_DFA.step(self.state, event)
        return self.state
