# c12simulator-clients

`c12simulator-clients` is a Python package with a tools that enables a user to communicate with the 
C12's remote simulator whose purpose
is to simulate the operations on the real C12 quantum computer. 

C12’s quantum computer is based on optimized
spin qubits. The spin qubit is realized from electrons trapped in a double quantum dot suspended on carbon 
nano tubes (CNTs) embedded in a silicon nano circuit and microwave cavity. C12’s spin qubits have 
high fidelity, scalability and connectivity because of the properties of the materials used to build the basics 
elements of the C12 system.

## Installing

#### From the Test PyPI repository

Run the following command inside your local python environment:

`pip install -i https://test.pypi.org/simple/ c12simulator-clients`

#### From the PyPI repository

Run the following command inside your local python environment:

`pip install c12simulator-clients`

#### From the GitHub package
In order to run the package the best policy is to create the conda environment where
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

`conda activate c12simulator-clients`
</li>
<li> And finally install the dependencies with 

`poetry install`
</li>
</ol>


## Usage

<ol>

<li> <b> <u>From the command line:</u></b> </li>


The application will run a circuit given in Open QASM format. In order to do that a user has to have its
token (given by the administrator or ??? ). All this parameters can be given as a command line arguments:

`python3 main.py --qasmfile {{PATH_TO_FILE_WITH_QASM_STR}} --token {{USER_AUTH_TOKEN}}`

Additional argument `--verbose` can be added in order to see the more detailed output.

Detailed information of the command structure can be obtained using command `python3 main.py --help`


<li> <b> <u>From the installed package:</u></b> </li>

Jupyter notebooks are given on the link: <a href="?">notebooks</a>

</ol>

