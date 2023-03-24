FROM python:3.9-slim AS builder

WORKDIR /build

COPY pyproject.toml poetry.lock /build/

RUN pip3 install poetry
RUN poetry export -f requirements.txt --output requirements.txt

# ---

FROM jupyter/base-notebook:python-3.9.12

WORKDIR /c12sim-clients

COPY --from=builder /build/requirements.txt requirements.txt
USER root
RUN sudo apt-get -y update && sudo apt-get -y install build-essential
RUN sudo apt-get install -y libopenblas-dev
RUN pip install -r requirements.txt
RUN pip install matplotlib
RUN pip install pylatexenc
RUN python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple c12simulator-clients
RUN fix-permissions "${CONDA_DIR}"
RUN fix-permissions "/home/${NB_USER}"

COPY ./docs .

ENTRYPOINT ["jupyter-lab","--allow-root","--ip","0.0.0.0","--port","9999", "--ServerApp.token=f9a3bd4e9f2c3be01cd629154cfb224c2703181e050254b5"]
