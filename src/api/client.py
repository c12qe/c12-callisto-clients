from typing import Optional
import time
import requests
from c12simulator.api.configs import (
    API_MAXJOBS_URL,
    API_BACKENDS_URL,
    API_QUERY_URL,
    API_JOB_STATUS_URL,
    API_USER_JOBS,
)
from c12simulator.api.exceptions import ApiError


class Request:
    """Facade for the API requests to the C12 simulator backend."""

    def __init__(self, auth_token: str):
        """
        :param auth_token:  authorisation token of a user that is used for access
                to the C12 APIs
        """
        self._auth_token = auth_token

        # Setting the header with a token
        self._auth_header = {"Authorization": "Bearer " + self._auth_token}

    @property
    def auth_token(self):
        """
        Getter for the authentication token.
        :return: user authentication token
        """
        return self._auth_token

    @auth_token.setter
    def auth_token(self, auth_token: str):
        self._auth_token = auth_token
        self._auth_header = {"Authorization": "Bearer " + self._auth_token}

    def do_request(self, url: str, method: str, params: dict = None, header: dict = None) -> object:
        """
        Generic function for performing the API request.

        :param url: string - the endpoint url of the API
        :param method: http method ("get", "put", "post", "patch", "delete")
        :param params: query parameters of the request (dictionary)
        :param header: additional header options
        :return: object (json)

        :raise ValueError - if some parameters ar in the work fmt
               HTTPError - if some Error occurred during the execution of the api request
               PermissionError - if the user do not have enough permission for the execution of
                        the API

        """
        if header is None:
            headers = self._auth_header
        else:
            headers = {**header, **self._auth_header}
        if method not in ("get", "put", "post", "patch", "delete"):
            raise ValueError(f"Wrong parameter for method argument: {method}")

        response = requests.request(method=method, url=url, params=params, headers=headers)
        status = response.status_code

        if status == 401:
            raise PermissionError(
                "You do not have a proper credentials to access the requested endpoint."
            )

        if status < 200 or status >= 300:
            raise ApiError(f"Error occurred during the execution of the request: {status}")

        data = response.json()

        if data is None:
            raise ApiError("Error occurred during the execution of the request")

        return data

    def get_job_result(
        self, job_uuid: str, timeout: Optional[float] = None, wait: float = 5
    ) -> object:
        """
         Wait for the job state is finished or an error during the job execution
         occurred.

        :param job_uuid: job id
        :param timeout: seconds to wait for a job (if None wait forever)
        :param wait: seconds between queries
        :return:  json with job information (dict)

        :raise ApiError if error in API communication occurred
               TimeoutError if timeout is exceeded
        """
        params = {"job_uuid": job_uuid}

        if wait < 0.5:
            raise ValueError(f"Parameter wait cannot be smaller than 0.5s ({wait})")

        start = time.time()  # the current time in seconds
        while True:
            data = self.do_request(API_QUERY_URL, method="get", params=params)
            job_status = data["status"]
            if job_status in ("ERROR", "FINISHED", "CANCELLED"):
                return data

            time_diff = time.time() - start
            if timeout is not None and time_diff >= timeout:
                raise TimeoutError(f"Timeout while waiting for job {job_uuid}")

            time.sleep(wait)

    def start_job(self, qasm_str: str, shots: int, result: str, backend_name: str) -> str:
        """
        Call the API to start the job.

        :param qasm_str:  QASM string with quantum circuit
        :param shots:  Number of shots for the simulation
        :param result: what is desired output (statevector, counts, density_matrix)
        :param backend_name: the name of the backend to run on
        :return: str (job uuid)

        :raise ApiError if unexpected API error happened
        """
        params = {
            "qasm_str": qasm_str,
            "shots": shots,
            "result": result,
            "backend-name": backend_name,
        }
        data = self.do_request(API_QUERY_URL, method="post", params=params)

        if "job_uuid" not in data:
            raise ApiError("Unexpected error when starting a job")

        return data["job_uuid"]

    def get_maxjobs(self) -> int:
        """
        Call to the API to get the maximum number of jobs per user.
        :return: number of jobs (int)
        :raise ApiError if unexpected API error happened
        """
        data = self.do_request(API_MAXJOBS_URL, method="get")
        if "maxjobs" not in data:
            raise ApiError("Unexpected error getting a max allowed jobs for a user.")

        return data["maxjobs"]

    def get_backends(self) -> list:
        """
        Call to the API to get all available backends.
        :return: list of available backends, empty if none available
        :raise ApiError if unexpected API error happened
        """
        data = self.do_request(API_BACKENDS_URL, method="get")

        if "backends" not in data:
            raise ApiError("Unexpected error getting available system backends.")
        return data["backends"]

    def get_job_status(self, job_uuid: str) -> str:
        params = {"job_uuid": job_uuid}
        data = self.do_request(API_JOB_STATUS_URL, method="get", params=params)

        if "status" not in data:
            raise ApiError("Unexpected error getting available system backends.")

        return data["status"]

    def get_user_jobs(self, limit: int, offset: int) -> list:
        params = {"number_of_records": limit, "offset": offset}
        data = self.do_request(API_USER_JOBS, method="get", params=params)

        if "jobs" not in data:
            raise ApiError("Unexpected error getting available system backends.")

        return data["jobs"]
