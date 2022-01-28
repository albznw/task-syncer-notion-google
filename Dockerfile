FROM python:3.10-bullseye
WORKDIR /app

COPY . .
RUN pip install -r requirements.txt

CMD ["python3.10", "-u", "main.py"]