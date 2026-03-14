CONTAINER_BIN = podman
CONTAINER_NAME = marquee-web
SERVICE_NAME = container-$(CONTAINER_NAME).service
CONTAINER_OPTS = --publish 8888:8888 --env-file .env
CONTAINER_VOLUMES = --volume $(shell pwd)/auth/:/auth

ifdef SYSTEM_UNIT
SYSTEMD_USER_FLAG =
SYSTEMD_DIR = /etc/systemd/system/
SYSTEMCTL_CMD = sudo systemctl
MKDIR_CMD = sudo mkdir
else
SYSTEMD_USER_FLAG = --user
SYSTEMD_DIR = ~/.config/systemd/user/
SYSTEMCTL_CMD = systemctl
MKDIR_CMD = mkdir
endif

.PHONY: build start stop status remove create install run shell

build:
	$(CONTAINER_BIN) build -t $(CONTAINER_NAME) .

stop:
	$(SYSTEMCTL_CMD) $(SYSTEMD_USER_FLAG) stop $(SERVICE_NAME) || true

start:
	$(SYSTEMCTL_CMD) $(SYSTEMD_USER_FLAG) start $(SERVICE_NAME) || true

status:
	$(SYSTEMCTL_CMD) --no-pager $(SYSTEMD_USER_FLAG) status $(SERVICE_NAME)
	$(CONTAINER_BIN) logs $(CONTAINER_NAME) | tail -20

remove: stop
	$(CONTAINER_BIN) rm -f $(CONTAINER_NAME) || true

create: remove build
	mkdir -p $(shell pwd)/auth/
	touch $(shell pwd)/auth/admin.json
	$(CONTAINER_BIN) create --name $(CONTAINER_NAME) \
		$(CONTAINER_OPTS) \
		$(CONTAINER_VOLUMES) \
		localhost/$(CONTAINER_NAME):latest

install: create
	$(MKDIR_CMD) -p $(SYSTEMD_DIR)
	$(CONTAINER_BIN) generate systemd --name $(CONTAINER_NAME) > $(SYSTEMD_DIR)/$(SERVICE_NAME)
	$(SYSTEMCTL_CMD) daemon-reload
	$(SYSTEMCTL_CMD) enable $(SERVICE_NAME)

run: remove install start status
	@echo "Marquee Web Interface is now running as a systemd service"
	@echo "Web interface available at: http://localhost:8888"

shell:
	$(CONTAINER_BIN) exec -it $(CONTAINER_NAME) /bin/sh

logs:
	$(CONTAINER_BIN) logs -f $(CONTAINER_NAME)

run-debug: create
	$(CONTAINER_BIN) run $(CONTAINER_OPTS) $(CONTAINER_VOLUMES) $(CONTAINER_NAME)
