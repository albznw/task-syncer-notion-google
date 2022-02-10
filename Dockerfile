FROM python:3-bullseye
WORKDIR /app

ENV PYTHONUNBUFFERED=1 

COPY . .
RUN pip install -r requirements.txt
RUN pip uninstall bson -y
RUN pip uninstall pymongo -y
RUN pip install pymongo

CMD ["python3.10", "-u", "main.py"]
