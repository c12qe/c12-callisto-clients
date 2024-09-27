# pylint: disable=import-error
from typing import Optional

from qiskit.providers.jobstatus import JobStatus
from qiskit.result import Result as QiskitResult
from qat.comm.shared.ttypes import Job, Batch
from qat.core.qpu.qpu import QPUHandler
from qat.interop.qiskit.providers import (
    generate_qlm_list_results,
    job_to_qiskit_circuit,
    generate_qlm_result,
)


from c12_callisto_clients.user_configs import UserConfigs
from c12_callisto_clients.api.client import Request
from c12_callisto_clients.api.exceptions import ApiError

from c12_callisto_clients.myqlm.providers import _parse_result_data

# Callisto Job Wrapper for AsyncCallistoBackendToQPU


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


class AsyncCallistoBackendToQPU(QPUHandler):

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

    user_auth_token = os.getenv("C12_TOKEN", "")
    configs = UserConfigs.parse_obj({"token": user_auth_token})

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

    pass
