upload:
	rm -rf neomatrix/__pycache__
	ampy -p /dev/tty.usbmodem1234561 put neomatrix
	ampy -p /dev/tty.usbmodem1234561 put test.py
	ampy -p /dev/tty.usbmodem1234561 put boot.py
	ampy -p /dev/tty.usbmodem1234561 put main.py
	ampy -p /dev/tty.usbmodem1234561 put secrets.py
	ampy -p /dev/tty.usbmodem1234561 put mqtt.py
	ampy -p /dev/tty.usbmodem1234561 ls
