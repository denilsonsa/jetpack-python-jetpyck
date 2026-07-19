"""jetpyck.gfxdat is a module for handling Jetpack `*.DAT` files containing
graphic assets.

Both the shareware version and the full version have the exact same graphic
assets, and they are stored in files named `JETPACK?.DAT`:

* `JETPACK0.DAT` contains the tileset for rendering the levels, the player, and
  the enemies. It also contains the characters for rendering the text.
* `JETPACK1.DAT` contains some large graphic assets:
    * the High Scores header and frame
    * the Jetpack logo
    * the background of the main menu
    * the "UNREGISTERED!" graphic in the shareware version
    * the border around the fuel bar
    * the arrows on the list of custom levels
    * the splash screen before entering a level
* `JETPACK2.DAT` contains the entire main menu screen background
* `JETPACK3.DAT` contains the fourth help screen: the jetpack.
* `JETPACK4.DAT` contains the first help screen: list of game controls.
* `JETPACK5.DAT` contains the fifth help screen: a large version of the tiles.

The Christmas Special version uses the same filenames, but the data is
encoded in a completely different way. This encoding is still unknown, and thus
still unsupported in this module. There is an additional `JETPACK6.DAT` file in
this version, and due to its considerably larger size, it is believed to
contain the images displayed when exiting the game.

## JSWITCH - Jetpack Graphics Module Switcher

The full game is distributed with an external tool `JSWITCH.EXE` to change the
in-game level graphics. This is accomplished by having extra graphics modules
as additional files, and the tool will overwrite the main `JETPACK0.DAT` with
the selected one.

Each additional graphics module is distributed as two files:

* `_JETP_A0.DAT` contains the graphics.
* `_JETP_A.DAT` contains the name of this graphics module.

Different modules will have a different letter. These three are distributed
with the main game:

* `_JETP_A0.DAT` and `_JETP_A.DAT`: Regular Jetpack
* `_JETP_B0.DAT` and `_JETP_B.DAT`: Christmas Jetpack
* `_JETP_C0.DAT` and `_JETP_C.DAT`: Jetpack Junior!

Users have created more modules, and they are distributed as other letters.

Upon running, the `JSWITCH.EXE` tool finds all available graphics modules in
the current directory and asks the user to pick one (by choosing a letter).
Then it will overwrite `JETPACK0.DAT` with the corresponding `_JETP_?0.DAT`
file. It will also write a simple one-byte file `_JETP_.DAT` containing the
currently selected choice: b`\x00` for `A`, b`\x01` for B, and so on. In other
words, the byte is the zero-based index of the letter in alphabetical order.

"""

from collections.abc import Iterable
from itertools import batched
from warnings import warn

# Please install `pillow`, it's the most popular library for working with
# images in Python.
from PIL import Image

__all__ = [
    # Not including this in the default "*" import.
    # It's not generally useful outside this module.
    # Yet, if anyone wants, it's always possible to explicitly import it.
    # "BitGenerator",
]


# TODO: Document the code in this module!
# Also refactor this code as needed!
# I should probably create a new class JetpackGfx instead of the plain function gfxdat_parser()


def jswitch_name_decode(data: Iterable[int]) -> str:
    return bytes(b ^ 52 for b in data).decode("ascii")


def jswitch_name_encode(name: str) -> bytes:
    return bytes(b ^ 52 for b in name.encode("ascii"))


class BitGenerator:
    def __init__(self, data: bytes):
        self.data = data
        self.pointer = 0
        self.buffer: list[int] = []

    def remaining_bits(self) -> int:
        return len(self.buffer) + len(self.data) - self.pointer

    def is_empty(self) -> bool:
        return self.pointer >= len(self.data) and len(self.buffer) == 0

    def consume_byte(self) -> int:
        out = self.data[self.pointer]
        self.pointer += 1
        return out

    def get_bit(self) -> int:
        if len(self.buffer) == 0:
            self.buffer.extend(int(bit) for bit in "{:08b}".format(self.consume_byte()))
        return self.buffer.pop(0)

    def get_bits(self, how_many: int) -> int:
        out = 0
        for i in range(how_many):
            out <<= 1
            out |= self.get_bit()
        return out

    def get_byte(self) -> int:
        return self.get_bits(8)


def gfxdat_parser(rawdata: bytes) -> Image.Image:
    # Raw palette has one byte per channel (R, G, B).
    # Each channel is 6-bit (0..63), as per VGA palette limitation.
    rawpalette = rawdata[: 256 * 3]
    # Compressed stream of pixels.
    rawpixels = rawdata[256 * 3 :]

    # One byte per channel (R, G, B), 8-bit per channel.
    palette = bytearray(round(c * 255 / 63) for c in rawpalette)

    # Our framebuffer where the compressed image will be uncompresed.
    pixels = bytearray(320 * 200)
    pointer = 0

    stream = BitGenerator(rawpixels)
    while pointer < len(pixels):
        is_repeating = stream.get_bit()
        qty = 1
        if is_repeating:
            qty = 2 + stream.get_bits(5)
        colorindex = stream.get_byte()
        for i in range(qty):
            pixels[pointer] = colorindex
            pointer += 1

    if (remainder := stream.remaining_bits()) >= 8:
        print(
            "Warning: {} trailing bytes ({} bits) are being ignored after the pixel data.".format(
                remainder // 8, remainder
            )
        )

    img = Image.new(mode="P", size=(320, 200))
    img.putpalette(palette)
    img.putdata(pixels)

    return img
