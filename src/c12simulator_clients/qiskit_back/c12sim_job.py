from typing import Optional
from datetime import datetime
import numpy as np
from qiskit import QuantumCircuit
from qiskit.result import Result
from qiskit.quantum_info import Statevector, DensityMatrix
from qiskit.providers import JobStatus, JobV1, BackendV2
from qiskit.result.models import ExperimentResult, ExperimentResultData
from c12simulator_clients.qiskit_back.exceptions import C12SimApiError, C12SimJobError


from c12simulator_clients.api.exceptions import ApiError


def get_qiskit_status(status: str) -> JobStatus:
    """
      Function to get a qiskit's JobStatus status of a job.
    :param status:  String with job's status description.
    :return: JobStatus

    :raise: C12SimJobError if unknown status is given
    """

    status = status.upper().strip()
    if status == "QUEUED":
        return JobStatus.QUEUED
    if status == "FINISHED":
        return JobStatus.DONE
    if status == "RUNNING":
        return JobStatus.RUNNING
    if status == "ERROR":
        return JobStatus.ERROR
    if status == "CANCELLED":
        return JobStatus.CANCELLED
    raise C12SimJobError(f"Unknown job state {status}")

    # match status.upper().strip():
    #     case "QUEUED":
    #         return JobStatus.QUEUED
    #     case "FINISHED":
    #         return JobStatus.DONE
    #     case "RUNNING":
    #         return JobStatus.RUNNING
    #     case "ERROR":
    #         return JobStatus.ERROR
    #     case "CANCELLED":
    #         return JobStatus.CANCELLED
    #     case _:
    #         raise C12SimJobError(f"Unknown job state {status}")


class C12SimJob(JobV1):
    """Class representing the C12Sim Job"""

    def __init__(self, backend: BackendV2, job_id: str, **metadata: Optional[dict]):
        super().__init__(backend=backend, job_id=job_id, metadata=metadata)
        self._job_id = job_id
        self._backend = backend
        self._date = datetime.now()
        self._metadata = metadata
        self._result = None

    def submit(self):
        """
          Not implemented methos as to submit a job we are using run() method.
        :return:

        :raise NotImplementedError
        """
        raise NotImplementedError("submit() is not supported. Please use run to submit a job.")

    def shots(self) -> int:
        """Return the number of shots.

        Returns: number of shots.
        """
        return self.metadata["metadata"]["shots"] if "shots" in self.metadata["metadata"] else 0

    @staticmethod
    def _convert_json_to_np_array(data) -> np.ndarray:
        """Function to convert json string data to numpy array"""
        array = np.asarray(data)
        array = np.array(list(map(lambda item: complex(item), array)))
        return array

    @staticmethod
    def _convert_json_to_np_matrix(data) -> np.ndarray:
        """Function to convert json string data to numpy matrix"""
        matrix = []
        dm = np.array(data)
        for i in range(len(dm)):
            matrix.append(C12SimJob._convert_json_to_np_array(dm[i]))
        return np.array(matrix)

    def result(self, timeout: Optional[float] = None, wait: float = 5):
        try:
            result = self._backend.request.get_job_result(self._job_id, timeout, wait)
        except ApiError as err:
            raise C12SimApiError(
                "Unexpected error happened during the accessing the remote server"
            ) from err
        except TimeoutError as err2:
            raise C12SimJobError("Timeout occurred while waiting for job execution") from err2

        job_status = get_qiskit_status(result["status"])

        experiment_results = []

        if job_status == JobStatus.DONE:
            if "counts" not in result["results"] or "statevector" not in result["results"]:
                raise C12SimJobError("Error getting the information from the system.")

            # Getting the counts & statevector of the circuit after execution
            counts = result["results"]["counts"]
            statevector = self._convert_json_to_np_array(result["results"]["statevector"])

            # Additional mid-circuit data (if any)
            additional_data = {}
            if "states" in result["results"]:
                states = result["results"]["states"]

                if "density_matrix" in states and "statevector" in states:
                    dms = states["density_matrix"]
                    svs = states["statevector"]

                    for key in svs.keys():
                        svs[key] = self._convert_json_to_np_array(svs[key])

                    for key in dms.keys():
                        dms[key] = self._convert_json_to_np_matrix(dms[key])

                    additional_data = {**dms, **svs}

            data = ExperimentResultData(counts=counts, statevector=statevector, **additional_data)

            experiment_results.append(
                ExperimentResult(
                    shots=self.shots(),
                    success=job_status == JobStatus.DONE,
                    status=self.status().name,
                    data=data if job_status == JobStatus.DONE else None,
                )
            )

        self._result = Result(
            backend_name=self._backend,
            backend_version=self._backend.version,
            job_id=self._job_id,
            qobj_id=0,
            success=job_status == JobStatus.DONE,
            results=experiment_results,
            status=job_status,
        )

        return self._result

    def cancel(self):
        pass

    def backend(self):
        return self._backend

    def status(self):
        try:
            status = self._backend.request.get_job_status(self._job_id)
        except ApiError as err:
            raise C12SimApiError(
                "Unexpected error happened during the accessing the remote server"
            ) from err

        return get_qiskit_status(status)

    def get_qasm(self, transpiled: bool = False) -> Optional[str]:
        """
        Method returns the qasm string for a given job.
        :return: qasm str or None
        """
        if self.metadata is None or "qasm" not in self.metadata["metadata"]:
            return None
        if transpiled:
            return self.metadata["metadata"]["qasm"]
        else:
            # Added for some backward compatibility
            return (
                self.metadata["metadata"]["qasm_orig"]
                if "qasm_orig" in self.metadata["metadata"]
                else None
            )

    def get_circuit(self, transpiled: bool = False) -> Optional[QuantumCircuit]:
        """
        Method return QuantumCircuit object for a given job.
        :return: QuantumCircuit or None
        """
        qasm_str = self.get_qasm(transpiled=transpiled)
        if qasm_str is None:
            return None

        return QuantumCircuit.from_qasm_str(qasm_str)

    def get_mid_statevector(self, barrier: int) -> Optional[Statevector]:
        """
        Function to get the mid-circuit statevector (if any).
        :param barrier: ordinal number of barrier
        :return: Statevector instance
        """

        if self._result is None:
            raise RuntimeError(
                f"There is no results stored in the job class. You should call result() "
                f"method before calling {self.get_mid_statevector.__name__}"
            )

        result_data = self._result.data()

        if f"sv{barrier}" not in result_data:
            return None

        return Statevector(result_data[f"sv{barrier}"])

    def get_mid_density_matrix(self, barrier: int) -> Optional[DensityMatrix]:
        """
        Function to get the mid-circuit density matrix (if any).
        :param barrier: ordinal number of barrier
        :return: DansityMatrix instance
        """
        if self._result is None:
            raise RuntimeError(
                f"There is no results stored in the job class. You should call result() "
                f"method before calling {self.get_mid_density_matrix.__name__}"
            )

        result_data = self._result.data()

        if f"dm{barrier}" not in result_data:
            return None

        return DensityMatrix(result_data[f"dm{barrier}"])
