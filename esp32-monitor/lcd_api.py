
import time


class LcdApi:
    LCD_CLR = 0x01
    LCD_HOME = 0x02
    LCD_ENTRY_MODE = 0x04
    LCD_ENTRY_INC = 0x02
    LCD_ON_CTRL = 0x08
    LCD_ON_DISPLAY = 0x04
    LCD_FUNCTION = 0x20
    LCD_FUNCTION_2LINES = 0x08
    LCD_DDRAM = 0x80

    def __init__(self, num_lines=2, num_columns=16):
        self.num_lines = num_lines
        self.num_columns = num_columns
        self.cursor_x = 0
        self.cursor_y = 0

    def clear(self):
        self.hal_write_command(self.LCD_CLR)
        time.sleep_ms(2)
        self.cursor_x = 0
        self.cursor_y = 0

    def move_to(self, col, row):
        self.cursor_x = col
        self.cursor_y = row
        endereco = col + (0x40 if row else 0)
        self.hal_write_command(self.LCD_DDRAM | endereco)

    def putstr(self, texto):
        for caractere in str(texto):
            if caractere == "\n":
                self.move_to(0, (self.cursor_y + 1) % self.num_lines)
            else:
                self.hal_write_data(ord(caractere))
                self.cursor_x += 1

    def hal_write_command(self, comando):
        raise NotImplementedError

    def hal_write_data(self, dado):
        raise NotImplementedError
