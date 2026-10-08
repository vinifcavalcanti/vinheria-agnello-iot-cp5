
import time
from lcd_api import LcdApi


class I2cLcd(LcdApi):
    MASK_RS = 0x01
    MASK_ENABLE = 0x04
    MASK_BACKLIGHT = 0x08

    def __init__(self, i2c, endereco, linhas=2, colunas=16):
        self.i2c = i2c
        self.endereco = endereco
        self.backlight = self.MASK_BACKLIGHT

        super().__init__(linhas, colunas)

        time.sleep_ms(50)

        # Inicializa o LCD no modo de 4 bits.
        for _ in range(3):
            self._enviar_nibble(0x30)
            time.sleep_ms(5)

        self._enviar_nibble(0x20)
        time.sleep_ms(1)

        self.hal_write_command(
            self.LCD_FUNCTION | self.LCD_FUNCTION_2LINES
        )
        self.hal_write_command(
            self.LCD_ON_CTRL | self.LCD_ON_DISPLAY
        )
        self.clear()
        self.hal_write_command(
            self.LCD_ENTRY_MODE | self.LCD_ENTRY_INC
        )

    def _enviar_nibble(self, dado):
        valor = dado | self.backlight

        self._escrever(valor)
        self._escrever(valor | self.MASK_ENABLE)
        time.sleep_us(1)
        self._escrever(valor)

    def _escrever(self, valor):
        self.i2c.writeto(self.endereco, bytes([valor]))

    def _enviar_byte(self, dado, modo):
        self._enviar_nibble((dado & 0xF0) | modo)
        self._enviar_nibble(((dado << 4) & 0xF0) | modo)

    def hal_write_command(self, comando):
        self._enviar_byte(comando, 0)

    def hal_write_data(self, dado):
        self._enviar_byte(dado, self.MASK_RS)
