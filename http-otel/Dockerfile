FROM python:3-slim-buster

RUN apt-get  update && \
  apt-get install -y make bash curl gcc && \
  python3 -m ensurepip && \
  pip3 install --upgrade -q pip setuptools

WORKDIR /project

COPY requirements.txt ./
COPY web ./web

RUN pip3 install -q -r requirements.txt
ENV FLASK_APP=web

ENTRYPOINT []
CMD ["flask","run"]
