try:
    import qiskit
except ImportError:
    raise ImportError(
        "Qiskit is required to use this module. "
        "Install it with: pip install c12_callisto_clients[qiskit]"
    )

from . import c12sim_provider
from . import c12sim_job
from . import c12sim_backend
