#!/usr/bin/python

### Control the LED strip via serial communication
# for use with serial_control.ino and serial_individual_brightness_control.ino

import pyaudio
import struct
import math
import serial
import time







#!/usr/bin/env python
# 

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import pyaudio
import struct
import wave
import pylab as pl


### Audio Sampling Constants
nFFT = 512 # based on sound-spectrum_experimenting.py, increasing doesn't seem to help
BUF_SIZE = 4 * nFFT
FORMAT = pyaudio.paInt16
CHANNELS = 1
# RATE = 44100
RATE = 22050
INPUT_BLOCK_TIME = 0.05
INPUT_FRAMES_PER_BLOCK = int(RATE*INPUT_BLOCK_TIME)

### LED Serial Communication Constants
NUM_LEDS = 64
port = '/dev/cu.usbmodemfa131'  # usb port left-bottom (away from screen)
# port = '/dev/cu.usbmodemfd121' # usb port left-top (toward screen)
baud_rate = 2000000 #rate of serial read/write
ser = serial.Serial(port, baud_rate)

# the internal serial buffer size of micro controller
BUFFER_SIZE = 64

MAX_BRIGHTNESS = 20
maxExpectedY = 20


def normalize(collection, MAX_VALUE, maxExpectedY):
  """ Normalizes all items in collection to be in [0, MAX_VALUE] """
  """ maxExpectedY is maximum possible y value of input """
  """ assumes collection is linearly distributed """

  # max_amplitude = max(collection)
  # min_amplitude = min(collection)
  # new_collection = list()
  # for i in range(len(collection)):
  #   item = collection[i] / maxExpectedY
  #   new_collection.append(item)
  normalized = map(lambda x: x / maxExpectedY if x < maxExpectedY else 1, collection)
  return map(lambda x: int(x * MAX_VALUE), normalized)

def write_leds_brightness(amplitudes):
  """ Map amplitudes to brightness for each LED. """
  """ For use with serial_individual_brightness_control.ino """
  
  # compress amplitudes to be NUM_LEDS wide
  buckets = [0] * NUM_LEDS
  freqs_per_bucket = int(math.ceil(len(amplitudes) * 1.0 / NUM_LEDS))
  for i in range(len(amplitudes)):
    # truncate to find current bucket
    bucket_index = i / freqs_per_bucket
    buckets[bucket_index] = buckets[bucket_index] + amplitudes[i]
  # print("summed buckets: " + str(buckets))
  # print("max bucket: " + str(max(buckets)))
  global maxExpectedY
  maxExpectedY = max(maxExpectedY, max(buckets))
  buckets = normalize(buckets, MAX_BRIGHTNESS, maxExpectedY)
  # print("\n\nwriting: " + str(buckets))
  # write instructions to microcontroler
  # TODO: make it work when buffer size < num leds
  for i in range(NUM_LEDS / BUFFER_SIZE):
    ser.write(bytearray(buckets[i * BUFFER_SIZE : (i + 1) * BUFFER_SIZE]))
  # ser.write(bytearray(buckets))
    # acknowledgement = ser.readline()
    # print("acknowledgement: " + str(acknowledgement))

def write_leds_color():
  """ For use with serial_control.ino """
  for i in range(NUM_LEDS):
      # TODO: speed up by writing bytes: ie ser.write(bytes)
      ser.write("255,00,00")
      acknowledgement = ser.readline()
      # print("acknowledgement: " + str(acknowledgement))
  # print("end")
  exit()

def get_avg_power_in_range(high, freqs, Y):
  """ [0 - high) """
  frequencies_per_index = RATE * 1.0 / nFFT # number of frequencies in each X 'bucket'
  high_index = int(high / frequencies_per_index) # 0-based
  # the real "zero" is in the middle
  start_index = len(Y) / 2 - high_index
  end_index = len(Y) / 2 + high_index
  total_power = 0
  for i in range(start_index, end_index):
    print("frequency: " + str(freqs[i]))
    print("power: " + str(Y[i]))
    total_power += Y[i]
  return total_power / (end_index - start_index)



# X goes from -XXXX to +XXXX
def get_power(stream, MAX_y):
  """ Modified from code by Yu-Jie Lin """

  data = stream.read(INPUT_FRAMES_PER_BLOCK)

  # Unpack data
  y = np.array(struct.unpack("%dh" % (INPUT_FRAMES_PER_BLOCK * CHANNELS), data)) / MAX_y
  # Fourier Transform
  Y = np.fft.fft(y, nFFT)
  # for some reason Y is duplicated / mirrored, so only take right (positive) half
  Y = abs(np.hstack((Y[:nFFT/2])))

  return Y


def main():
  """ Modified from code by Yu-Jie Lin """
  p = pyaudio.PyAudio()

  # Frequency range
  x_f = 1.0 * np.arange(0, nFFT / 2) / nFFT * RATE
  
  # Used for normalizing signal. If use paFloat32, then it's already -1..1.
  # Because of saving wave, paInt16 will be easier.
  MAX_y = 2.0**(p.get_sample_size(FORMAT) * 8 - 1)

  try:
    while(True):
      try:
        stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=BUF_SIZE)
        Y = get_power(stream, MAX_y)
        # pl.plot(x_f, Y)
        # pl.xlabel("Frequency(Hz)")
        # pl.ylabel("Power(dB)")
        # pl.show()
        # print("Y: " + str(Y[:50]))
        # print("Y end: " + str(Y[len(Y) - 50:-1]))
        write_leds_brightness(Y)

        # print("power in low interval: " + str(get_avg_power_in_range(100, x_f, Y)))
      except IOError, e:
        print("Error recording: %s"%e)
  except KeyboardInterrupt:
    print("received KeyboardInterrupt. Cleaning up and exiting")
    stream.stop_stream()
    stream.close()
    p.terminate()
    return


if __name__ == '__main__':
    # clear anything in the buffer
    ser.flushInput()
    ser.flushOutput()   

    # Arduino resets when new serial connection is opened, so wait
    # for this process to complete
    time.sleep(3)

    # while(True):
    #     write_leds()
    
    main()
  
