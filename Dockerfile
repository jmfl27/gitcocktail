# Base Python image
FROM python:3

# Install Golang
RUN apt-get update && apt-get install -y golang

WORKDIR /gitcocktail

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

WORKDIR /gitcocktail/app

CMD ["python3", "app.py"]