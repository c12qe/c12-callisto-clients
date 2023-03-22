from typing import Optional
from datetime import datetime
import numpy as np
from qiskit import QuantumCircuit
from qiskit.result import Result
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

        if job_status != JobStatus.ERROR:
            counts = result["results"]["counts"]
            statevector = np.asarray(result["results"]["statevector"])
            statevector = np.array(list(map(lambda item: complex(item), statevector)))
            data = ExperimentResultData(counts=counts, statevector=statevector)
        experiment_results = ExperimentResult(
            shots=self.shots(),
            success=True,
            status=self.status().name,
            data=data if job_status == JobStatus.DONE else None,
        )
        return Result(
            backend_name=self._backend,
            backend_version=self._backend.version,
            job_id=self._job_id,
            qobj_id=0,
            success=job_status not in (JobStatus.RUNNING, JobStatus.ERROR, JobStatus.QUEUED),
            results=[experiment_results],
            status=job_status,
        )

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

    def get_qasm(self) -> Optional[str]:
        """
        Method returns the qasm string for a given job.
        :return: qasm str or None
        """
        if self.metadata is None or "qasm" not in self.metadata["metadata"]:
            return None
        return self.metadata["metadata"]["qasm"]

    def get_circuit(self) -> Optional[QuantumCircuit]:
        """
        Method return QuantumCircuit object for a given job.
        :return: QuantumCircuit or None
        """
        qasm_str = self.get_qasm()
        if qasm_str is None:
            return None

        return QuantumCircuit.from_qasm_str(qasm_str)
