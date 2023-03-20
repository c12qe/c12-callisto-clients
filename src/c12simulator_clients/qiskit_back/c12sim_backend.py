from typing import Iterable, List, Optional, Dict, Tuple, Union, NewType
from numpy import pi
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary
from qiskit.compiler.transpiler import transpile
from qiskit.providers import BackendV2, Provider, Options
from qiskit.transpiler import Target, InstructionProperties
from qiskit.circuit import Measure, Parameter, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import RXGate, RYGate, RZGate, iSwapGate, CRXGate, CXGate

from c12simulator_clients.api.client import Request
from c12simulator_clients.api.exceptions import ApiError
from c12simulator_clients.qiskit_back.exceptions import C12SimJobError

from c12simulator_clients.qiskit_back.c12sim_job import C12SimJob

gate_name_to_instruction_mapper = {
    "rx": RXGate(Parameter("theta")),
    "ry": RYGate(Parameter("theta")),
    "rz": RZGate(Parameter("theta")),
    "iswap": iSwapGate(),
    "crx": CRXGate(Parameter("theta")),
    "cx": CXGate(),
}

InstOpsType = NewType(
    "InstOpsType",
    Optional[Dict[Union[Tuple[int], Tuple[int, int]], Optional[InstructionProperties]]],
)


class C12SimBackend(BackendV2):
    """
    C12 simulator backend wrapper for Qiskit's BackendV2 class.

    """

    @classmethod
    def _default_options(cls):
        options = Options()
        return options

    def __init__(
        self,
        name: str,
        request: Request,
        provider: Provider = None,
        properties: dict = None,
        **fields,
    ):
        """
        Constructor for C12SIM backend. Checking authentication and
        a backend name.

        :type provider: Backward Provider object that is used to provide access to the backend
        :param name:name of a backend
        :param request: Request API object for making the api requests to the C12 sim backend
        :param properties: Dictionary of the backend properties
        :param fields: additional fields to set the backend as number of shots

        """
        super().__init__(
            provider=provider,
            name=name,
            **fields,
        )

        self._backend_name = name
        self._request = request
        self._properties = properties
        self._max_circuits = self._properties["max-circuits"]

    @property
    def request(self):
        return self._request

    @property
    def target(self):
        """
            The Target class is used to represent a backend or hardware target.
            It provides information about the capabilities and properties of a quantum device or
            simulator, such as the number of qubits, available gates, and measurement options.
            This information can be used to configure and validate quantum circuits before they are
            executed on the target backend.

            See: https://qiskit.org/documentation/stubs/qiskit.transpiler.Target.html


        :return: Target object
        """

        # target
        target = Target(description=f"Target for device: {self._backend_name}")
        n_qubits = self._properties["n_qubits"]
        basis_gates = self._properties["basis_gates"]

        # add measurement instructions
        target.add_instruction(Measure(), {(i,): None for i in range(n_qubits)})

        for gate_name in basis_gates:
            inst = gate_name_to_instruction_mapper[gate_name]
            if gate_name == "crx":
                qreg_q = QuantumRegister(2, "q")
                circuit = QuantumCircuit(qreg_q)
                circuit.crx(pi, qreg_q[0], qreg_q[1])

                SessionEquivalenceLibrary.add_equivalence(CXGate(), circuit)

            inst_ops: InstOpsType = {}
            if inst.num_qubits == 1:
                # One qubit ops
                for i in range(n_qubits):
                    # On all qubits it is available
                    inst_ops[(i,)] = None
                target.add_instruction(inst, inst_ops)
            elif inst.num_qubits == 2:
                # Two qubit ops
                for i in range(n_qubits):
                    for j in range(i + 1, n_qubits):
                        inst_ops[(i, j)] = None
                        inst_ops[(j, i)] = None
                target.add_instruction(inst, inst_ops)
            else:
                # Currently, we do not support three qubit operations
                pass

        return target

    def jobs(self, limit: int = 50, offset: int = 0) -> List[C12SimJob]:
        """
        Returns all the jobs associated to the user for the backend.
        :param limit: number of records to be returned
        :param offset: offset from start
        :return: list of C12SimJob
        """
        try:
            jobs = self._request.get_user_jobs(limit, offset)
        except ApiError as err:
            raise C12SimJobError("Error starting a job") from err

        result = [
            C12SimJob(
                backend=self,
                job_id=item["uuid"],
                qasm=item["task"],
                shots=item["options"]["shots"],
                result=item["options"]["result"],
            )
            for item in jobs
        ]

        return result

    @property
    def max_circuits(self):
        return self._max_circuits

    @property
    def dtm(self) -> float:
        raise NotImplementedError(f"System time resolution of output signals is not supported by {self._backend_name}.")

    @property
    def meas_map(self) -> List[List[int]]:
        raise NotImplementedError(f"Meas map is not supported by {self._backend_name}.")

    def drive_channel(self, qubit: int):
        raise NotImplementedError(f"Drive channel is not supported by {self._backend_name}.")

    def measure_channel(self, qubit: int):
        raise NotImplementedError(f"Mesure channel is not supported by {self._backend_name}.")

    def acquire_channel(self, qubit: int):
        raise NotImplementedError(f"Acquire channel is not supported by {self._backend_name}.")

    def control_channel(self, qubits: Iterable[int]):
        raise NotImplementedError(f"Control channel is not supported by {self._backend_name}.")

    def run(self, run_input, **options) -> Union[C12SimJob, List[C12SimJob]]:
        """
            This method returns a :class:`~qiskit.providers.Job` object that runs circuits.

        :param run_input: (QuantumCircuit) or list: object to run on the backend.
        :param options: Any kwarg options to pass to the backend for running the
                        config.
        :return: C12SimJob instance

        :raise C12SimJobError if there is an error starting a job
                ValueError if arguments are not proper type
        """

        if not isinstance(run_input, QuantumCircuit) and not isinstance(run_input, list):
            raise ValueError(f"Input type {type(run_input)}")

        shots = options["shots"] if "shots" in options else 1024
        result_type = "counts,statevector"

        if not isinstance(run_input, list):
            run_input = [run_input]

        jobs = []

        for circuit in run_input:
            if not isinstance(circuit, QuantumCircuit):
                # Skip the elements that are not QuantumCircuit
                continue

            # This part of transpilation to a basis set of circuit before sending qasm string
            # is done because of the bug in qiskit qasm function
            # see: https://github.com/Qiskit/qiskit-terra/issues?q=is%3Aissue%20is%3Aopen%20Qasm%20%22Cannot%20find%20gate%20definition%22
            # It has been suggested that the best way is to transpile it to some basis set
            circuit = transpile(circuit, basis_gates=["rx", "ry", "rz", "cx"])

            qasm = circuit.qasm(formatted=False)
            try:
                job_uuid = self._request.start_job(
                    qasm_str=qasm, shots=shots, result=result_type, backend_name=self._backend_name
                )
            except ApiError as err:
                raise C12SimJobError("Error starting a job") from err

            jobs.append(C12SimJob(backend=self, job_id=job_uuid, qasm=qasm, shots=shots, result=result_type))

        return jobs if len(jobs) > 1 else jobs[0]
