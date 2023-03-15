"""
  Basic URLs to the C12 sim APIs.
"""

HOST_URL = "dev-simulator.c12qe.net"
PORT = 8080


API_BASE_URL = f"https://{HOST_URL}/api"

API_SIMULATOR_URL = API_BASE_URL + "/c12sim"
API_HEALTH_URL = API_BASE_URL + "/health"


API_QUERY_URL = API_SIMULATOR_URL + "/query"
API_BACKENDS_URL = API_SIMULATOR_URL + "/backends"
API_MAXJOBS_URL = API_SIMULATOR_URL + "/maxjobs"
API_JOB_STATUS_URL = API_QUERY_URL + "/status"
API_USER_JOBS = API_SIMULATOR_URL + "/jobs"
