import datetime as dt
from typing import Any

type JsonDict = dict[str, Any]
type RawTimeType = None | str | dt.date
type RawTimeIntervalType = tuple[RawTimeType, RawTimeType]
