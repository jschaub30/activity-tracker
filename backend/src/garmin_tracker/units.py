"""Metric storage, imperial display (miles / feet)."""

from typing import Optional

METERS_PER_MILE = 1609.344
METERS_PER_FOOT = 0.3048


def m_to_mi(meters: Optional[float]) -> Optional[float]:
    if meters is None:
        return None
    return round(meters / METERS_PER_MILE, 2)


def m_to_ft(meters: Optional[float]) -> Optional[float]:
    if meters is None:
        return None
    return round(meters / METERS_PER_FOOT, 0)


def mi_to_m(miles: float) -> float:
    return miles * METERS_PER_MILE


def ft_to_m(feet: float) -> float:
    return feet * METERS_PER_FOOT
