FROM python:3.9
RUN pip install kubernetes
COPY app /app