
#  This class is responsible for:
#    - reading in the raw packet data from the /dev/eeg/encrypted device
#    - decrypting the signal (two 16-byte packets, ECB mode AES)
#    - queuing the decoded packets for buffer pull requests
#    - forwarding the packets to registered subscribers
#    - passing the packets to the EmotivDevice for updating
#

import string
import threading
import select
import traceback
import time
import Queue
from Crypto.Cipher import AES
from emotiv_data_packet import EmotivDataPacket, counter_to_sensor_id

class EmotivDevice:

    def __init__(self, serial_num, in_dev_name = '/dev/eeg/encrypted'):
        """
        Initialize the Emotiv device with its serial number.
        """
        self.in_dev_name = in_dev_name

        # permanent objects
        self.packet_queue = Queue.Queue()
        self.setup_aes_cipher(serial_num)

        # setup state-dependent objects
        self.clear_state()

    def start_reader(self):
        """
        Start the reader thread.
        """
        # if already started, return immediately
        if self.running:
            return

        # construct a new reader & start it
        self.reader = threading.Thread(target = self.read_data)
        self.reader.start()

    def read_data(self):

        ts_buf = [ 0 ] * 128
        ts_ndx = 0

        # open the device, if unsuccesfull, return immediately
        try:
            f = open(self.in_dev_name, 'r')

            # we're only running if the file opened succesfully
            self.running = True

            # read until we are told to stop
            while not self.stop_requested:

                # wait until data is ready, if not continue (and check if stop is requested)
                ret = select.select([f], [], [], 0.1)
                if len(ret[0]) == 0:
                    self.packet_speed = 0.0
                    continue

                # read 32 bytes from the device
                enc_data = f.read(32)

                # record the packet incoming time
                ts_buf[ts_ndx] = time.time()
                rd_ndx = (ts_ndx + 1) % 128
                self.packet_speed = 128.0 / (ts_buf[ts_ndx] - ts_buf[rd_ndx])
                ts_ndx = (ts_ndx + 1) % 128
            
                # decrypt the data using the AES cipher (two 16 byte blocks)
                raw_data = self.aes.decrypt(enc_data[:16]) + self.aes.decrypt(enc_data[16:])

        finally:
            # reset flags
            self.running = False
            self.stop_requested = False

            # close device
            if f is not None:
                f.close()
                
device = new EmotiveDevice()
device.start_reader()
