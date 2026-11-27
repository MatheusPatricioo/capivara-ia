"""The moon's phase on a given date, from the length of its cycle."""

from datetime import UTC, datetime, timedelta

SYNODIC_MONTH_DAYS = 29.530588853
"""Days from one new moon to the next, on average."""
KNOWN_NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=UTC)


def moon_phase(moment: datetime) -> float:
    """From 0 (new moon) through 0.25 (first quarter), 0.5 (full) and 0.75 (last quarter)
    to just under 1. A moment without a time zone is taken as local time.

    Real cycles run a few hours early or late around the average, so this is close, not exact.
    """
    elapsed = moment.astimezone(UTC) - KNOWN_NEW_MOON
    cycles = elapsed / timedelta(days=SYNODIC_MONTH_DAYS)
    return cycles % 1.0
