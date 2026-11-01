"""A small, generic deterministic finite automaton (DFA) engine.

Both the connection state machine (session.py) and the command lexer
(lexer.py) are built on this one class, so every transition in the system
is an explicit entry in a transition table.
"""
from __future__ import annotations


class InvalidTransition(Exception):
    """Raised when no transition is defined for (state, symbol)."""

    def __init__(self, state, symbol):
        super().__init__(f"no transition from {state!r} on {symbol!r}")
        self.state = state
        self.symbol = symbol


class DFA:
    def __init__(self, transitions, start, accepting):
        # transitions: {(state, symbol): next_state}
        self.transitions = dict(transitions)
        self.start = start
        self.accepting = frozenset(accepting)

    def step(self, state, symbol):
        try:
            return self.transitions[(state, symbol)]
        except KeyError:
            raise InvalidTransition(state, symbol) from None

    def run(self, symbols, state=None):
        """Feed a sequence of symbols; return the final state."""
        state = self.start if state is None else state
        for s in symbols:
            state = self.step(state, s)
        return state

    def accepts(self, symbols):
        try:
            return self.run(symbols) in self.accepting
        except InvalidTransition:
            return False

    def to_mermaid(self):
        """Export the transition table as a Mermaid state diagram."""
        lines = ["stateDiagram-v2", f"    [*] --> {self.start}"]
        for (src, sym), dst in sorted(self.transitions.items(), key=str):
            lines.append(f"    {src} --> {dst}: {sym}")
        for a in sorted(self.accepting, key=str):
            lines.append(f"    {a} --> [*]")
        return "\n".join(lines)
