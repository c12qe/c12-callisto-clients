import importlib.util

spec = importlib.util.find_spec("pytket")
if spec is None:
    raise ImportError(
        "Pytket is required to use this module. Install it with: pip install c12_callisto_clients[pytket]"
    )


from .extensions.callisto.backends.callisto import CallistoBackend, CallistoRunningError  # noqa: E402

__all__ = ["CallistoBackend", "CallistoRunningError"]
