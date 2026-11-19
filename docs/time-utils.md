# Time utilities

`sentinel_hub.time_utils` parses and serialises the timestamps and intervals used by the
[Catalog](catalog-api.md) and [Process](process-api.md) APIs. The public helpers are
importable from `sentinel_hub`.

- [Accepted inputs](#accepted-inputs)
- [parse_time](#parse_time)
- [parse_time_interval](#parse_time_interval)
- [serialize_time](#serialize_time)
- [filter_times](#filter_times)
- [is_valid_time](#is_valid_time)

## Accepted inputs

Wherever the library takes a `time` / `time_interval`, you can pass:

| Input | Interpreted as |
|---|---|
| `"2024-06-15"` | `2024-06-15T00:00:00` → `2024-06-15T23:59:59` |
| `"2024-06-15T10:30:00"` | that exact instant (start = end) |
| `("2024-06-01", "2024-06-30")` | `2024-06-01T00:00:00` → `2024-06-30T23:59:59` |
| `(datetime.date(...), datetime.datetime(...))` | dates expand to whole days, datetimes are kept |
| `(None, "2024-06-30")` or `("..", "2024-06-30")` | open start (where allowed) |

Timestamps without a timezone are treated as **UTC** when sent to the API.

## parse_time

```python
from sentinel_hub import parse_time

parse_time("2024-06-15")  # datetime.date(2024, 6, 15)
parse_time("2024-06-15T10:30:00")  # datetime.datetime(2024, 6, 15, 10, 30)
parse_time("2024-06-15", force_datetime=True)  # datetime.datetime(2024, 6, 15, 0, 0)
parse_time(None, allow_undefined=True)  # None
parse_time("2024-06-15T10:30:00+02:00", ignoretz=True)  # extra kwargs go to dateutil
```

## parse_time_interval

```python
from sentinel_hub import parse_time_interval

parse_time_interval("2024-06-15")
# (datetime(2024, 6, 15, 0, 0), datetime(2024, 6, 15, 23, 59, 59))

parse_time_interval(("2024-06-01", None), allow_undefined=True)
# (datetime(2024, 6, 1, 0, 0), None)
```

Raises `ValueError` if the start is after the end, or the input isn't a string / date or
a pair of them.

## serialize_time

Turns `date` / `datetime` (or an iterable of them) into ISO 8601 strings. `None` becomes `".."`.

```python
from sentinel_hub import serialize_time

serialize_time(datetime(2024, 6, 15, 10, 30))  # '2024-06-15T10:30:00'
serialize_time(datetime(2024, 6, 15, 10, 30), use_tz=True)  # '2024-06-15T10:30:00Z'
serialize_time((start, None), use_tz=True)  # ('2024-06-01T00:00:00Z', '..')
```

With `use_tz=True`, naive datetimes are assumed UTC; plain `date` objects raise `ValueError`.

## filter_times

Removes timestamps closer than `time_difference` to the previous kept one, keeping the
oldest of each cluster. Useful for collapsing tiles from the same satellite pass.

```python
import datetime as dt
from sentinel_hub import filter_times

filter_times(timestamps, dt.timedelta(hours=1))
```

Output is sorted and de-duplicated.

## is_valid_time

```python
from sentinel_hub import is_valid_time

is_valid_time("2024-06-15")  # True
is_valid_time("not a date")  # False
```

Also available (not re-exported): `sentinel_hub.time_utils.date_to_datetime(date, time=None)`.
