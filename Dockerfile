FROM python:3.13.2-bookworm

WORKDIR /square

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]