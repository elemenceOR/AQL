from Adafruit_LED_Backpack import SevenSegment
import RPi.GPIO as GPIO
from time import sleep
from luma.core.interface.serial import spi, noop
from luma.led_matrix.device import max7219
from luma.core.render import canvas
from main import e, f, g, temp_buffer, hum_buffer


ADDRESS = 0x70

LEFT_BUTTON = 25
RIGHT_BUTTON = 19

GPIO.setmode(GPIO.BCM)

GPIO.setup(LEFT_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(RIGHT_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)

serial_interface = spi(port=0, device=1, gpio=noop())
device = max7219(serial_interface, cascaded=1, block_orientation=90, rotate=0)

display = SevenSegment.SevenSegment(address=ADDRESS)

measurements = [e, f, g, temp_buffer, hum_buffer]
total_measurements = len(measurements)

selected_measurement = 0


def update_display():
    with canvas(device) as draw:
        for i in range(total_measurements):
            draw.point((i, 7), fill="white" if i == selected_measurement else "black")


while True:
    display.begin()
    update_display()

    if GPIO.input(RIGHT_BUTTON) == GPIO.LOW:
        selected_measurement = (selected_measurement + 1) % total_measurements
        display.print_float(selected_measurement, decimal_digits=1)
        display.write_display()
        sleep(1)

    if GPIO.input(LEFT_BUTTON) == GPIO.LOW:
        selected_measurement = (selected_measurement - 1 + total_measurements) % total_measurements
        display.print_float(selected_measurement, decimal_digits=1)
        display.write_display()
        sleep(1)
