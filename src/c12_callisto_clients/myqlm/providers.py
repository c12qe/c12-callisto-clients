# pylint: disable=import-error
from typing import Optional, List
import numpy as np

from qiskit.providers.jobstatus import JobStatus
from qiskit.result.models import ExperimentResult, ExperimentResultData
from qiskit.result import Result as QiskitResult

from qat.core.wrappers.result import Result as WResult
from qat.comm.shared.ttypes import Job, Batch
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


# Callisto backend to myQLM QPU Handler
# Backend accepts the QLM circuit and returns the QLM results
class CallistoBackendToQPU(QPUHandler):

    _backend = None

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

            job_uuid, transpiled_qasm = self._request.start_job(
                qasm_str=circuit.qasm(),
                shots=qlm_job.nbshots,
                result="counts",
                backend_name=self.backend["backend_name"],
            )
            qiskit_result = self._wait_for_completion(job_uuid, shots=qlm_job.nbshots)
            qiskit_results.append(qiskit_result)

        results = generate_qlm_list_results(qiskit_results[0])
        new_results = []
        for result in results:
            new_results.append(WResult.from_thrift(result))
        return _wrap_results(qlm_batch, new_results, 100000)

    def __init__(
        self, user_configs: UserConfigs, name: Optional[str] = "c12sim-iswap", plugins=None
    ):
        """
        Constructor for the CallistoBackendToQPU class.
        It is a QPUHandler that is going to use the CallistoSimProvider to get the backend

        :param user_configs: UserConfigs object that contains the token for the access to the remote server
        :param name: string representing the name of the backend. it is optional and if not provide it has a default
                    value of c12sim-iswap
        :param plugins:  Any plugins to be added (c.f qat.core documentation)
        """
        super().__init__(plugins)
        self._name = name
        self._user_configs = user_configs

        self._request = Request(self._user_configs.token, self._user_configs.verbose)
        self.set_backend(name, self._user_configs.token, self._user_configs.verbose)

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
                backend_version="0.0.1",
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


if __name__ == "__main__":

    import os

    user_auth_token = os.getenv("C12_TOKEN", "3ae88c08-29cf-456e-b284-e01add5ca833")
    configs = UserConfigs.parse_obj({"token": user_auth_token})

    nbqubits = 2
    qpu = CallistoBackendToQPU(configs, name="c12sim-iswap")

    from qat.lang.AQASM import Program, H

    prog = Program()
    reg = prog.qalloc(1)
    prog.apply(H, reg[0])

    job = prog.to_circ().to_job(nbshots=10024)

    print("Selected backend:", qpu.backend)
    results = qpu.submit(job)
    print(results)
