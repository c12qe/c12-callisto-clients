import importlib.util

from c12_callisto_clients.api import client, configs, exceptions
from c12_callisto_clients.user_configs import UserConfigs

qiskit_spec = importlib.util.find_spec("qiskit")
if qiskit_spec is not None:
    from c12_callisto_clients.qiskit import c12sim_backend, c12sim_job, c12sim_provider

pytket_spec = importlib.util.find_spec("pytket")
if pytket_spec is not None:
    from c12_callisto_clients.pytket import CallistoBackend, CallistoRunningError


def check_qiskit_installed():
    """Check if qiskit extra is installed."""
    if qiskit_spec is None:
        raise ImportError("Qiskit support is not installed. Install it with: pip install c12_callisto_clients[qiskit]")


def check_pytket_installed():
    """Check if pytket extra is installed."""
    if pytket_spec is None:
        raise ImportError("Pytket support is not installed. Install it with: pip install c12_callisto_clients[pytket]")


__all__ = [
    "CallistoBackend",
    "CallistoRunningError",
    "UserConfigs",
    "c12sim_backend",
    "c12sim_job",
    "c12sim_provider",
    "check_pytket_installed",
    "check_qiskit_installed",
    "client",
    "configs",
    "exceptions",
]
