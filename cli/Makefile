CONTAINER_BIN = podman
CONTAINER_NAME = mlb-game-watcher

.PHONY: build stop run shell

build:
	$(CONTAINER_BIN) build -t $(CONTAINER_NAME) .

stop:
	$(CONTAINER_BIN) rm -f $(CONTAINER_NAME) || true

run: build stop
	$(CONTAINER_BIN) run -d --name mlb-game-watcher localhost/$(CONTAINER_NAME):latest

shell:
	$(CONTAINER_BIN) exec -it $(CONTAINER_NAME) /bin/sh
