.. c12-callisto-clients documentation master file, created by
   sphinx-quickstart on Mon Mar 18 15:31:41 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


Introduction
====================================

c12-callisto-clients is a Python package with tools that enable a user to communicate with C12's Callisto emulator, whose purpose is to emulate operations on the C12's quantum computer hardware.

C12’s quantum computer is based on optimized spin qubits. The spin qubit is realized from electrons trapped in a double quantum dot suspended on a carbon nanotube embedded in a silicon nanofabricated circuit. C12’s spin qubits have high fidelity, scalability and connectivity because of the properties of the materials used.

Installation
====================================

To use Callisto, you design quantum circuits according to either `Qiskit <https://docs.quantum.ibm.com/>`_ or `OpenQASM <https://openqasm.com/>`_ specifications and send them as jobs to the Callisto quantum emulator.

This is done via `Python <https://www.python.org/>`_, so the first step is to install Python and/or an Integrated Development Environment such as `PyCharm <https://www.jetbrains.com/pycharm/>`_ or `Visual Studio Code <https://code.visualstudio.com/>`_. Then install the Callisto client.

From the PyPI repository
------------------------

Run the following command inside your local Python environment:

.. code-block:: bash

   pip install c12_callisto_clients

From the GitHub package
-----------------------

In order to run the package, the best approach is to create a Conda environment where all the necessary packages will be installed. To do that, we need to have Conda installed (if that is not the case see `Conda installation <https://conda.io/projects/conda/en/latest/user-guide/install/index.html>`_).

Clone the GitHub repository into local folder:

.. code-block:: bash

   git clone https://github.com/c12qe/c12simulator-clients.git

Create the Conda environment with the command:

.. code-block:: bash

   conda env create -f environment.yml

Then activate the Conda environment with:

.. code-block:: bash

   conda activate c12_callisto_clients

And finally install the dependencies with

.. code-block:: bash

   poetry install

Getting started
====================================
.. toctree::
   :maxdepth: 2
   :caption: Contents:


   self

   0. README.ipynb
   1. Short_introduction_to_Qiskit.ipynb
   2. Using_the_C12_emulator.ipynb
   3. Working_with_jobs.ipynb
   4. Using API.ipynb
   5. Getting mid circuit states.ipynb
   6. Physical parameters of the system.ipynb
   7. Tket backend.ipynb


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
