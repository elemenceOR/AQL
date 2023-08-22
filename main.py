import RPi.GPIO as GPIO
import dht11
from collections import deque
import requests
import thingspeak
from matplotlib import pyplot as plt
import numpy as np
from time import sleep
import threading

# AQI database
CHANNEL_ID_SEND = '2233058'
write_key = 'AT9HYGWD6A7BJCO1'
channel = thingspeak.Channel(id=CHANNEL_ID_SEND, api_key=write_key)

# Channel for sending warning mail
CHANNEL_ID_RECEIVE = '343018'
url = f"https://api.thingspeak.com/channels/{CHANNEL_ID_RECEIVE}/feeds.json"

# setup font type for plot
plt.rcParams['font.family'] = 'DejaVu Sans'

GPIO.setwarnings(False)

GPIO.setmode(GPIO.BCM)


# function for getting nd organizing data from the thingspeak channel.
def get_from_cloud():
    res = requests.get(url)

    data = res.json()
    # print(data)

    # Extract data for each field into separate arrays
    data_field_1 = [int(entry.get('field1')) for entry in data['feeds'] if
                    entry.get('field1') and entry.get('field1').isnumeric()]
    data_field_2 = [int(entry.get('field2')) for entry in data['feeds'] if
                    entry.get('field2') and entry.get('field2').isnumeric()]
    data_field_3 = [int(entry.get('field3')) for entry in data['feeds'] if
                    entry.get('field3') and entry.get('field3').isnumeric()]
    data_field_4 = [(entry.get('field4')) for entry in data['feeds']]
    data_field_5 = [(entry.get('field5')) for entry in data['feeds']]
    data_field_6 = [int(entry.get('field6')) for entry in data['feeds'] if
                    entry.get('field6') and entry.get('field6').isnumeric()]
    data_field_7 = [int(entry.get('field7')) for entry in data['feeds'] if
                    entry.get('field7') and entry.get('field7').isnumeric()]
    data_field_8 = [(entry.get('field8')) for entry in data['feeds']]

    # calculation mean for PM1.0, PM2.5, PM10.0
    mean1 = np.mean(data_field_1)
    mean2 = np.mean(data_field_2)
    mean3 = np.mean(data_field_3)

    plt.subplot(3, 1, 1)
    plt.axhline(mean1, color='r', linestyle='--')
    plt.plot(data_field_1)
    plt.xlabel('Sample')
    plt.ylabel(r'$\mu_g/m^3$')
    plt.title('PM1.0')

    plt.subplot(3, 1, 2)
    plt.plot(data_field_2)
    plt.axhline(mean2, color='r', linestyle='--')
    plt.xlabel('Sample')
    plt.ylabel(r'$\mu_g/m^3$')
    plt.title('PM2.5')

    plt.subplot(3, 1, 3)
    plt.plot(data_field_3)
    plt.axhline(mean3, color='r', linestyle='--')
    plt.xlabel('Sample')
    plt.ylabel(r'$\mu_g/m^3$')
    plt.title('PM10.0')

    plt.subplots_adjust(wspace=0.5, hspace=1)
    plt.show()

    return mean2, mean3, data_field_6, data_field_7, data_field_1, data_field_2, data_field_3


# function for collecting local temperature and humidity
def local_data(buffer_temp, buffer_hum):
    instance = dht11.DHT11(pin=4)
    result = instance.read()
    while not result.is_valid():
        result = instance.read()

    local_temp = result.tempreture  # local temperature
    local_hum = result.humidity  # local humidity

    buffer_temp.append(local_temp)
    buffer_hum.append(local_hum)

    print("Current temperature: %-3.1f C" % local_temp)
    print("Current humidity: %-3.1f %%" % local_hum)
    # print(buffer_temp)
    # print(buffer_hum)

    mean_temp = np.mean(buffer_temp)
    mean_hum = np.mean(buffer_hum)

    plt.figure()
    plt.subplot(211)
    plt.title('Mean Temperature')
    plt.plot(mean_temp)

    plt.subplot(212)
    plt.plot(mean_hum)
    plt.title('Mean Humidity')
    plt.show()


# function for calculating AQI
def aql_calc(mean2, mean3):
    x = mean2
    y = mean3

    # setting up the piecewise linear function
    Cp_2 = [0.0, 12.0, 12.1, 35.4, 35.5, 55.4, 55.5, 150.4, 150.5, 250.4, 250.5, 350.4, 350.5, 500.4]
    Cp_10 = [0, 54, 55, 154, 155, 254, 255, 354, 355, 424, 425, 504, 505, 604]
    Ip = [0, 50, 51, 100, 101, 150, 151, 200, 201, 300, 301, 400, 401, 500]

    for i in range(len(Cp_2) - 1):
        if Cp_2[i] <= x <= Cp_2[i + 1]:
            x0, x1 = Cp_2[i], Cp_2[i + 1]
            y0, y1 = Ip[i], Ip[i + 1]

            IP_2 = (((y1 - y0) / (x1 - x0)) * (x - x0)) + y0
            aqi_2_5 = round(IP_2, 1)

    for j in range(len(Cp_10) - 1):
        if Cp_10[j] <= y <= Cp_10[j + 1]:
            m0, m1 = Cp_10[j], Cp_10[j + 1]
            n0, n1 = Ip[j], Ip[j + 1]

            IP_10 = (((n1 - n0) / (m1 - m0)) * (y - m0)) + n0
            aqi_10 = round(IP_10, 1)

    max_aqi = max(aqi_2_5, aqi_10)
    # print(max_aqi)
    # print(aqi_2_5)
    # print(aqi_10)

    channel.update({'field1': aqi_2_5, 'field2': aqi_10, 'field3': max_aqi})


def function_60_seconds():
    while True:
        a, b, c, d, e, f, g = get_from_cloud()

        # a = mean2 (mean of aqi2.5)
        # b = mean3 (mean of aqi10.0)
        # c = data_field_6 (Temperature)
        # d = data_field_7 (Humidity)
        # e = data_field_1 (aqi1.0)
        # f = data_field_2 (aqi2.5)
        # g = data_field_3 (aqi10.0)

        aql_calc(a, b)

        sleep(60)
        return c, d


def function_10_seconds(temp, hum):
    bt = deque(temp, maxlen=100)
    tc = [(x - 32) * 5 / 92 for x in bt]
    bh = deque(hum, maxlen=100)
    while True:
        local_data(tc, bh)
        sleep(10)


# main run

thread_60_seconds = threading.Thread(target=function_60_seconds)
thread_10_seconds = threading.Thread(target=function_10_seconds)

t, h = thread_60_seconds.start()
thread_10_seconds.start(t, h)

