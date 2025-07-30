from c12_callisto_clients.api import *
from c12_callisto_clients.user_configs import *

try:
    import qiskit

    HAS_QISKIT = True
    from c12_callisto_clients.qiskit import *
except ImportError:
    HAS_QISKIT = False


try:
    import pytket

    HAS_PYTKET = True
    from c12_callisto_clients.pytket import *
    from c12_callisto_clients.pytket.extensions import *
    from c12_callisto_clients.pytket.extensions.callisto import *

except ImportError:
    HAS_PYTKET = False


def check_qiskit_installed():
    """Check if qiskit extra is installed."""
    if not HAS_QISKIT:
        raise ImportError(
            "Qiskit support is not installed. "
            "Install it with: pip install c12_callisto_clients[qiskit]"
        )


def check_pytket_installed():
    """Check if pytket extra is installed."""
    if not HAS_PYTKET:
        raise ImportError(
            "Pytket support is not installed. "
            "Install it with: pip install c12_callisto_clients[pytket]"
        )


__all__ = ["HAS_QISKIT", "HAS_PYTKET", "check_qiskit_installed", "check_pytket_installed"]
