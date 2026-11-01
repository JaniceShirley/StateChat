"""Command lexer built as a DFA over character classes.

Grammar accepted for one input line:

    line  := text | "/" name (SPACE+ arg)* SPACE*
    name  := [a-z]+
    arg   := [A-Za-z0-9_-]+
    text  := any line that does not start with "/"

The DFA decides whether a line is a plain chat message, a well-formed
command, or malformed; tokens are emitted as the automaton leaves the
CMD / ARG states.
"""
from .dfa import DFA, InvalidTransition

# DFA states
START, TEXT, SLASH, CMD, GAP, ARG = "START", "TEXT", "SLASH", "CMD", "GAP", "ARG"

# Character classes (the DFA's input alphabet)
C_SLASH, C_LOWER, C_ARGCH, C_SPACE, C_OTHER = "slash", "lower", "argch", "space", "other"


def char_class(ch):
    if ch == "/":
        return C_SLASH
    if ch == " ":
        return C_SPACE
    if "a" <= ch <= "z":
        return C_LOWER
    if ch.isascii() and (ch.isalnum() or ch in "_-"):
        return C_ARGCH
    return C_OTHER


_T = {}
# START: a leading slash begins a command, anything else is plain text
_T[(START, C_SLASH)] = SLASH
for c in (C_LOWER, C_ARGCH, C_SPACE, C_OTHER):
    _T[(START, c)] = TEXT
# TEXT absorbs the rest of the line
for c in (C_SLASH, C_LOWER, C_ARGCH, C_SPACE, C_OTHER):
    _T[(TEXT, c)] = TEXT
# a command name is one or more lowercase letters
_T[(SLASH, C_LOWER)] = CMD
_T[(CMD, C_LOWER)] = CMD
_T[(CMD, C_SPACE)] = GAP
# arguments are separated by spaces
for c in (C_LOWER, C_ARGCH):
    _T[(GAP, c)] = ARG
    _T[(ARG, c)] = ARG
_T[(GAP, C_SPACE)] = GAP
_T[(ARG, C_SPACE)] = GAP

LEXER_DFA = DFA(_T, start=START, accepting={TEXT, CMD, GAP, ARG})


class LexError(Exception):
    pass


def tokenize(line):
    """Return ("text", line) or ("command", name, [args]); raise LexError."""
    line = line.rstrip("\r\n")
    state, buf, tokens = LEXER_DFA.start, "", []
    for pos, ch in enumerate(line):
        cls = char_class(ch)
        try:
            nxt = LEXER_DFA.step(state, cls)
        except InvalidTransition:
            raise LexError(f"unexpected {ch!r} at position {pos}") from None
        if nxt in (CMD, ARG):
            buf += ch
        elif state in (CMD, ARG):          # leaving a token
            tokens.append(buf)
            buf = ""
        state = nxt
    if state in (CMD, ARG):
        tokens.append(buf)
    if state not in LEXER_DFA.accepting:
        raise LexError("incomplete command")
    if state == TEXT:
        return ("text", line)
    return ("command", tokens[0], tokens[1:])
