.PHONY: egg build clean install

# Build the heartbeat module as an egg package
egg:
	cd $(shell pwd) && python3 -m pip install --upgrade build
	python3 -m build

# Install the egg in development mode
install:
	cd $(shell pwd) && python3 -m pip install -e .

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf heartbeat.egg-info/
