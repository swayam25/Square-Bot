FROM python:3.12.8-slim

WORKDIR /square

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["/bin/bash", "-c", ". .venv/bin/activate && python main.py"]