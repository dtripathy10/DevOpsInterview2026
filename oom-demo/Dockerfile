FROM python:3.12-slim
WORKDIR /app
COPY app.py .
# exec form so python is PID 1 and receives signals directly
CMD ["python", "-u", "app.py"]