upload:
	rm -rf neomatrix/__pycache__
	ampy -p /dev/tty.usbserial-110 put neomatrix
	ampy -p /dev/tty.usbserial-110 put test.py
	ampy -p /dev/tty.usbserial-110 put boot.py
	ampy -p /dev/tty.usbserial-110 put main.py
	ampy -p /dev/tty.usbserial-110 put secrets.py
	ampy -p /dev/tty.usbserial-110 put mqtt.py
	ampy -p /dev/tty.usbserial-110 ls
