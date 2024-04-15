FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y curl git

RUN git clone --depth 1 https://github.com/acmesh-official/acme.sh.git
WORKDIR /acme.sh
RUN ./acme.sh --install --accountemail kozubaeff@yandex-team.ru --nocron
WORKDIR /
RUN rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.acme.sh:${PATH}"
RUN acme.sh --register-account -m kozubaeff@yandex-team.ru

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .

CMD ["python3", "main.py"]
