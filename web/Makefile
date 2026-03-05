CONTAINER_BIN = podman
CONTAINER_NAME = marquee-web
SERVICE_NAME = container-$(CONTAINER_NAME).service
CONTAINER_OPTS = --publish 8888:8888

.PHONY: build start stop status remove create install run shell

build:
	$(CONTAINER_BIN) build -t $(CONTAINER_NAME) .

stop:
	systemctl --user stop $(SERVICE_NAME) || true

start:
	systemctl --user start $(SERVICE_NAME) || true

status:
	systemctl --no-pager --user status $(SERVICE_NAME)
	$(CONTAINER_BIN) logs $(CONTAINER_NAME) | tail -20

remove: stop
	$(CONTAINER_BIN) rm -f $(CONTAINER_NAME) || true

create: remove build
	$(CONTAINER_BIN) create --name $(CONTAINER_NAME) \
		$(CONTAINER_OPTS) \
		--volume $(shell pwd)/../:/app/parent \
		localhost/$(CONTAINER_NAME):latest

install: create
	mkdir -p ~/.config/systemd/user/
	$(CONTAINER_BIN) generate systemd --name $(CONTAINER_NAME) > ~/.config/systemd/user/$(SERVICE_NAME)
	systemctl --user daemon-reload
	systemctl --user enable $(SERVICE_NAME)

run: remove install start status
	@echo "Marquee Web Interface is now running as a systemd service"
	@echo "Web interface available at: http://localhost:8888"

shell:
	$(CONTAINER_BIN) exec -it $(CONTAINER_NAME) /bin/sh

logs:
	$(CONTAINER_BIN) logs -f $(CONTAINER_NAME)

run-debug: create
	$(CONTAINER_BIN) run $(CONTAINER_OPTS) $(CONTAINER_NAME)
