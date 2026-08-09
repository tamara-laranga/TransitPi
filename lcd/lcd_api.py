"""Provides an API for talking to HD44780 compatible character LCDs"""

import time


class LcdApi:
    """API for talking with an HD44780 compatible 16x2 or
    20x4 character-based LCD connected to a Raspberry Pi"""

    LCD_CLR = 0x01  # DB0: clear display
    LCD_HOME = 0x02  # DB1: return to home position

    LCD_ENTRY_MODE = 0x04  # DB2: set entry mode
    LCD_ENTRY_INC = 0x02  # DB1: increment
    LCD_ENTRY_SHIFT = 0x01  # DB0: shift

    LCD_ON_CTRL = 0x08  # DB3: turn lcd/cursor on
    LCD_ON_DISPLAY = 0x04  # DB2: turn display on
    LCD_ON_CURSOR = 0x02  # DB1: turn cursor on
    LCD_ON_BLINK = 0x01  # DB0: blinking cursor

    LCD_MOVE = 0x10  # DB4: move cursor/display
    LCD_MOVE_DISP = 0x08  # DB3: move display
    LCD_MOVE_RIGHT = 0x04  # DB2: move right

    LCD_FUNCTION = 0x20  # DB5: function set
    LCD_FUNCTION_8BIT = 0x10  # DB4: set 8BIT mode
    LCD_FUNCTION_2LINES = 0x08  # DB3: two lines
    LCD_FUNCTION_10DOTS = 0x04  # DB2: 5x10 font
    LCD_FUNCTION_RESET = 0x30  # See "Initializing by Instruction" section

    LCD_CGRAM = 0x40  # DB6: set CG RAM address
    LCD_DDRAM = 0x80  # DB7: set DD RAM address

    LCD_RS_CMD = 0
    LCD_RS_DATA = 1

    LCD_RW_WRITE = 0
    LCD_RW_READ = 1

    def __init__(self, num_lines, num_columns):
        self.num_lines = num_lines
        if self.num_lines > 4:
            self.num_lines = 4
        self.num_columns = num_columns
        if self.num_columns > 40:
            self.num_columns = 40
        self.cursor_x = 0
        self.cursor_y = 0
        self.implied_newline = False
        self.backlight = True
        self.display_off()
        self.backlight_on()
        self.clear()
        self.hal_write_command(self.LCD_ENTRY_MODE | self.LCD_ENTRY_INC)
        self.hide_cursor()
        self.display_on()

    def clear(self):
        """Clears the LCD display and moves the cursor to the top left corner"""
        self.hal_write_command(self.LCD_CLR)
        self.hal_write_command(self.LCD_HOME)
        self.cursor_x = 0
        self.cursor_y = 0

    def show_cursor(self):
        """Causes the cursor to be made visible"""
        self.hal_write_command(
            self.LCD_ON_CTRL | self.LCD_ON_DISPLAY | self.LCD_ON_CURSOR
        )

    def hide_cursor(self):
        """Hiddens the cursor"""
        self.hal_write_command(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY)

    def blink_cursor_on(self):
        """Turns on the cursor, and makes it blink"""
        self.hal_write_command(
            self.LCD_ON_CTRL
            | self.LCD_ON_DISPLAY
            | self.LCD_ON_CURSOR
            | self.LCD_ON_BLINK
        )

    def blink_cursor_off(self):
        """Turns on the cursor, and makes it no blink"""
        self.hal_write_command(
            self.LCD_ON_CTRL | self.LCD_ON_DISPLAY | self.LCD_ON_CURSOR
        )

    def display_on(self):
        """Turns on the LCD"""
        self.hal_write_command(self.LCD_ON_CTRL | self.LCD_ON_DISPLAY)

    def display_off(self):
        """Turns off the LCD"""
        self.hal_write_command(self.LCD_ON_CTRL)

    def backlight_on(self):
        """Turns the backlight on"""
        self.backlight = True
        self.hal_backlight_on()

    def backlight_off(self):
        """Turns the backlight off"""
        self.backlight = False
        self.hal_backlight_off()

    def move_to(self, cursor_x, cursor_y):
        """Moves the cursor position to the indicated position. The cursor
        position is zero based"""
        self.cursor_x = cursor_x
        self.cursor_y = cursor_y
        addr = cursor_x & 0x3F
        if cursor_y & 1:
            addr += 0x40
        if cursor_y & 2:
            addr += 0x14
        self.hal_write_command(self.LCD_DDRAM | addr)

    def putchar(self, char):
        """Writes the indicated character to the LCD at the current cursor
        position, and advances the cursor by one position"""
        if char == "\n":
            if self.implied_newline:
                self.hal_write_data(ord(" "))
            self.implied_newline = False
            self.move_to(0, (self.cursor_y + 1) % self.num_lines)
        else:
            self.hal_write_data(ord(char))
            self.cursor_x += 1
            if self.cursor_x >= self.num_columns:
                self.cursor_x = 0
                self.cursor_y += 1
                self.implied_newline = char != " "
            if self.cursor_y >= self.num_lines:
                self.cursor_y = 0
            self.move_to(self.cursor_x, self.cursor_y)

    def putstr(self, string):
        """Write the indicated string to the LCD at the current cursor
        position and advances the cursor position appropriately"""
        for char in string:
            self.putchar(char)

    def custom_char(self, location, charmap):
        """Write a character to one of the 8 CGRAM locations, available
        as chr(0) through chr(7)"""
        location &= 0x7
        self.hal_write_command(self.LCD_CGRAM | (location << 3))
        self.hal_sleep_us(40)
        for i in range(8):
            self.hal_write_data(charmap[i])
            self.hal_sleep_us(40)
        self.move_to(self.cursor_x, self.cursor_y)

    def hal_backlight_on(self):
        """Allows the hal layer to turn the backlight on"""
        pass

    def hal_backlight_off(self):
        """Allows the hal layer to turn the backlight off"""
        pass

    def hal_write_command(self, cmd):
        """Write a command to the LCD.
        Data is latched on the falling edge of E"""
        raise NotImplementedError

    def hal_write_data(self, data):
        """Write data to the LCD.
        Data is latched on the falling edge of E"""
        raise NotImplementedError

    def hal_sleep_us(self, usecs):
        """Sleep for some number of microseconds"""
        time.sleep_us(usecs)
