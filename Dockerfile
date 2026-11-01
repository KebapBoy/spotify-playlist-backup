FROM python:3.14-slim
RUN useradd --create-home --uid 1000 appuser
WORKDIR /app
ENV PYTHONUNBUFFERED=1
USER appuser
RUN pip install --no-cache-dir --user spotipy apscheduler pyyaml
USER root
RUN mkdir -p /data && chown -R appuser:appuser /data
USER appuser
CMD ["python", "/app/app.py"]
