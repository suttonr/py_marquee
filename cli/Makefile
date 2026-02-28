CONTAINER_BIN = podman
CONTAINER_NAME = mlb-game-watcher
SERVICE_NAME = container-$(CONTAINER_NAME).service

.PHONY: build start stop status remove create install run shell

build:
	$(CONTAINER_BIN) build -t $(CONTAINER_NAME) .

stop:
	systemctl --user stop $(SERVICE_NAME) || true

start:
	systemctl --user start $(SERVICE_NAME) || true

status:
	systemctl --user status $(SERVICE_NAME)
	$(CONTAINER_BIN) logs mlb-game-watcher | tail

remove: stop
	$(CONTAINER_BIN) rm -f $(CONTAINER_NAME) || true	

create: build
	$(CONTAINER_BIN) create --name $(CONTAINER_NAME) localhost/$(CONTAINER_NAME):latest

install: create
	mkdir -p ~/.config/systemd/user/
	$(CONTAINER_BIN) generate systemd --name $(CONTAINER_NAME) > ~/.config/systemd/user/$(SERVICE_NAME)
	systemctl --user daemon-reload
	systemctl --user enable $(SERVICE_NAME)

run: remove install start status
	echo "Done"

shell:
	$(CONTAINER_BIN) exec -it $(CONTAINER_NAME) /bin/sh
