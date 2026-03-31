FROM python:3.12
ARG UID=10000
ARG GID=10000

WORKDIR /src
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY *.py ./

USER $UID:$GID
CMD ["python3", "runtime_exporter.py"]

