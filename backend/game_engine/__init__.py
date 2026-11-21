"""Pure game rules for Telephone Doodle.

This package holds the rules and nothing else: plain dataclasses and functions
with no FastAPI, no sockets, no clock and no database. `rooms` calls into it;
it never calls back out. All randomness is injected as a `random.Random` so a
game can be replayed exactly in tests.
"""
