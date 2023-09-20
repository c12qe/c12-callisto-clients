""" Pytket Backend for C12 Callisto quantum emulator """
# pylint: disable = no-name-in-module
# pylint: disable = import-error
from typing import Optional, List, Union, Sequence, Dict
import numpy as np


from pytket import OpType, Circuit
from pytket.passes import (
    BasePass,
    DecomposeBoxes,
    SimplifyInitial,
    SequencePass,
    FullPeepholeOptimise,
    SynthesiseTket,
    auto_rebase_pass,
)
from pytket.predicates import (
    Predicate,
    MaxNQubitsPredicate,
    NoClassicalBitsPredicate,
    NoMidMeasurePredicate,
    NoClassicalControlPredicate,
    NoSymbolsPredicate,
)
from pytket.utils import OutcomeArray
from pytket.qasm import circuit_to_qasm_str
from pytket.utils.results import KwargTypes
from pytket.architecture import FullyConnected
from pytket.backends import Backend, CircuitStatus, StatusEnum, CircuitNotRunError
from pytket.backends.backendresult import BackendResult
from pytket.backends.backendinfo import BackendInfo
from pytket.backends.resulthandle import _ResultIdTuple, ResultHandle

from c12_callisto_clients.api.client import Request, ApiError


# Mapping between our way of describing the basis gates and pytket's way
gate_mapping = {
    "rx": OpType.Rx,
    "ry": OpType.Ry,
    "rz": OpType.Rz,
    "crx": OpType.CRx,
    "iswap": OpType.SWAP,
}


class CallistoRunningException(Exception):
    """Callisto Exception"""

    pass


class CallistoBackend(Backend):
    """A pytket Backing wrapper class for the C12 emulator"""

    _access_token: str = None  # Token used to access the C12 API
    _backend_info: Optional[BackendInfo] = None

    _supports_state = True  # Callisto supports retrieval of the statevector
    _supports_density_matrix = True  # Callisto supports retrieval of density matrix
    _supports_unitary = False  # Callisto does not support unitary retrieval
    _supports_counts = True  # Callisto supports retrieval of the counts
    _persistent_handles = False

    @staticmethod
    def get_available_devices(token: str):
        """Get all available backends for the device"""
        request = Request(token, verbose=False)

        try:
            backends = request.get_backends()
        except PermissionError as permission_error:
            raise CallistoRunningException(
                "You do not have a permission to access the resource!"
            ) from permission_error
        except ApiError as api_err:
            raise CallistoRunningException(
                "An error occured during the retrieval of the available backends"
            ) from api_err

        return backends

    def __init__(self, backend_name: str, token: str, verbose: bool = False):
        super().__init__()

        self._backend_name = backend_name
        self._access_token = token
        self._request = Request(self._access_token, verbose)

    @property
    def backend_info(self) -> Optional[BackendInfo]:
        """
        Getter for obtaining the information about a backend. If the backend is not set, it calls
        ptivate _get_info method to retrieve the information.
        :return: BackendInfo or None
        """
        if self._backend_info is None:
            self._backend_info = self._get_info(self._backend_name)
        return self._backend_info

    def _get_info(self, backend_name: str) -> Optional[BackendInfo]:
        """
        Get the BackendInfo instance for a given backend_name.
        :param backend_name: string representing the backend name for the instance.
        :return: BackendInfo or None
        """
        if backend_name is None or self._request is None:
            return None

        try:
            backends = self._request.get_backends()
        except PermissionError as permission_error:
            raise CallistoRunningException(
                "You do not have a permission to access the resource!"
            ) from permission_error
        except ApiError as api_err:
            raise CallistoRunningException(
                "An error occured during the retrieval of the available backends"
            ) from api_err

        for backend in backends:
            if backend_name in backend["backend_name"]:
                return self._dict_to_info(backend)

        return None

    @staticmethod
    def _dict_to_info(data: dict) -> BackendInfo:
        """
        Method to translate from the dictionary that is obtained from the API call to
         the instance of the BackendInfo class.
        :param data: data obtained from the API
        :return: BackendInfo
        """
        name = data["backend_name"]
        n_qubits = data["n_qubits"]
        gate_set: List[str] = data["basis_gates"]

        return BackendInfo(
            name=name,
            gate_set=gate_set,
            architecture=FullyConnected(n_qubits),
            device_name="C12 emulator",
            version="1.0.0",
        )

    @property
    def required_predicates(self) -> List[Predicate]:
        """
        Predicates represent the requirements that the circuit needs to satisfy to be able
        to be run on one backend.
        This is a property of the class (inherited from the parent, Backend class).
        It is a list of the instances of the
        classes whose parent class is a Predicate class.
        :return: list of the predicates
        """
        predicates = [
            NoMidMeasurePredicate(),  # No mid circuit measurements
            MaxNQubitsPredicate(self.backend_info.n_nodes),  # Max number of qubits
            NoClassicalControlPredicate(),  # No classical control statements
            NoSymbolsPredicate(),  # No symbols
        ]

        return predicates

    def default_compilation_pass(self, optimisation_level: int = 1) -> BasePass:
        """
        Abstract method from the Backend class. A suggested compilation pass that will, if possible, produce an
         equivalent circuit suitable for running on this backend.

        :param optimisation_level:
        :return:
        """
        assert optimisation_level in range(3)

        seq = [DecomposeBoxes()]  # Decompose boxes into basic gates
        if optimisation_level == 1:
            seq.append(
                SynthesiseTket()
            )  # Optimises and converts all gates to CX, TK1 and Phase gates.
        elif optimisation_level == 2:
            seq.append(SynthesiseTket())
            seq.append(SimplifyInitial())  # Simplify the circuit using knowledge of qubit state.
        else:
            seq.append(SynthesiseTket())
            seq.append(SimplifyInitial())
            seq.append(
                FullPeepholeOptimise()
            )  # Deep optimisation and performing a peephole optimisation

        return SequencePass(seq)

    @property
    def _result_id_type(self) -> _ResultIdTuple:
        """
        The way a job will be represented. Each job will have unique UUID identifier.
        :return: tuple (str, str) - (job_uuid, backend_name)
        """
        return (str,)

    @staticmethod
    def job_id(handle: ResultHandle) -> str:
        """
        Returns a job id from the handle.
        Object to store multidimensional identifiers for a circuit sent to a backend for execution.
        :param handle: ResultHandle of a job
        :return: UUID of the job
        """
        return handle[0]

    @staticmethod
    def get_circuit_status(status: str) -> StatusEnum:
        """
        Method to transform C12's job statuses to the TKET's StatusEnum values.
        :param status: status of the job
        :return: corresponding StatusEnum value

        :raise: CallistoRunningException
        """
        if status == "QUEUED":
            return StatusEnum.QUEUED
        if status == "RUNNING":
            return StatusEnum.RUNNING
        if status == "FINISHED":
            return StatusEnum.COMPLETED
        if status == "ERROR":
            return StatusEnum.ERROR
        if status == "CANCELLED":
            return StatusEnum.CANCELLED

        raise CallistoRunningException(f"Status not found {status}")

    def circuit_status(self, handle: ResultHandle) -> CircuitStatus:
        """
        Method to get the status of the running job if it takes too much time to execute.
        :param handle: job handle
        :return: CircuitStatus
        """
        self._check_handle_type(handle)  # Check if a handle (result) is proper
        job_uuid = self.job_id(handle)

        if self._request is None:
            raise RuntimeError(f"Unable to retrieve circuit status for handle {handle}")

        status = self._request.get_job_status(job_uuid)

        if status is None:
            raise CircuitNotRunError(handle)

        status = self.get_circuit_status(status.upper().strip())

        if status == StatusEnum.COMPLETED:
            self.get_result(handle)  # Get results if the job is finished
            return CircuitStatus(status)

        if status in [StatusEnum.ERROR, StatusEnum.COMPLETED]:
            error_message: str = self.get_error_message(handle)
            return CircuitStatus(status, error_message)

        return CircuitStatus(status)

    def process_circuits(
        self,
        circuits: Sequence[Circuit],
        n_shots: Optional[Union[int, Sequence[int]]] = None,
        valid_check: bool = True,
        **kwargs: KwargTypes,
    ) -> List[ResultHandle]:
        """
         Method that is called to run the circuit on the backend. It accepts a list of the instances of the Circuit
          class and a corresponding list of shots.

        Internally it calls process_circuit method.

        :param circuits: circuits to be run on the backend
        :param n_shots: number of shots for each circuit (it can be different)
        :param valid_check: if we are verifying the predicates
        :param kwargs: additional arguments

        :returns: ResultHandle list
        """
        circuits = list(circuits)
        handles = []
        n_shots_list = Backend._get_n_shots_as_list(
            n_shots,
            len(circuits),
            optional=False,
        )

        if valid_check:
            self._check_all_circuits(circuits)

        count = 0
        for circuit in circuits:
            try:
                handles.append(self.process_circuit(circuit, n_shots_list[count]))
            except CallistoRunningException as error:
                print(f"The circuit {circuit} wasn't run successfully. {error}")
            count = count + 1

        return handles

    def process_circuit(
        self,
        circuit: Circuit,
        n_shots: Optional[int] = None,
        valid_check: bool = True,
        **kwargs: KwargTypes,
    ) -> ResultHandle:
        """
        Run a single circuit.
        """
        if valid_check:
            self._check_all_circuits([circuit])

        n_shots = 1024 if n_shots is None else n_shots
        result_type = "counts,statevector,density_matrix"
        ini_noise = kwargs.get("ininoise", False)
        physical_params = kwargs.get("physical_params", None)

        try:
            job_uuid, _ = self._request.start_job(
                qasm_str=circuit_to_qasm_str(circuit),
                shots=n_shots,
                result=result_type,
                backend_name=self._backend_name,
                ini_noise=ini_noise,
                physical_params=physical_params,
            )

        except ApiError as api_err:
            raise CallistoRunningException("Error starting a job") from api_err

        handle = ResultHandle(job_uuid)
        self._cache[handle] = dict()

        return handle

    @staticmethod
    def _convert_json_to_np_matrix(data) -> np.ndarray:
        """Function to convert json string data to numpy matrix"""
        matrix = []
        density_matrix = np.array(data)
        for i in range(len(density_matrix)):
            matrix.append(CallistoBackend._convert_json_to_np_array(density_matrix[i]))
        return np.array(density_matrix)

    @staticmethod
    def _convert_json_to_np_array(data) -> np.ndarray:
        """Function to convert json string data to numpy array"""
        array = np.asarray(data)
        array = np.array(list(map(lambda item: complex(item), array)))
        return array

    def _convert_result(self, data: dict) -> BackendResult:
        """
        Method to convert the C12 results to the Tket BackendResult class.
        :param data:
        :return:
        """
        data = data["results"]
        if "counts" not in data or "statevector" not in data:
            raise CallistoRunningException("Result is in a wrong format")

        counts = data["counts"]
        statevector = self._convert_json_to_np_array(data["statevector"])
        shots = []
        for key, value in counts.items():
            shot = [np.uint8(val) for val in key]
            shot.reverse()
            # NOTE: the reverse() is important as the order of the bits for the Qiskit (C12's emulator is based on
            # the Qiskit library).
            # State vector order is -> 00, 01, 10, 11 ->big-endian fashion BE, while Qiskit uses little-endian
            # way -> 11, 10, 01, 00
            for _ in range(value):
                shots.append(shot)

        outcome_array = OutcomeArray.from_readouts(np.array(shots))
        density_matrix = self._convert_json_to_np_matrix(data["density_matrix"])
        return BackendResult(state=statevector, shots=outcome_array, density_matrix=density_matrix)

    def get_error_message(self, handle: ResultHandle) -> Optional[str]:
        """
        Method to get an error message if the job has failed its execution.
        :param handle: job handle
        :return: error message or None
        """
        job_id = handle[0]
        data = self._request.get_job_result(job_id)
        return data["errors"] if "errors" in data else None

    def get_result(self, handle: ResultHandle, **kwargs: KwargTypes) -> BackendResult:
        """
        Get the results of the job with a given handle
        """
        try:
            return super().get_result(handle)
        except CircuitNotRunError:  # if the job hasn't been started, run it
            timeout = kwargs.get("timeout", 60)
            wait = kwargs.get("wait", 5)
            job_id = handle[0]

            data = self._retrieve_job(job_id, timeout=timeout, wait=wait)

            status = self.get_circuit_status(data["status"])

            if status == StatusEnum.ERROR:
                raise CallistoRunningException(
                    f"Error during the circuit execution {data['errors']}"
                )

            backend_result = self._convert_result(data)
            self._update_cache_result(handle, {"result": backend_result})
            return backend_result

    def _retrieve_job(
        self,
        jobid: str,
        result_type: str = "counts,statevector,density_matrix",
        timeout: Optional[int] = None,
        wait: Optional[int] = None,
    ) -> Dict:
        """Get the results from the server"""
        if self._request is None or self._backend_name is None:
            raise RuntimeError("Backend client is not set")

        data = self._request.get_job_result(jobid, result_type, timeout, wait)
        if data is None:
            raise RuntimeError(f"Unable to retrieve job {jobid}")

        return data

    def rebase_pass(self) -> BasePass:
        """A single compilation pass that when run converts all gates in a Circuit to an OpType supported by the
        Backend (ignoring architecture constraints)."""
        return auto_rebase_pass(self.backend_info.gate_set)

    def _update_cache_result(self, handle: ResultHandle, result: BackendResult) -> None:
        """update the results"""
        if handle in self._cache:
            self._cache[handle].update(result)
        else:
            self._cache[handle] = result
