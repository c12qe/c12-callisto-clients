from typing import Iterable, List, Optional, Dict, Tuple, Union, NewType
from numpy import pi
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary
from qiskit.quantum_info import TwoQubitBasisDecomposer
from qiskit.providers import BackendV2, Provider, Options
from qiskit.transpiler import Target, InstructionProperties
from qiskit.circuit import Measure, Parameter, QuantumCircuit
from qiskit.circuit.library import RXGate, RYGate, RZGate, iSwapGate, CRXGate, CXGate

from c12_callisto_clients.api.client import Request
from c12_callisto_clients.api.exceptions import ApiError
from c12_callisto_clients.qiskit_back.exceptions import C12SimJobError

from c12_callisto_clients.qiskit_back.c12sim_job import C12SimJob

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
                decomposer = TwoQubitBasisDecomposer(CRXGate(pi))
                circ = decomposer(CXGate().to_matrix())
                SessionEquivalenceLibrary.add_equivalence(CXGate(), circ)

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
            raise C12SimJobError("Error getting user jobs") from err

        result = [
            C12SimJob(
                backend=self,
                job_id=item["uuid"],
                qasm=item["task"],
                shots=item["options"]["shots"],
                result=item["options"]["result"],
                qasm_orig=item["task_orig"],
            )
            for item in jobs
        ]

        return result

    def get_job(self, job_uuid: str) -> Optional[C12SimJob]:
        """
        Get the job with a given uuid.
        :param job_uuid:  uuid of a job
        :return:  None or an instance of C12SimJob class
        """
        try:
            job = self._request.get_job(job_uuid)
        except ApiError as err:
            raise C12SimJobError("Error getting a job") from err

        if job is None:
            return None

        return C12SimJob(
            backend=self,
            job_id=job["uuid"],
            qasm=job["task"],
            shots=job["options"]["shots"],
            result=job["options"]["result"],
            qasm_orig=job["task_orig"],
        )

    @property
    def max_circuits(self):
        return self._max_circuits

    @property
    def dtm(self) -> float:
        raise NotImplementedError(
            f"System time resolution of output signals is not supported by {self._backend_name}."
        )

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

    def _prepare_qasm_file(self, circuit: QuantumCircuit) -> str:
        tmp_qc = circuit.copy_empty_like()

        for instruction, qargs, cargs in circuit:
            if instruction.name in ["initialize"]:
                # Qiskit is not able to convert "initialize" instruction to OpenQASM 2, so we need to decompose it first
                # This is mainly as it is not Unitary instruction
                # it should be solved for OpenQASM 3
                # This can be used for all additional changes to the circuits

                ini_circuit = tmp_qc.copy_empty_like()
                ini_circuit.append(instruction, qargs, cargs)
                ini_circuit = (
                    ini_circuit.decompose()
                )  # It has to be done for the OpenQASM 2.0 it will fail otherwise

                # Pass over the ini_circuit and append it
                # The best way would be to append two circuits
                # Currently QuantumCircuit.append() appends only Instructions
                for ini_instruction, ini_qargs, ini_cargs in ini_circuit:
                    tmp_qc.append(ini_instruction, ini_qargs, ini_cargs)

            else:
                tmp_qc.append(instruction, qargs, cargs)

        return tmp_qc.qasm(formatted=False)

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

        ini_noise = options["ininoise"] if "ininoise" in options else False
        physical_params = options["physical_params"] if "physical_params" in options else None

        if not isinstance(run_input, list):
            run_input = [run_input]

        jobs = []

        for circuit in run_input:
            if not isinstance(circuit, QuantumCircuit):
                # Skip the elements that are not QuantumCircuit
                continue

            # see: https://github.com/Qiskit/qiskit-terra/issues?q=is%3Aissue%20is%3Aopen%20Qasm%20%22Cannot%20find%20gate%20definition%22
            # It has been suggested that the best way is to transpile it to some basis gate set that is simpler
            # For some circuits Qiskit's qasm() function can return wrong qasm fmts.

            qasm = self._prepare_qasm_file(circuit)
            try:
                QuantumCircuit.from_qasm_str(qasm)
            except Exception:
                raise C12SimJobError(
                    "There has been a problem while converting the circuit for OpenQASM fmt"
                    " if possible try transpiling the circuit to more basic gate set. See documentation for more"
                    " information"
                )

            try:
                job_uuid, transpiled_qasm = self._request.start_job(
                    qasm_str=qasm,
                    shots=shots,
                    result=result_type,
                    backend_name=self._backend_name,
                    ini_noise=ini_noise,
                    physical_params=physical_params,
                )
            except ApiError as err:
                raise C12SimJobError("Error starting a job") from err

            # Get the transpiled one

            jobs.append(
                C12SimJob(
                    backend=self,
                    job_id=job_uuid,
                    qasm=transpiled_qasm,
                    qasm_orig=qasm,
                    shots=shots,
                    result=result_type,
                    ini_noise=ini_noise,
                )
            )

        return jobs if len(jobs) > 1 else jobs[0]
