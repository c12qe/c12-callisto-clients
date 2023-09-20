from typing import Optional, Tuple, List
from datetime import datetime
import numpy as np
from qiskit import QuantumCircuit
from qiskit.result import Result
from qiskit.providers import JobV1, BackendV2
from qiskit.quantum_info import Statevector, DensityMatrix
from qiskit.providers.jobstatus import JobStatus, JOB_FINAL_STATES
from qiskit.result.models import ExperimentResult, ExperimentResultData
from c12_callisto_clients.qiskit.exceptions import C12SimApiError, C12SimJobError


from c12_callisto_clients.api.exceptions import ApiError


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

    def __init__(self, backend: BackendV2, job_id: str, **metadata):
        super().__init__(backend=backend, job_id=job_id, metadata=metadata)
        self._job_id = job_id  # uuid of the job
        self._backend = backend  # backend instance
        self._date = datetime.now()
        self._metadata = metadata  # additional data
        self._result = None  # result of the job
        self._status = None  # current status of the job
        self._result_data = None  # row job result data
        self._error = None
        self._job_error_msg = None

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

    def refresh(self) -> None:
        """Obtain the latest job information from the server.
        Function has a side effect of changing private fields.
        :return: None
        """

        try:
            # Get job data
            job = self._backend.request.get_job(self._job_id)
        except ApiError as err:
            raise C12SimJobError("Error getting a job") from err

        if job is None:
            return None

        self._status = get_qiskit_status(job["status"])
        self._metadata = {
            "qasm": job["task"],
            "shots": job["options"]["shots"],
            "result": job["options"]["result"],
            "qasm_orig": job["task_orig"],
        }
        self._result_data = job["result"]
        self._error = job["errors"]

    def _wait_for_completion(
        self,
        timeout: Optional[float] = None,
        wait: float = 5,
        required_states: Tuple[JobStatus] = JOB_FINAL_STATES,
    ) -> bool:
        """
        Wrapper: waiting for the job completion.

        :param timeout: Seconds until the exception is triggered. None for indefinitely.
        :param wait: The wait time in seconds between queries.
        :param required_states: The final job status required.
        :return: True if the final job status matches one of the required states.
        """

        if self._status in JOB_FINAL_STATES:
            return self._status in required_states

        try:
            result = self._backend.request.get_job_result(
                self._job_id,
                output_data="counts,statevector,states,density_matrix",
                timeout=timeout,
                wait=wait,
            )
        except ApiError as err:
            raise C12SimApiError(
                "Unexpected error happened during the accessing the remote server"
            ) from err
        except TimeoutError as err2:
            raise C12SimJobError("Timeout occurred while waiting for job execution") from err2

        # Refresh the job params
        self.refresh()

        return self._status in required_states

    def error_message(self) -> Optional[str]:
        """
        Provide details about the reason of a job failure.
        :return: An error report if the job failed or None
        """

        if not self._wait_for_completion(required_states=(JobStatus.ERROR,)):
            return None

        if not self._job_error_msg:
            if not self._error:
                self.refresh()

            self._job_error_msg = f"Error: {self._error} "

        return self._job_error_msg

    def _parse_result_data(self) -> List[ExperimentResult]:
        """
        Parse result dictionary.
        :return: Result object or none
        """

        if self._result_data is None:
            return []
        if "counts" not in self._result_data or "statevector" not in self._result_data:
            raise C12SimJobError("Error getting the information from the system.")

        # Getting the counts & statevector of the circuit after execution
        counts = self._result_data["counts"]
        statevector = self._convert_json_to_np_array(self._result_data["statevector"])

        # Additional mid-circuit data (if any)
        additional_data = {}
        if "states" in self._result_data:
            states = self._result_data["states"]

            if "density_matrix" in states and "statevector" in states:
                dms = states["density_matrix"]
                svs = states["statevector"]

                for key in svs.keys():
                    svs[key] = self._convert_json_to_np_array(svs[key])

                for key in dms.keys():
                    dms[key] = self._convert_json_to_np_matrix(dms[key])

                additional_data = {**dms, **svs}

        experiment = ExperimentResult(
            shots=self.shots(),
            success=self.status() is JobStatus.DONE,
            status=self.status().name,
            data=ExperimentResultData(counts=counts, statevector=statevector, **additional_data),
        )

        return [experiment]

    def result(self, timeout: Optional[float] = None, wait: float = 5):
        if not self._wait_for_completion(timeout, wait, required_states=(JobStatus.DONE,)):
            if self._status is JobStatus.CANCELLED:
                raise C12SimJobError(
                    f"Unable to retrieve result for job {self._job_id}. Job was cancelled"
                )

            if self._status is JobStatus.ERROR:
                raise C12SimJobError(
                    f"Unable to retrieve result for job {self._job_id}. "
                    f"Job finished with an error state. "
                    f"Use error_message() method to get more details."
                )

        self.refresh()

        self._result = Result(
            backend_name=self._backend,
            backend_version=self._backend.version,
            job_id=self._job_id,
            qobj_id=0,
            success=self._status == JobStatus.DONE,
            results=self._parse_result_data(),
            status=self._status,
        )

        return self._result

    def cancel(self):
        pass

    def backend(self):
        return self._backend

    def status(self) -> JobStatus:
        """
        Get the latest job status of a current job instance.
        :return: The status of the job.
        """
        if self._status in JOB_FINAL_STATES:
            return self._status

        try:
            status = self._backend.request.get_job_status(self._job_id)
        except ApiError as err:
            raise C12SimApiError(
                "Unexpected error happened during the accessing the remote server"
            ) from err

        self._status = get_qiskit_status(status)

        return self._status

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
