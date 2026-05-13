__author__ = 'ryan'
__version__ = '2.0.0'

__all__ = []

try:
    from image_match.elasticsearch_driver_es7 import SignatureES7  # noqa: F401
    __all__.append('SignatureES7')
except ImportError:
    pass

try:
    from image_match.elasticsearch_driver_es8 import SignatureES8  # noqa: F401
    __all__.append('SignatureES8')
except ImportError:
    pass

try:
    from image_match.qdrant_driver import SignatureQdrant  # noqa: F401
    __all__.append('SignatureQdrant')
except ImportError:
    pass
