# c12-callisto-clients

`c12-callisto-clients` is a Python package with tools that enable a user to communicate with 
C12's Callisto emulator, whose purpose is to emulate operations on C12’s quantum computer hardware.

C12’s quantum computer is based on optimized spin qubits. The spin qubit is realized from electrons
trapped in a double quantum dot suspended on a carbon nanotube embedded in a silicon nanofabricated
circuit. C12’s spin qubits have high fidelity, scalability and connectivity because of the properties
of the materials used.

## Installing


#### From the PyPI repository

Run the following command inside your local Python environment:

`pip install  c12_callisto_clients`

#### From the GitHub package
In order to run the package the best policy is to create a conda environment where
all the necessary packages will be installed. To do that, we need to have conda installed (if that
is not the case see <a href="https://conda.io/projects/conda/en/latest/user-guide/install/index.html#regular-installation">conda installation</a>).
<ol>
<li> Clone the GitHub repository into local folder:

`git clone https://github.com/c12qe/c12simulator-clients.git`

</li>

<li> Create the conda environment with the command:

`conda env create -f environment.yml`
</li>
<li> Then activate the conda environment with:

`conda activate  c12_callisto_clients`
</li>
<li> And finally install the dependencies with 

`poetry install`
</li>
</ol>


## Usage

<ol>

<li> <b> <u>From the command line:</u></b> </li>


The application will run a circuit given in Open QASM format. In order to do that a user has to input
a personal token that C12 can provide. All the parameters can be given as command line arguments:

`python3 main.py --qasmfile {{PATH_TO_FILE_WITH_QASM_STR}} --token {{USER_AUTH_TOKEN}}`

The additional argument `--verbose` can be added in order to see a more detailed output.

Details of the command structure can be obtained using command `python3 main.py --help`


<li> <b> <u>From the installed package:</u></b> </li>

Jupyter notebooks are available at: <a href="https://github.com/c12qe/c12-callisto-clients/tree/master/docs">notebooks</a>

</ol>

