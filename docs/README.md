### C12 Jupyther hub


The C12 simulator JupytherHab allows users to learn, try, and utilize the simulator that will demonstrate the benefits of the future C12 quantum
computer. JupytherLab has already preinstalled and preconfigured Python packages necessary to use the C12 simulator.

After successful login, the user can use the full JupyterLab capabilities. The users can save their Jupyther notebooks and work in their local folder, but it is crucial to notice that no files can be kept inside the folder that contains tutorials (docs/ folder). This folder is a read-only folder, so it is not possible to save custom-made files there, as well as it is not possible to change the notebooks.  


The tutorials can be seen on the left side of the initial JupyterLab screen, and they are divided into five notebooks:

 1. The first one is devoted to the basics of the Qiskit library, mainly creating the quantum circuits and performing the perfect simulation using Qiskit's Aer package. Also, we will briefly cover the OpenQASM format and its properties.

2. The second one shows the usage of the c12simulator-clients package for running the quantum circuits on the C12 simulator and obtaining the simulation results. The notebook also shows one example using a popular quantum algorithm: Groover's algorithm.

3. The third notebook explains how we can retrieve the information from the jobs that have already been run. Besides that, we will see how to run multiple circuits simultaneously.

4. The fourth notebook shows how to run circuits using simple API calls. This notebook demonstrates low-level communication with the C12 simulator.

5. The fifth notebook demonstrates how to get the mid-circuit states using barriers.

![](/Users/viktor/Desktop/Projects/c12sim-frontend/docs/Figure1.png)

