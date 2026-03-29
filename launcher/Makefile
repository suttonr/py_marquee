CONTAINER_BIN = podman
CONTAINER_NAME = marquee-launcher-service
SERVICE_NAME = container-$(CONTAINER_NAME).service
CONTAINER_OPTS = --publish 4000:4000 --env PORT=4000 --env DEBUG=true
CONTAINER_BUILD_ARGS = $(shell cat ./build_args.txt) --platform=linux/amd64,linux/arm64
IMAGE_REPO = repo.aptbox.net/internal
IMAGE_VERSION = $(shell grep "^current_version =" bumpver.toml | cut -d '=' -f 2 | tr -d '\" ' | tr -d '\n')


ifdef SYSTEMD_SYSTEM_UNIT
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

.PHONY: get_egg package_cli package build start stop status remove create install run shell

get_egg:
	# mqtt-heartbeat is now installed from internal PyPI
	@echo "mqtt-heartbeat is installed from internal PyPI"

package:
	cd .. && git archive --format=tar.gz --output=py_marquee-launcher-$(shell git rev-parse --short HEAD).tar.gz HEAD:launcher/

package_cli:
	tar -cvzf cli.tar.gz -C .. --exclude=cli/cache --exclude=cli/examples --exclude cli/__pycache__ cli

build: package_cli
	bumpver update --patch && \
	IMAGE_VERSION=$$(grep "^current_version =" bumpver.toml | cut -d '=' -f 2 | tr -d '\" ' | tr -d '\n') && \
	$(SUDO) $(CONTAINER_BIN) manifest create $(IMAGE_REPO)/$(CONTAINER_NAME):$${IMAGE_VERSION} && \
	$(SUDO) $(CONTAINER_BIN) build $(CONTAINER_BUILD_ARGS) --manifest $(IMAGE_REPO)/$(CONTAINER_NAME):$${IMAGE_VERSION} .

push: build
	IMAGE_VERSION=$$(grep "^current_version =" bumpver.toml | cut -d '=' -f 2 | tr -d '\" ' | tr -d '\n') && \
	$(SUDO) $(CONTAINER_BIN) manifest push --all  $(IMAGE_REPO)/$(CONTAINER_NAME):$${IMAGE_VERSION} docker://$(IMAGE_REPO)/$(CONTAINER_NAME):$${IMAGE_VERSION} && \
	$(SUDO) $(CONTAINER_BIN) manifest push --all  $(IMAGE_REPO)/$(CONTAINER_NAME):$${IMAGE_VERSION} docker://$(IMAGE_REPO)/$(CONTAINER_NAME):latest

stop:
	$(SYSTEMCTL_CMD) $(SYSTEMD_USER_FLAG) stop $(SERVICE_NAME) || true

start:
	$(SYSTEMCTL_CMD) $(SYSTEMD_USER_FLAG) start $(SERVICE_NAME) || true

status:
	$(SYSTEMCTL_CMD) --no-pager $(SYSTEMD_USER_FLAG) status $(SERVICE_NAME)
	$(CONTAINER_BIN) logs $(CONTAINER_NAME) | tail -20

remove: stop
	$(CONTAINER_BIN) rm -f $(CONTAINER_NAME) || true

create: remove
	$(CONTAINER_BIN) pull $(CONTAINER_REPO)/$(CONTAINER_NAME):latest
	$(CONTAINER_BIN) create --name $(CONTAINER_NAME) \
		$(CONTAINER_OPTS) \
		--volume $(shell pwd)/../:/app/parent \
		$(CONTAINER_REPO)/$(CONTAINER_NAME):latest

install: create
	$(MKDIR_CMD) -p $(SYSTEMD_DIR)
	$(CONTAINER_BIN) generate systemd --name $(CONTAINER_NAME) > $(SYSTEMD_DIR)/$(SERVICE_NAME)
	$(SYSTEMCTL_CMD) $(SYSTEMD_USER_FLAG) daemon-reload
	$(SYSTEMCTL_CMD) $(SYSTEMD_USER_FLAG) enable $(SERVICE_NAME)

run: remove install start status
	@echo "Marquee Launcher Service is now running as a systemd service"
	@echo "API available at: http://localhost:4000"
	@echo "Health check: curl http://localhost:4000/health"

shell:
	$(CONTAINER_BIN) exec -it $(CONTAINER_NAME) /bin/sh

logs:
	$(CONTAINER_BIN) logs -f $(CONTAINER_NAME)

run-debug: create
	$(CONTAINER_BIN) run $(CONTAINER_OPTS) $(CONTAINER_NAME)