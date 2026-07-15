from __future__ import annotations

import pytest
from talaqi.identity.csrf import CsrfService
from talaqi.platform import ApiError


def test_csrf_requires_cookie_header_match_and_server_hash() -> None:
    service = CsrfService("test-session-secret")
    raw = service.issue()
    stored = service.hash(raw)
    service.verify(raw, raw, stored)
    for cookie, header in ((None, raw), (raw, None), (raw, "wrong")):
        with pytest.raises(ApiError) as error:
            service.verify(cookie, header, stored)
        assert error.value.code == "csrf_failed"


def test_csrf_is_session_secret_bound() -> None:
    first = CsrfService("first-session-secret")
    second = CsrfService("second-session-secret")
    raw = first.issue()
    with pytest.raises(ApiError):
        second.verify(raw, raw, first.hash(raw))
