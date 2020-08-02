import re
import struct
import sys
import time

import cursor
import pandas as pd


class Frame:
    def __init__(self, data):
        self.frame = data
        self.id_dec = int(self.frame[0])
        self.len = int(self.frame[1])
        self.hex_data = self.frame[2:(self.len+2)]
        self.hex_byte_1 = '  '
        self.hex_byte_2 = '  '
        self.hex_byte_3 = '  '
        self.hex_byte_4 = '  '
        self.hex_byte_5 = '  '
        self.hex_byte_6 = '  '
        self.hex_byte_7 = '  '
        self.hex_byte_8 = '  '
        self.extract_hex_bytes()
        self.xPos = 0
        self.colour = ''
        self.count = 0
        self.count_in_last_3_seconds = 0
        self.count_per_total_seconds = 0
        self.count_per_second_in_last_3_seconds = 0

    def extract_hex_bytes(self):
        if (len(self.hex_data) == 1):
            self.hex_byte_1 = self.hex_data[0]
        elif (len(self.hex_data) == 2):
            self.hex_byte_1 = self.hex_data[0]
            self.hex_byte_2 = self.hex_data[1]
        elif (len(self.hex_data) == 3):
            self.hex_byte_1 = self.hex_data[0]
            self.hex_byte_2 = self.hex_data[1]
            self.hex_byte_3 = self.hex_data[2]
        elif (len(self.hex_data) == 4):
            self.hex_byte_1 = self.hex_data[0]
            self.hex_byte_2 = self.hex_data[1]
            self.hex_byte_3 = self.hex_data[2]
            self.hex_byte_4 = self.hex_data[3]
        elif (len(self.hex_data) == 5):
            self.hex_byte_1 = self.hex_data[0]
            self.hex_byte_2 = self.hex_data[1]
            self.hex_byte_3 = self.hex_data[2]
            self.hex_byte_4 = self.hex_data[3]
            self.hex_byte_5 = self.hex_data[4]
        elif (len(self.hex_data) == 6):
            self.hex_byte_1 = self.hex_data[0]
            self.hex_byte_2 = self.hex_data[1]
            self.hex_byte_3 = self.hex_data[2]
            self.hex_byte_4 = self.hex_data[3]
            self.hex_byte_5 = self.hex_data[4]
            self.hex_byte_6 = self.hex_data[5]
        elif (len(self.hex_data) == 7):
            self.hex_byte_1 = self.hex_data[0]
            self.hex_byte_2 = self.hex_data[1]
            self.hex_byte_3 = self.hex_data[2]
            self.hex_byte_4 = self.hex_data[3]
            self.hex_byte_5 = self.hex_data[4]
            self.hex_byte_6 = self.hex_data[5]
            self.hex_byte_7 = self.hex_data[6]
        elif (len(self.hex_data) == 8):
            self.hex_byte_1 = self.hex_data[0]
            self.hex_byte_2 = self.hex_data[1]
            self.hex_byte_3 = self.hex_data[2]
            self.hex_byte_4 = self.hex_data[3]
            self.hex_byte_5 = self.hex_data[4]
            self.hex_byte_6 = self.hex_data[5]
            self.hex_byte_7 = self.hex_data[6]
            self.hex_byte_8 = self.hex_data[7]

    def increase_count(self):
        self.count += 1
        self.count_in_last_3_seconds += 1

    def calc_counts_per_total_seconds(self):
        global START_TIME
        self.count_per_total_seconds = (self.count / (get_current_time() - START_TIME))
    
    def calc_count_per_second_in_last_3_seconds(self, tempTime):
        global TEMP_TIME
        timeWindow = get_current_time() - tempTime
        if (timeWindow >= 3):
            self.count_in_last_3_seconds = 0
            TEMP_TIME = get_current_time()
        elif ((round(timeWindow,1) % 1) == 0):
            self.count_per_second_in_last_3_seconds = (self.count_in_last_3_seconds / timeWindow)

    def set_position(self, x):
        self.xPos = x

    def print(self, hex_byte_pos=[], colour=''):
        sys.stdout.write(str(self.id_dec)+'\t')
        sys.stdout.write(' '+str(self.len)+'\t')
        sys.stdout.write('| ')
        if (1 in hex_byte_pos):
            set_text_colour(colour)
        sys.stdout.write(self.hex_byte_1+' ')
        set_text_colour('RESET')
        sys.stdout.write('| ')
        if (2 in hex_byte_pos):
            set_text_colour(colour)
        sys.stdout.write(self.hex_byte_2+' ')
        set_text_colour('RESET')
        sys.stdout.write('| ')
        if (3 in hex_byte_pos):
            set_text_colour(colour)
        sys.stdout.write(self.hex_byte_3+' ')
        set_text_colour('RESET')
        sys.stdout.write('| ' )
        if (4 in hex_byte_pos):
            set_text_colour(colour)
        sys.stdout.write(self.hex_byte_4+' ')
        set_text_colour('RESET')
        sys.stdout.write('| ')
        if (5 in hex_byte_pos):
            set_text_colour(colour)
        sys.stdout.write(self.hex_byte_5+' ')
        set_text_colour('RESET')
        sys.stdout.write('| ')
        if (6 in hex_byte_pos):
            set_text_colour(colour)
        sys.stdout.write(self.hex_byte_6+' ')
        set_text_colour('RESET')
        sys.stdout.write('| ')
        if (7 in hex_byte_pos):
            set_text_colour(colour)
        sys.stdout.write(self.hex_byte_7+' ')
        set_text_colour('RESET')
        sys.stdout.write('| ')
        if (8 in hex_byte_pos):
            set_text_colour(colour)
        sys.stdout.write(self.hex_byte_8+' ')
        set_text_colour('RESET')
        sys.stdout.write('| \t')
        sys.stdout.write(str(self.count))
        sys.stdout.write('\t |\t')
        sys.stdout.write(str(round(self.count_per_total_seconds,2)))
        sys.stdout.write('\t |')
        sys.stdout.write('\t')
        sys.stdout.write(str(round(self.count_per_second_in_last_3_seconds,2)))
        sys.stdout.write('\n')

def print_header():
    sys.stdout.write('\033[1m') # Bold text
    print('ID\tLEN\t  B1   B2   B3   B4   B5   B6   B7   B8       COUNT          COUNT/SEC          COUNT/SEC (LAST 3 SECS)')
    sys.stdout.write('\033[0m') # Normal text
    print('----------------------------------------------------------------------------------------------------------------------------')

def get_current_time():
    return time.time()

def clear_terminal_then_print(uniqueFrames):
    sys.stdout.write('\033[2J')     # Clear
    sys.stdout.write('\033[0;0H')   # Set cursor to 0,0
    print_header()
    for frame in uniqueFrames:
        frame.print()

def move_to_line_in_terminal_then_print(newFrame, hex_byte_pos):
    sys.stdout.write('\033[s')      # Save cursor position
    # Move cursor to line that has this frame
    sys.stdout.write('\033[{0};0H'.format(newFrame.xPos+3))
    sys.stdout.write("\033[K")      # Clear terminal line
    newFrame.print(hex_byte_pos, 'CYAN')
    sys.stdout.write('\033[u')      # Re-load saved cursor position

def set_text_colour(colour):
    colours = {
        1: '\033[1;31m',
        2: '\033[1;34m',
        3: '\033[1;36m',
        4: '\033[1;32m',
        5: '\033[0;0m'
    }
    if (colour == 'RED'):
        sys.stdout.write(colours.get(1))
    elif (colour == 'BLUE'):
        sys.stdout.write(colours.get(2))
    elif (colour == 'CYAN'):
        sys.stdout.write(colours.get(3))
    elif (colour == 'GREEN'):
        sys.stdout.write(colours.get(4))
    elif (colour == 'RESET'):
        sys.stdout.write(colours.get(5))
    else:
        raise Exception('Invalid colour option')

def get_index_in_list(uniqueFrames, id_dec):
    for index,frame in enumerate(uniqueFrames):
        if frame.id_dec == id_dec:
            return index
    return -1

def sort_list_by_id(uniqueFrames):
    return sorted(uniqueFrames, key=lambda x: x.id_dec)

def check_for_byte_changes(newFrame, oldFrame):
    differentBytes = []
    for ii in range(len(newFrame.hex_data)):
        if newFrame.hex_data[ii] != oldFrame.hex_data[ii]:
            differentBytes.append(ii+1)
    return differentBytes

def read_csv_file(filePath):
    return pd.read_csv(filePath)

def update_data(newFrame, oldFrame, index):
    oldFrame.set_position(index)
    for val in filter(lambda a: a.startswith('hex') | a.startswith('frame'), dir(oldFrame)):
        setattr(oldFrame,val,getattr(newFrame,val))

def listen_to_usb_serial(dataStream):
    uniqueFrames = []

    for _, data in enumerate(dataStream.values):
        # Imitate delay
        time.sleep(0.0005)

        # Create a new frame object
        newFrame = Frame(data)

        # Check if we have seen this frame before
        index = get_index_in_list(uniqueFrames, newFrame.id_dec)
        if (index == -1): # If no, append to uniqueFrames, sort then print
            uniqueFrames.append(newFrame)
            uniqueFrames = sort_list_by_id(uniqueFrames)
            clear_terminal_then_print(uniqueFrames)
        else: # If yes, overwrite frame in uniqueFrames
            differentBytes = check_for_byte_changes(newFrame, uniqueFrames[index])
            update_data(newFrame, uniqueFrames[index], index)
            uniqueFrames[index].increase_count()
            uniqueFrames[index].calc_counts_per_total_seconds()
            uniqueFrames[index].calc_count_per_second_in_last_3_seconds(TEMP_TIME)
            move_to_line_in_terminal_then_print(uniqueFrames[index], differentBytes)


if __name__ == "__main__":
    # Start time for collecting data
    START_TIME = get_current_time()
    TEMP_TIME = get_current_time()
    cursor.hide()
    sys.stdout.write("\x1b[8;{rows};{cols}t".format(rows=50, cols=80))
    print_header()
    sys.stdout.write('\033[s')
    dataStream = read_csv_file("log-(31-07-2020_12-55-39).csv")
    listen_to_usb_serial(dataStream)
