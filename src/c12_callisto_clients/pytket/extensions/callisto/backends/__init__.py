try:
    import pytket
except ImportError:
    raise ImportError(
        "Pytket is required to use this module. "
        "Install it with: pip install c12_callisto_clients[pytket]"
    )

from .callisto import CallistoBackend
