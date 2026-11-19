import pytest

from sentinel_hub.download.rate_limit import SHRateLimit


def test_first_request_can_start_immediately() -> None:
    rate_limit = SHRateLimit()
    assert rate_limit.register_next() == 0


def test_consecutive_requests_are_spaced_by_minimum_wait_time() -> None:
    rate_limit = SHRateLimit(num_processes=2, minimum_wait_time=10)

    assert rate_limit.register_next() == 0
    assert rate_limit.register_next() == pytest.approx(20, abs=0.5)


def test_wait_time_is_capped() -> None:
    rate_limit = SHRateLimit(
        num_processes=100, minimum_wait_time=10, maximum_wait_time=5
    )

    assert rate_limit.wait_time == 5


@pytest.mark.parametrize("retry_after", [2000, "2000", "2000.0"])
def test_update_uses_retry_header_in_milliseconds(retry_after: int | str) -> None:
    rate_limit = SHRateLimit(minimum_wait_time=0)

    rate_limit.update({SHRateLimit.RETRY_HEADER: retry_after}, default=0)

    assert rate_limit.register_next() == pytest.approx(2, abs=0.5)


def test_update_falls_back_to_default() -> None:
    rate_limit = SHRateLimit(minimum_wait_time=0)

    rate_limit.update({}, default=3000)

    assert rate_limit.register_next() == pytest.approx(3, abs=0.5)


def test_update_without_wait_does_not_delay() -> None:
    rate_limit = SHRateLimit(minimum_wait_time=0)

    rate_limit.update({}, default=0)

    assert rate_limit.register_next() == 0
