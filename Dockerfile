FROM python:3

WORKDIR ./
COPY . ./
RUN python3 -m pip install --no-cache-dir -r requirements.txt

CMD [ "python3", "./main.py" ]