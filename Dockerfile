FROM python:3.9.10-slim-buster
EXPOSE 5000/tcp
WORKDIR /app
COPY requirements.txt requirements.txt
RUN python -m pip install --upgrade pip
RUN pip install --upgrade setuptools
RUN pip3 install -r requirements.txt
COPY . .
CMD [ "python3", "main.py" ]