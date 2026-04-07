"""Backward-compatibility shim for image_match.elasticsearch_driver.

Use SignatureES7 or SignatureES8 directly instead:

    from image_match.elasticsearch_driver_es7 import SignatureES7
    from image_match.elasticsearch_driver_es8 import SignatureES8
"""
import warnings

from image_match.elasticsearch_driver_es7 import SignatureES7
from image_match.elasticsearch_driver_es8 import SignatureES8


def SignatureES(*args, **kwargs):
    """Deprecated. Use SignatureES7 or SignatureES8 explicitly."""
    warnings.warn(
        "SignatureES is deprecated. Use SignatureES7 (for ES 7.x) or "
        "SignatureES8 (for ES 8.x) from their respective modules.",
        DeprecationWarning,
        stacklevel=2,
    )
    return SignatureES7(*args, **kwargs)


__all__ = ['SignatureES', 'SignatureES7', 'SignatureES8']
