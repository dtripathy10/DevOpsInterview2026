FROM python:3.12-slim
WORKDIR /app
COPY error.py .
# exec form so python is PID 1 and receives signals directly
CMD ["python", "-u", "error.py"]