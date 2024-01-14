upload:
	rm -rf neomatrix/__pycache__
	ampy -p /dev/tty.usbserial-110 put neomatrix
	ampy -p /dev/tty.usbserial-110 put test.py
