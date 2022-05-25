# syntax=docker/dockerfile:1
FROM python:3.8.0-buster
#Makes a directory for our application
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# copy source code file
COPY . .
ENTRYPOINT ["python3", "./plots.py"]

