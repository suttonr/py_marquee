FROM python:3-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN apk add --no-cache --virtual .build-deps gcc musl-dev curl
RUN apk add --no-cache runit
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /etc/service/marquee && \
    cat > /etc/service/marquee/run << 'EOF'
#!/bin/sh
cd /usr/src/app
exec python -u ./marquee_launcher.py find-games -f "Red Sox" --launch
EOF
RUN chmod +x /etc/service/marquee/run

CMD ["runsvdir", "/etc/service"]
