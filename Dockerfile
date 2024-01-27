FROM python:3.9

WORKDIR /app

COPY . /app

RUN apt-get update \
    && apt-get install -y libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
