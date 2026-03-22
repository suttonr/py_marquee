.PHONY: egg build clean publish install
VERSION_FILE := pyproject.toml
# Build the heartbeat module as an egg package
egg: clean
	bumpver update --patch
	python3 -m pip install --upgrade build
	python3 -m build

publish: egg
	twine upload -r pypi dist/*

# Install the egg in development mode
install:
	cd $(shell pwd) && python3 -m pip install -e .

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf heartbeat.egg-info/
