FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt;
COPY app.py .
COPY oss_service.py .
ENV TZ=Asia/Shanghai
ENV PYTHONPATH="/app:$PYTHONPATH"
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:7081", "app:app"]
