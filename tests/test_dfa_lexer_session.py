import pytest

from statechat.dfa import DFA, InvalidTransition
from statechat.lexer import LexError, tokenize
from statechat.session import (AUTHENTICATED, CLOSED, CONNECTED, IN_ROOM, JOIN,
                               LEAVE, LOGIN, QUIT, SAY, Session)


def test_generic_dfa_even_number_of_ones():
    t = {("E", "0"): "E", ("E", "1"): "O", ("O", "0"): "O", ("O", "1"): "E"}
    d = DFA(t, "E", {"E"})
    assert d.accepts("1010") and not d.accepts("100") and d.accepts("")
    assert not d.accepts("12")  # undefined symbol is rejected


def test_lexer_plain_text():
    assert tokenize("hello there, how are you?") == ("text", "hello there, how are you?")


def test_lexer_commands():
    assert tokenize("/login alice") == ("command", "login", ["alice"])
    assert tokenize("/join room_1") == ("command", "join", ["room_1"])
    assert tokenize("/leave") == ("command", "leave", [])
    assert tokenize("/join   dev-team  ") == ("command", "join", ["dev-team"])


@pytest.mark.parametrize("bad", ["/", "/Login bob", "/login bob!", "/join a/b", "/1x"])
def test_lexer_rejects_malformed_commands(bad):
    with pytest.raises(LexError):
        tokenize(bad)


def test_session_happy_path():
    s = Session()
    assert s.state == CONNECTED
    assert s.fire(LOGIN) == AUTHENTICATED
    assert s.fire(JOIN) == IN_ROOM
    assert s.fire(SAY) == IN_ROOM
    assert s.fire(LEAVE) == AUTHENTICATED
    assert s.fire(QUIT) == CLOSED


@pytest.mark.parametrize("events", [[SAY], [JOIN], [LOGIN, SAY], [LOGIN, LOGIN], [LOGIN, JOIN, JOIN], [LOGIN, LEAVE]])
def test_session_rejects_illegal_order(events):
    s = Session()
    with pytest.raises(InvalidTransition):
        for e in events:
            s.fire(e)


def test_closed_is_terminal():
    s = Session()
    s.fire(QUIT)
    for e in (LOGIN, JOIN, SAY, LEAVE, QUIT):
        with pytest.raises(InvalidTransition):
            s.fire(e)
