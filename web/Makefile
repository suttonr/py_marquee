CONTAINER_BIN = podman
CONTAINER_NAME = marquee-web
SERVICE_NAME = container-$(CONTAINER_NAME).service
CONTAINER_OPTS = --publish 8888:8888 --env-file .env
CONTAINER_VOLUMES = --volume $(shell pwd)/auth/:/auth
PUBLISH_HOST = web.ryanmsutton.com
PUBLISH_PATH = /home/opc

ifdef SYSTEM_UNIT
SYSTEMD_USER_FLAG =
SYSTEMD_DIR = /etc/systemd/system
SYSTEMCTL_CMD = sudo systemctl
SUDO = sudo
else
SYSTEMD_USER_FLAG = --user
SYSTEMD_DIR = ~/.config/systemd/user/
SYSTEMCTL_CMD = systemctl
SUDO = 
endif

.PHONY: build start stop status remove create install run shell package

package:
	cd .. && git archive --format=tar.gz --output=py_marquee-web-$(shell git rev-parse --short HEAD).tar.gz HEAD:web/

publish: package
	scp ../py_marquee-web-$(shell git rev-parse --short HEAD).tar.gz $(PUBLISH_HOST):$(PUBLISH_PATH)
	ssh $(PUBLISH_HOST) "mkdir -p $(PUBLISH_PATH)/web; tar -xvzf $(PUBLISH_PATH)/py_marquee-web-$(shell git rev-parse --short HEAD).tar.gz -C $(PUBLISH_PATH)/web/"
	ssh $(PUBLISH_HOST) "bash -c 'cd $(PUBLISH_PATH)/web; export SYSTEM_UNIT=true; make run'"


build:
	$(SUDO) $(CONTAINER_BIN) build -t $(CONTAINER_NAME) .

stop:
	$(SUDO) $(SYSTEMCTL_CMD) $(SYSTEMD_USER_FLAG) stop $(SERVICE_NAME) || true

start:
	$(SUDO) $(SYSTEMCTL_CMD) $(SYSTEMD_USER_FLAG) start $(SERVICE_NAME) || true

status:
	$(SUDO) $(SYSTEMCTL_CMD) --no-pager $(SYSTEMD_USER_FLAG) status $(SERVICE_NAME)
	$(CONTAINER_BIN) logs $(CONTAINER_NAME) | tail -20

remove: stop
	$(SUDO) $(CONTAINER_BIN) rm -f $(CONTAINER_NAME) || true

create: remove build
	mkdir -p $(shell pwd)/auth/
	touch $(shell pwd)/auth/admin.json
	$(SUDO) $(CONTAINER_BIN) create --name $(CONTAINER_NAME) \
		$(CONTAINER_OPTS) \
		$(CONTAINER_VOLUMES) \
		localhost/$(CONTAINER_NAME):latest

install: create
	$(SUDO) mkdir -p $(SYSTEMD_DIR)
	$(SUDO) $(CONTAINER_BIN) generate systemd --name $(CONTAINER_NAME) | $(SUDO) tee $(SYSTEMD_DIR)/$(SERVICE_NAME)
	$(SUDO) $(SYSTEMCTL_CMD) daemon-reload
	$(SUDO) $(SYSTEMCTL_CMD) enable $(SERVICE_NAME)

run: remove install start status
	@echo "Marquee Web Interface is now running as a systemd service"
	@echo "Web interface available at: http://localhost:8888"

shell:
	$(SUDO) $(CONTAINER_BIN) exec -it $(CONTAINER_NAME) /bin/sh

logs:
	$(CONTAINER_BIN) logs -f $(CONTAINER_NAME)

run-debug: create
	$(CONTAINER_BIN) run $(CONTAINER_OPTS) $(CONTAINER_VOLUMES) $(CONTAINER_NAME)

