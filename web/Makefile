CONTAINER_BIN = podman
CONTAINER_NAME = marquee-web
CONTAINER_REPO = repo.aptbox.net/internal
SERVICE_NAME = container-$(CONTAINER_NAME).service
CONTAINER_OPTS = --publish 8888:8888 --env-file .env
CONTAINER_VOLUMES = --volume $(shell pwd)/auth/:/auth:Z
PUBLISH_HOST = web.ryanmsutton.com
PUBLISH_PATH = /home/opc
CONTAINER_BUILD_ARGS = $(shell cat ./build_args.txt)

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

.PHONY: get_egg build start stop status remove create install run shell package

get_egg:
	# mqtt-heartbeat is now installed from internal PyPI
	@echo "mqtt-heartbeat is installed from internal PyPI"

package:
	cd .. && git archive --format=tar.gz --output=py_marquee-web-$(shell git rev-parse --short HEAD).tar.gz HEAD:web/

publish: package
	scp ../py_marquee-web-$(shell git rev-parse --short HEAD).tar.gz $(PUBLISH_HOST):$(PUBLISH_PATH)
	ssh $(PUBLISH_HOST) "mkdir -p $(PUBLISH_PATH)/web; tar -xvzf $(PUBLISH_PATH)/py_marquee-web-$(shell git rev-parse --short HEAD).tar.gz -C $(PUBLISH_PATH)/web/"
	ssh $(PUBLISH_HOST) "bash -l -c 'cd $(PUBLISH_PATH)/web; export SYSTEM_UNIT=true; make run'"


build:
	$(SUDO) $(CONTAINER_BIN) build $(CONTAINER_BUILD_ARGS) -t $(CONTAINER_NAME) .

stop:
	$(SUDO) $(SYSTEMCTL_CMD) $(SYSTEMD_USER_FLAG) stop $(SERVICE_NAME) || true

start:
	$(SUDO) $(SYSTEMCTL_CMD) $(SYSTEMD_USER_FLAG) start $(SERVICE_NAME) || true

status:
	$(SUDO) $(SYSTEMCTL_CMD) --no-pager $(SYSTEMD_USER_FLAG) status $(SERVICE_NAME)
	$(SUDO) $(CONTAINER_BIN) logs $(CONTAINER_NAME) | tail -20

remove: stop
	$(SUDO) $(CONTAINER_BIN) rm -f $(CONTAINER_NAME) || true

create: remove
	mkdir -p $(shell pwd)/auth/ || true
	touch $(shell pwd)/auth/admin.json  || true
	$(SUDO) $(CONTAINER_BIN) create --name $(CONTAINER_NAME) \
		$(CONTAINER_OPTS) \
		$(CONTAINER_VOLUMES) \
		$(CONTAINER_REPO)/$(CONTAINER_NAME):latest

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
	$(SUDO) $(CONTAINER_BIN) logs -f $(CONTAINER_NAME)

run-debug: create
	$(CONTAINER_BIN) run $(CONTAINER_OPTS) $(CONTAINER_VOLUMES) $(CONTAINER_NAME)

