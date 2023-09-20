"""
  Basic URLs to the C12 sim APIs.
"""

import os

HOST_URL = os.getenv("C12_HOST_URL", "57.128.103.232")
PORT = os.getenv("C12_PORT", "8080")
PROTOCOL = os.getenv("C12_PROTOCOL", "http")

API_BASE_URL = f"{PROTOCOL}://{HOST_URL}{'' if PORT is None else ':'+str(PORT)}/api"

API_SIMULATOR_URL = API_BASE_URL + "/c12sim"
API_HEALTH_URL = API_BASE_URL + "/health"


API_QUERY_URL = API_SIMULATOR_URL + "/query"
API_BACKENDS_URL = API_SIMULATOR_URL + "/backends"
API_PARAMS_URL = API_SIMULATOR_URL + "/params"
API_MAXJOBS_URL = API_SIMULATOR_URL + "/maxjobs"
API_JOB_STATUS_URL = API_QUERY_URL + "/status"
API_USER_JOBS = API_SIMULATOR_URL + "/jobs"
API_GET_JOB = API_SIMULATOR_URL + "/job"
