# pylint: disable=import-error
from typing import Optional, List, Dict, Any
import numpy as np
import networkx as nx

from qiskit.providers.jobstatus import JobStatus
from qiskit.result.models import ExperimentResult, ExperimentResultData
from qiskit.result import Result as QiskitResult

from qat.core.gate_set import GateSet
from qat.lang import RX, RZ, RY, ISWAP, SWAP, CNOT as CX
from qat.core import HardwareSpecs
from qat.core import Topology
from qat.core.wrappers.result import Result as WResult
from qat.comm.shared.ttypes import Job, Batch, ProcessingType
from qat.core.qpu.qpu import QPUHandler
from qat.interop.qiskit.providers import (
    generate_qlm_list_results,
    job_to_qiskit_circuit,
    generate_qlm_result,
    _wrap_results,
)


from c12_callisto_clients.user_configs import UserConfigs
from c12_callisto_clients.api.client import Request
from c12_callisto_clients.api.exceptions import ApiError

GATE_SET_MAP: Dict[str, Any] = {
    "RX": RX,
    "RY": RY,
    "RZ": RZ,
    "ISWAP": ISWAP,
    "CX": CX,
    "SWAP": SWAP,
}
BACKEND_VERSION: str = "1.0.0"


def _parse_result_data(result_data, shots) -> List[ExperimentResult]:
    """
    Parse result dictionary.
    """

    if result_data is None:
        return []
    if "counts" not in result_data or "statevector" not in result_data:
        raise ValueError("Error getting the information from the system.")

    # Getting the counts & statevector of the circuit after execution
    counts = result_data["counts"]
    statevector = _convert_json_to_np_array(result_data["statevector"])

    # Additional mid-circuit data (if any)
    additional_data = {}
    if "states" in result_data:
        states = result_data["states"]

        if "density_matrix" in states and "statevector" in states:
            dms = states["density_matrix"]
            svs = states["statevector"]

            for key in svs.keys():
                svs[key] = _convert_json_to_np_array(svs[key])

            for key in dms.keys():
                dms[key] = _convert_json_to_np_matrix(dms[key])

            additional_data = {**dms, **svs}

    experiment = ExperimentResult(
        shots=shots,
        success=True,
        status="FINISHED",
        data=ExperimentResultData(counts=counts, statevector=statevector, **additional_data),
    )

    return [experiment]


def _convert_json_to_np_matrix(data) -> np.ndarray:
    """Function to convert json string data to numpy matrix"""
    matrix = []
    dm = np.array(data)
    for i in range(len(dm)):
        matrix.append(_convert_json_to_np_array(dm[i]))
    return np.array(matrix)


def _convert_json_to_np_array(data) -> np.ndarray:
    """Function to convert json string data to numpy array"""
    array = np.asarray(data)
    array = np.array(list(map(lambda item: complex(item), array)))
    return array


class BaseCallistoProvider(QPUHandler):
    """
    Base class for the Callisto backend to QPU handler. It contains the common
    functionalities for the Callisto backend to QPU handler (both sync & async).
    """

    _backend = None
    _callisto_specs = None

    def __init__(
        self, user_configs: UserConfigs, name: Optional[str] = "c12sim-iswap", plugins=None
    ):
        """
        Constructor for the CallistoBackendToQPU class.
        It is a QPUHandler that is going to use the CallistoSimProvider to get the backend

        :param user_configs: UserConfigs object that contains the token for the access to the remote server
        :param name: string representing the name of the backend. it is optional and if not provide
                    it has a default value of c12sim-iswap
        :param plugins:  Any plugins to be added (c.f qat.core documentation)
        """
        super().__init__(plugins)
        self._name = name
        self._user_configs = user_configs

        self._request = Request(
            self._user_configs.token, self._user_configs.verbose
        )  # Request object for the API calls
        self.set_backend(name, self._user_configs.token, self._user_configs.verbose)

    def _set_backend_specs(self):
        """
        Function to set the backend specifications for the Callisto backend.
        :return:
        """

        basis_gates = self._backend["basis_gates"]
        basis_gate_set_map = {
            gate.upper(): GATE_SET_MAP[gate.upper()]
            for gate in basis_gates
            if gate.upper() in GATE_SET_MAP
        }

        basis_gate_set = GateSet(basis_gate_set_map)

        max_nqubits = self._backend["n_qubits"]
        # Create an array of every possible combination of the qubits that is a current Topology of the system
        topology_arr = []
        for i in range(max_nqubits):
            for j in range(i + 1, max_nqubits):
                topology_arr.append((i, j))
                topology_arr.append((j, i))

        graph = nx.Graph(topology_arr)
        topology = Topology.from_nx(graph)

        self._callisto_specs = HardwareSpecs(
            nbqbits=max_nqubits,
            topology=topology,
            gateset=basis_gate_set,
            processing_types=[ProcessingType.SAMPLE],
            description="Callisto specs",
            meta_data={
                "Date": "2024-09-27 10:50:00",
                "max_shots": self._backend["max_shots"],
                "max_circuits": self._backend["max-circuits"],
            },
        )

    def set_backend(self, backend_name: str, token: str, verbose: bool = False):
        """
        Function to set the backend for the C12BackendToQPU class.

        :param backend_name: string representing the name of the backend
        :param token: string representing the token for the access to the remote server
        :param verbose: boolean representing the verbosity of the output (for the request object)
        """
        self._request = Request(token, verbose)

        try:
            backends = self._request.get_backends()
            if backend_name is not None:
                backends = [item for item in backends if (backend_name in item["backend_name"])]

            if len(backends) == 0:
                raise NotImplementedError(f"No backend available with a name: {backend_name}")

            self._backend = backends[0]
            self._set_backend_specs()

        except PermissionError as p_err:
            raise PermissionError(
                "Permission error occurred during the access to the remote server"
            ) from p_err
        except ApiError as api_err:
            raise ApiError(
                "Unexpected error happened during the accessing the remote server"
            ) from api_err

    @property
    def backend(self):
        return self._backend

    def get_specs(self):
        """
        Returns the backend specifications.
        """
        return self._callisto_specs


class CallistoBackendToQPU(BaseCallistoProvider):
    """
    Callisto backend to myQLM QPU Handler
    Backend accepts the QLM circuit and returns the QLM results
    """

    def _submit_batch(self, qlm_batch):
        """
        Submits a Batch object to execute on a Callisto backend.
        """
        if self.backend is None:
            raise ValueError("Backend cannot be None")

        if isinstance(qlm_batch, Job):
            qlm_batch = Batch(jobs=[qlm_batch])

        qiskit_circuits = []
        qiskit_results = []

        for qlm_job in qlm_batch.jobs:
            circuit = job_to_qiskit_circuit(qlm_job, only_sampling=True)
            qiskit_circuits.append(circuit)

            job_uuid, _ = self._request.start_job(
                qasm_str=circuit.qasm(),
                shots=qlm_job.nbshots,
                result="counts",
                backend_name=self.backend["backend_name"],
            )
            qiskit_result = self._wait_for_completion(job_uuid, shots=qlm_job.nbshots)
            qiskit_results.append(qiskit_result)

        batch_results = [generate_qlm_list_results(res) for res in qiskit_results]
        new_results = []
        for result in batch_results:
            new_results.append(WResult.from_thrift(result[0]))
        return _wrap_results(qlm_batch, new_results, 100000)

    def submit_job(self, qlm_job):
        """
        Submits a Job to execute on a Callisto backend.

        Args:
            qlm_job: :class:`~qat.core.Job` object

        Returns:
            :class:`~qat.core.Result` object
        """
        if self._backend is None:
            raise ValueError("Backend cannot be None")

        circuit = job_to_qiskit_circuit(qlm_job)
        qasm = circuit.qasm()

        shots = qlm_job.nbshots or self._backend["max_shots"]

        try:
            job_uuid, _ = self._request.start_job(
                qasm_str=qasm,
                shots=shots,
                result="counts",
                backend_name=self.backend["backend_name"],
            )
            qlm_job.job_id = job_uuid
        except ApiError as err:
            raise ConnectionRefusedError(
                f"Error starting a job on the remote server {err}"
            ) from err

        qiskit_result = self._wait_for_completion(job_uuid, shots)
        result_qlm = generate_qlm_result(qiskit_result)
        return result_qlm

    def _wait_for_completion(
        self,
        job_id: str,
        shots: int,
        timeout: Optional[float] = None,
        wait: float = 5,
    ) -> QiskitResult:
        """
        Wrapper: waiting for the job completion.

        :param timeout: Seconds until the exception is triggered. None for indefinitely.
        :param wait: The wait time in seconds between queries.
        :return: True if the final job status matches one of the required states.
        """

        try:
            job_result = self._request.get_job_result(
                job_id,
                output_data="counts,statevector,states,density_matrix",
                timeout=timeout,
                wait=wait,
            )

            return QiskitResult(
                backend_name=self._backend["backend_name"],
                backend_version=BACKEND_VERSION,
                job_id=job_id,
                qobj_id=0,
                success=job_result["status"] == JobStatus.DONE,
                results=_parse_result_data(job_result["results"], shots),
                status=job_result["status"],
            )
        except ApiError as err:
            raise RuntimeError(
                "Unexpected error happened during the accessing the remote server"
            ) from err
        except TimeoutError as err2:
            raise TimeoutError("Timeout occurred while waiting for job execution") from err2


class CallistoJob:
    """
    Wrapper around Callisto job
    """

    _request: Optional[Request] = None

    def __init__(self, qlm_batch, job_uuid, max_shots, request):
        """
        Args:
            qlm_batch: :class:`~qat.core.Batch` or :class:`~qat.core.Job` object.
                    If a QLM Job object is given, it will be converted in a QLM
                    Batch object
            async_job: Qiskit job instance derived from JobV1.
                    Result of a previous asynchronous execution of qlm_batch
            max_shots: Maximal number of shots allowed by the Backend
        """
        self._job_uuid = job_uuid
        self._max_shots = max_shots
        self._request = request
        if isinstance(qlm_batch, Job):
            self._qlm_batch = Batch(jobs=[qlm_batch])
        else:
            self._qlm_batch = qlm_batch

    def job_id(self):
        """Returns the job's ID."""
        return self._job_uuid

    def status(self):
        """Returns the job status."""
        return self._request.get_job_status(self.job_id())

    def result(self):
        """
        Returns the result if available.

        Returns:
            :class:`~qat.core.Result` object or
            :class:`~qat.core.BatchResult` object
            if the batch submitted contains several jobs
        """
        print(f"result {self.status()}")
        if self.status() not in ["finished", "cancelled", "error"]:
            return None

        try:
            job_result = self._request.get_job_result(
                self.job_id(),
                output_data="counts,statevector,states,density_matrix",
            )
            result = generate_qlm_list_results(
                QiskitResult(
                    backend_name="backend_name",
                    backend_version="0.0.1",
                    job_id=self.job_id(),
                    qobj_id=0,
                    success=job_result["status"] == JobStatus.DONE,
                    results=_parse_result_data(job_result["results"], self._max_shots),
                    status=job_result["status"],
                )
            )
        except ApiError as err:
            raise RuntimeError(
                "Unexpected error happened during the accessing the remote server"
            ) from err
        except TimeoutError as err2:
            raise TimeoutError("Timeout occurred while waiting for job execution") from err2

        return result

    def cancel(self):
        """
        Attempts to cancel the job. We are currently not supporting this option.
        """
        print(f"Unable to cancel job with ID: {self.job_id()}")
        return False

    def dump(self, file_name):
        """
        Dumps the :class:`~qat.core.Batch` object used for creating the job into a
        binary file. This file should later be used with AsyncBackendToQPU's
        :func:`~qat.interop.qiskit.AsyncBackendToQPU.retrieve_job`.

        Args:
            file_name: Name of the binary file to create
        """
        if isinstance(self._qlm_batch.meta_data, dict):
            self._qlm_batch.meta_data["job_id"] = self.job_id()
        else:
            self._qlm_batch.meta_data = {"job_id": self.job_id()}

        self._qlm_batch.dump(file_name)


# Add class for the async backend to QPU handler


class AsyncCallistoBackendToQPU(BaseCallistoProvider):

    def submit_job(self, qlm_job):
        """
        Submits a QLM job to be executed on the previously
        selected backend, if no backends are chosen an exception is raised.

        Args:
            qlm_job: :class:`~qat.core.Job` object to be executed

        Returns:
            A :class:`~qat.interop.qiskit.QiskitJob` object with the same
            interface as a job derived from JobV1 for the user to have
            information on their job execution
        """
        if self.backend is None:
            raise ValueError("Backend cannot be None")

        circuit = job_to_qiskit_circuit(qlm_job, only_sampling=True)
        qasm = circuit.qasm()

        shots = qlm_job.nbshots or self._backend["max_shots"]

        try:
            job_uuid, _ = self._request.start_job(
                qasm_str=qasm,
                shots=shots,
                result="counts",
                backend_name=self.backend["backend_name"],
            )
        except ApiError as err:
            raise ConnectionRefusedError(
                f"Error starting a job on the remote server {err}"
            ) from err

        return CallistoJob(qlm_job, job_uuid, self.backend["max_shots"])

    def submit(self, qlm_batch):
        """
        Submits a QLM batch of jobs and returns the corresponding QiskitJob.

        Args:
            qlm_batch: :class:`~qat.core.Batch` or :class:`~qat.core.Job`.
                    If a single job is provided, a batch is created
                    from this job.
        Returns:
            :class:`~qat.interop.qiskit.QiskitJob` object with the same
            interface as a job derived from JobV1 for the user to have
            information on their job execution
        """
        if self.backend is None:
            raise ValueError("Backend cannot be None")

        if isinstance(qlm_batch, Job):
            qlm_batch = Batch(jobs=[qlm_batch])

        qiskit_circuits = []
        job_uuids = []
        for qlm_job in qlm_batch.jobs:
            circuit = job_to_qiskit_circuit(qlm_job, only_sampling=True)
            qiskit_circuits.append(circuit)

            job_uuid, _ = self._request.start_job(
                qasm_str=circuit.qasm(),
                shots=qlm_job.nbshots,
                result="counts",
                backend_name=self.backend["backend_name"],
            )
            job_uuids.append(job_uuid)

        return CallistoJob(qlm_batch, job_uuids, self.backend["max_shots"], self._request)

    def retrieve_job(self, file_name):
        """
        Retrieves a QiskitJob from a binary file in which the QLM Batch object
        - from which the QiskitJob has been created - has been dumped.

        Args:
            file_name: Name of the binary file

        Returns:
            :class:`~qat.interop.qiskit.QiskitJob` object
        """
        qlm_batch = Batch.load(file_name)
        async_job = self.backend.retrieve_job(qlm_batch.meta_data["job_id"])
        return CallistoJob(qlm_batch, async_job, self.backend["max_shots"], self._request)


if __name__ == "__main__":

    import os
    import time
    from qat.lang.AQASM import Program, H

    user_auth_token = os.getenv("C12_TOKEN", "3ae88c08-29cf-456e-b284-e01add5ca833")
    configs = UserConfigs.parse_obj({"token": user_auth_token})

    qpu = CallistoBackendToQPU(configs, name="c12sim-iswap")

    prog = Program()
    reg = prog.qalloc(1)
    prog.apply(H, reg[0])

    job = prog.to_circ().to_job(nbshots=10024)

    jobs = [job, job]

    print("Selected backend:", qpu.backend)
    results = qpu.submit(job)
    print(results)

    print("=== Specs ===")
    print(qpu.get_specs())

    print("---- ASYNC")
    qpu = AsyncCallistoBackendToQPU(configs, name="c12sim-iswap")

    prog = Program()
    reg = prog.qalloc(1)
    prog.apply(H, reg[0])

    job = prog.to_circ().to_job(nbshots=10024)

    jobs = [job, job]

    print("Selected backend:", qpu.backend)
    async_job = qpu.submit(job)
    print(async_job.status())
    time.sleep(30)
    print(async_job.status())
    time.sleep(30)
    print(async_job.status())
    result = async_job.result()
    print(result)

    print("=== Specs ===")
    print(qpu.get_specs())
