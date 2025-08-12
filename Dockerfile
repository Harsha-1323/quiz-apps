FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_ENV=production
EXPOSE 5000

# increase gunicorn timeout to avoid short worker timeouts on EC2 t2.micro
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app", "--workers", "2", "--timeout", "120"]

