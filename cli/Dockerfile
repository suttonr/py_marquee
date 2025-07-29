FROM python:3-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN apk add --no-cache --virtual .build-deps gcc musl-dev curl
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "-u", "./marquee_launcher.py", "find-games", "-f", "Red Sox", "--launch" ]
