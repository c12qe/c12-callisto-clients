import importlib.util

spec = importlib.util.find_spec("qiskit")
if spec is None:
    raise ImportError(
        "Qiskit is required to use this module. Install it with: pip install c12_callisto_clients[qiskit]"
    )

from . import c12sim_backend, c12sim_job, c12sim_provider  # noqa: E402

__all__ = ["c12sim_backend", "c12sim_job", "c12sim_provider"]
