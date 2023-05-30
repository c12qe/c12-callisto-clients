from typing import Optional, Union
import time
import json
import numpy as np
import requests
from c12simulator_clients.api.configs import (
    API_MAXJOBS_URL,
    API_BACKENDS_URL,
    API_QUERY_URL,
    API_JOB_STATUS_URL,
    API_USER_JOBS,
    API_GET_JOB,
    API_PARAMS_URL,
)
from c12simulator_clients.api.exceptions import ApiError


class Request:
    """Facade for the API requests to the C12 simulator backend."""

    def __init__(self, auth_token: str, verbose: bool = False):
        """
        :param auth_token:  authorisation token of a user that is used for access
                to the C12 APIs
        :param verbose: if detailed printing is active
        """
        self._auth_token = auth_token
        self._verbose = verbose

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

        if self._verbose:
            print(f"Calling API {method}:{url} with params {params}")

        if method == "post":
            response = requests.request(
                method=method, url=url, data=json.dumps(params), headers=headers, timeout=60
            )
        else:
            response = requests.request(
                method=method, url=url, params=params, headers=headers, timeout=60
            )
        status = response.status_code

        if self._verbose:
            print(f"Response {response.status_code}")

        if status == 401:
            raise PermissionError(
                "You do not have a proper credentials to access the requested endpoint."
            )

        if status < 200 or status >= 300:
            raise ApiError(f"Error occurred during the execution of the request: {status}")

        if self._verbose:
            print(f"Response body: {response.json()}")
        data = response.json()

        if data is None:
            raise ApiError("Error occurred during the execution of the request")

        return data

    def get_job_result(
        self,
        job_uuid: str,
        output_data: str = None,
        timeout: Optional[float] = None,
        wait: float = 5,
    ) -> object:
        """
         Wait for the job state is finished or an error during the job execution
         occurred.

        :param job_uuid: job id
        :param output_data: string to override which results to get,
                values should be 'counts, statevector,density_matrix,states'
                If no value is specified the one from the DB will be used.
        :param timeout: seconds to wait for a job (if None wait forever)
        :param wait: seconds between queries

        :return:  json with job information (dict)

        :raise ApiError if error in API communication occurred
               TimeoutError if timeout is exceeded
        """
        params = {"job_uuid": job_uuid, "output_data": output_data}

        if wait < 0.5:
            raise ValueError(f"Parameter wait cannot be smaller than 0.5s ({wait})")

        start = time.time()  # the current time in seconds
        if self._verbose:
            print("Getting job result... ")
        while True:
            data = self.do_request(API_QUERY_URL, method="get", params=params)
            job_status = data["status"]

            time_diff = time.time() - start
            if self._verbose:
                print(f"{time_diff:.3}s : job status: {job_status}")

            if job_status in ("ERROR", "FINISHED", "CANCELLED"):
                return data

            if timeout is not None and time_diff >= timeout:
                raise TimeoutError(f"Timeout while waiting for job {job_uuid}")

            time.sleep(wait)

    def start_job(
        self,
        qasm_str: str,
        shots: int,
        result: str,
        backend_name: str,
        ini_noise: bool = False,
        ini: Union[str, list[np.complexfloating]] = None,
        physical_params: str = None,
    ) -> tuple:
        """
        Call the API to start the job.

        :param qasm_str: QASM string with transpiled quantum circuit
        :param shots:  Number of shots for the simulation
        :param result: what is desired output (statevector, counts, density_matrix)
        :param backend_name: the name of the backend to run on
        :param ini_noise: specify if we want to apply a noise to the initialisation of the circuit
        :param ini: initial state of the circuit as a string (label) or array of complex numbers
        :param physical_params: stringify json with physical parameters
        :return: tuple str (job uuid) and transpiled qasm str

        :raise: ApiError if unexpected API error happened
        """
        params = {
            "qasm_str": qasm_str,
            "num_shots": shots,
            "result": result,
            "backend_name": backend_name,
        }

        if ini is not None:
            if isinstance(ini, str):
                params["inilabel"] = ini
            else:
                params["inistatevector"] = np.array2string(
                    np.array(ini), separator=",", suppress_small=True
                )
        if ini_noise:
            params["ininoise"] = True

        if physical_params is not None:
            params["physical_params"] = physical_params

        data = self.do_request(API_QUERY_URL, method="post", params=params)

        if "job_uuid" not in data or "transpiled" not in data:
            raise ApiError("Unexpected error when starting a job")

        return data["job_uuid"], data["transpiled"]

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

    def get_params(self) -> dict:
        """
        Call to the API to get the physical parameters of the C12 system.
        :return: list of parameters

        :raise: ApiError if unexpected API error has happened
        """

        data = self.do_request(API_PARAMS_URL, method="get")

        if "physical_params" not in data:
            raise ApiError("Unexpected error getting physical parameters of the system.")

        return data["physical_params"]

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
        """
        Get the status of a running job.
        :param job_uuid: job uuid
        :return: status of a job
        """
        params = {"job_uuid": job_uuid}
        data = self.do_request(API_JOB_STATUS_URL, method="get", params=params)

        if "status" not in data:
            raise ApiError("Unexpected error getting available system backends.")

        return data["status"]

    def get_job(self, job_uuid: str) -> dict:
        """
        Get a specific job with a given uuid.
        :param job_uuid: job_id
        :return: dict of job data
        """
        params = {"job_uuid": job_uuid}
        data = self.do_request(API_GET_JOB, method="get", params=params)

        if "job" not in data:
            raise ApiError("Unexpected error getting available system backends.")

        return data["job"]

    def get_user_jobs(self, limit: int, offset: int) -> list:
        """
        Get a list of a running job for a specific user, with a support
        for paging.
        :param limit:  number of records
        :param offset:  offset
        :return:  list of running jobs
        """
        params = {"limit": limit, "offset": offset}
        data = self.do_request(API_USER_JOBS, method="get", params=params)

        if "jobs" not in data:
            raise ApiError("Unexpected error getting available system backends.")

        return data["jobs"]
