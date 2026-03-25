import random

from CTFd.cache import cache
from CTFd.exceptions.email import (
    UserConfirmTokenInvalidException,
    UserResetPasswordTokenInvalidException,
)


def _generate_unique_code(prefix, length=6):
    """Generate a unique N-digit numeric code not currently active in cache."""
    for _ in range(50):
        code = str(random.randint(0, 10**length - 1)).zfill(length)
        if cache.get(f"{prefix}{code}") is None:
            return code
    return code


def generate_email_confirm_token(addr, timeout=1800):
    # Invalidate any previous code for this address
    old_code = cache.get(f"confirm_email_addr_{addr}")
    if old_code:
        cache.delete(f"confirm_email_{old_code}")
    code = _generate_unique_code("confirm_email_")
    cache.set(f"confirm_email_{code}", addr, timeout=timeout)
    cache.set(f"confirm_email_addr_{addr}", code, timeout=timeout)
    return code


def verify_email_confirm_token(code):
    addr = cache.get(f"confirm_email_{code}")
    if addr is None:
        raise UserConfirmTokenInvalidException
    return addr


def remove_email_confirm_token(code):
    addr = cache.get(f"confirm_email_{code}")
    if addr:
        cache.delete(f"confirm_email_addr_{addr}")
    cache.delete(f"confirm_email_{code}")


def generate_password_reset_token(addr, timeout=1800):
    # Invalidate any previous code for this address
    old_code = cache.get(f"reset_password_addr_{addr}")
    if old_code:
        cache.delete(f"reset_password_{old_code}")
    code = _generate_unique_code("reset_password_")
    cache.set(f"reset_password_{code}", addr, timeout=timeout)
    cache.set(f"reset_password_addr_{addr}", code, timeout=timeout)
    return code


def verify_reset_password_token(code):
    addr = cache.get(f"reset_password_{code}")
    if addr is None:
        raise UserResetPasswordTokenInvalidException
    return addr


def remove_reset_password_token(code):
    addr = cache.get(f"reset_password_{code}")
    if addr:
        cache.delete(f"reset_password_addr_{addr}")
    cache.delete(f"reset_password_{code}")
