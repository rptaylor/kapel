FROM python:3.12
ARG UID=10000
ARG GID=10000

WORKDIR /src
COPY python/requirements.txt .
RUN pip install -r requirements.txt
COPY python/*.py ./

USER $UID:$GID
CMD python3 KAPEL.py
