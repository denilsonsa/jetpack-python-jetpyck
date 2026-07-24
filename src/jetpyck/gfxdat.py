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

## SCLM.DAT

`SCLM.DAT` contains the short intro animation for the company logo.

On older releases, it had 54508 bytes and showed:

> PRESENTED BY
> Software Creations
> HOME OF THE AUTHORS

On the newer releases (such as the 1.5 freeware full version), it has 40235
bytes and shows the IMPULSE logo.

The file format is exactly the same across versions. In fact, it is possible to
overwrite the `SCLM.DAT` file from one version onto another version, and the
animation will play correctly.

However, the encoding is still unknown, and thus still unsupported in this
module.

## Color cycling

Color cycling was a common technique for creating animations on palette-based
graphics using very few resources. Since the pixels are just indexes to a color
palette, it is possible to render animations by just changing the RGB values of
certain colors of the palette. This requires very little extra storage (a few
bytes to define which colors have to be changed) and very little CPU usage
(computing the new colors and updating those colors in the palette), while
changing the colors of all pixels on the screen that point to the affected
indexes. Although limited, this is much cheaper than having multiple frames of
animation.

* <https://en.wikipedia.org/wiki/Color_cycling>
* <https://amiga.lychesis.net/specials/ColorCycling.html>
* <https://www.youtube.com/watch?v=aMcJ1Jvtef0>

[Deluxe Paint](https://en.wikipedia.org/wiki/Deluxe_Paint) was likely the most
famous bitmap graphics editor (or pixel art editor) around 1985 to 1995.
Originating from Amiga and later also released for DOS, it had color cycling
support since its first version.

In modern era, very few editors have native support for color cycling
animations:

* [DPaint.js](https://github.com/steffest/dpaint-js)
* [PyDPainter](https://github.com/mriale/PyDPainter)
* [Pro Motion](https://www.cosmigo.com/pixel_animation_software/features)

[This feature is planned](https://github.com/aseprite/aseprite/issues/1067),
but not yet implemented, in [Aseprite](https://github.com/aseprite/aseprite).

Regarding common file formats, only [ILBM](https://en.wikipedia.org/wiki/ILBM)
(Interleaved Bitmap) files have native support for storing color cycles, which
is stored inside `CRNG` chunks.

## Color cycling in Jetpack

JetPack implemented the following animations as just color cycles:

* flashing dashes at the main menu items
* blinking lights at the jetpack picture in the help screen
* blinking light on top of the jetpack of the player sprite
* rotating stunner power-up item
* flashing shield power-up item
* blinking light at the trackbot enemy
* blinking/spinning homer enemy
* blinking squares for the energy charger tiles
* walking lines for the energy drain tiles
* conveyor belt movement
* stairs moving up or down
* red pulsing effect at the high scores screen

The game runs in VGA mode `13h`, which runs at 70Hz. The game updates the
palette once every 4 frames in average, which means around 17.5Hz or about 57ms
between each step of the color cycling animation.

There are three color ranges that get animated:

* 4 colors (from 247 until 250)
    * white → middle gray → dark gray → middle gray
    * colors shifted forward (i.e. 248 receives the RGB color from 247, and
      247 receives from 250)
    * used for the stairs, and for the jetpack
* 4 colors (from 251 until 254)
    * dark gray → gradient → light gray
    * colors shifted forward (i.e. 252 receives the RGB color from 251, and
      251 receives from 254)
    * used for the power-up items, for the conveyor belts, for the energy
      charger/drain tiles, and for the trackbot and homer enemies
* 16 colors (from 32 until 47)
    * red → gradient → white
    * only used for the high scores screen
    * this color range is shared with other graphical elements, but those
      elements are not displayed in the high scores screen, and thus they are
      not animated

The two 4-color cycles (located at the end of the palette) are cycling
throughout the entire game, even during the high scores.

"""

import math
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import IntEnum
from functools import reduce
from io import BytesIO
from itertools import batched, chain
from typing import IO, Iterator, Optional, Self
from warnings import warn

# Please install `pillow`, it's the most popular library for working with
# images in Python.
from PIL import Image
from PIL._typing import StrOrBytesPath

from .rle import JetpackRLEDecoder

PILFileParameter = StrOrBytesPath | IO[bytes]

__all__ = [
    "JetpackColorCycleDirection",
    "JetpackColorCycle",
    "JetpackGfx",
    # Not including this in the default "*" import.
    # It's not generally useful outside this module.
    # Yet, if anyone wants, it's always possible to explicitly import it.
    # "BitGenerator",
    #
    # Not including these functions in the default "*" import.
    # If anyone wants, just import them explicitly.
    # "jswitch_name_decode",
    # "jswitch_name_encode",
    # TODO: Add stuff here.
]


# TODO: Document the code in this module!
# Also refactor this code as needed!
# I should probably create a new class JetpackGfx instead of the plain function gfxdat_parser()


def jswitch_name_decode(data: Iterable[int]) -> str:
    r"""Decodes a name from JSWITCH.EXE graphics module format.

    These are the small files named `_JETP_?.DAT`.

    ---

    Example of decoding the names from graphics modules:

    >>> # binname = Path('_JETP_A.DAT').read_bytes()
    >>> binname = b'fQSAXUF\x14~Q@DUW_'
    >>> jswitch_name_decode(binname)
    'Regular Jetpack'
    >>> binname == jswitch_name_encode(jswitch_name_decode(binname))
    True
    """
    return bytes(b ^ 52 for b in data).decode("ascii")


def jswitch_name_encode(name: str) -> bytes:
    r"""Encodes a name to JSWITCH.EXE graphics module format.

    These are the small files named `_JETP_?.DAT`.
    """
    return bytes(b ^ 52 for b in name.encode("ascii"))


def color_6bit_to_8bit(channel: int) -> int:
    """Given a 6-bit value (from VGA), convert to an 8-bit value (for RGB8).

    >>> color_6bit_to_8bit(0)
    0
    >>> color_6bit_to_8bit(31)
    125
    >>> color_6bit_to_8bit(32)
    130
    >>> color_6bit_to_8bit(63)
    255

    Converting VGA -> RGB8 -> VGA should return to the same color.

    >>> for x in range(64):
    ...     y = color_6bit_to_8bit(x)
    ...     z = color_8bit_to_6bit(y)
    ...     assert x == z, "{} -> {} -> {}".format(x, y, z)

    The colors should be uniformly distributed.

    >>> rgb8 = [color_6bit_to_8bit(x) for x in range(64)]
    >>> from itertools import pairwise
    >>> deltas = [next - prev for prev, next in pairwise(rgb8)]
    >>> len(deltas)
    63
    >>> expected = (([4] * 15) + [5]) * 4
    >>> expected = expected[:-1]
    >>> assert deltas == expected, (deltas, expected)

    >>> color_6bit_to_8bit(-1)
    Traceback (most recent call last):
    ...
    ValueError: ...
    >>> color_6bit_to_8bit(64)
    Traceback (most recent call last):
    ...
    ValueError: ...
    """

    if 0 <= channel < 64:
        return (channel << 2) | (channel >> 4)
    else:
        raise ValueError(
            "Color channel out of range, got {} but expected 0..63".format(channel)
        )


def color_8bit_to_6bit(channel: int) -> int:
    """Given an 8-bit value (from RGB8), convert to a 6-bit value (for VGA).

    >>> color_8bit_to_6bit(0)
    0
    >>> color_8bit_to_6bit(31)
    7
    >>> color_8bit_to_6bit(63)
    15
    >>> color_8bit_to_6bit(127)
    31
    >>> color_8bit_to_6bit(255)
    63

    Converting from 256 colors to 64 colors results in groups of 4 duplicate colors.

    >>> rgb6 = [color_8bit_to_6bit(x) for x in range(256)]
    >>> from itertools import chain
    >>> expected = list(chain.from_iterable([c] * 4 for c in range(64)))
    >>> assert rgb6 == expected, rgb6

    >>> color_8bit_to_6bit(-1)
    Traceback (most recent call last):
    ...
    ValueError: ...
    >>> color_8bit_to_6bit(256)
    Traceback (most recent call last):
    ...
    ValueError: ...
    """

    if 0 <= channel < 256:
        return channel >> 2
    else:
        raise ValueError(
            "Color channel out of range, got {} but expected 0..255".format(channel)
        )


class JetpackColorCycleDirection(IntEnum):
    Forward = 1
    Backward = -1
    Bounce = 2
    ReverseBounce = -2

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        return f"{cls_name}.{self.name}"


@dataclass(order=True)
class JetpackColorCycle:
    """A color cycle is defined by:

    - `first`: the index of the first color of the cycle
    - `last`: the index of the last color of the cycle
    - `direction`: how the colors are going to move

    Observe how the limits of the color cycle are inclusive, which is different
    from Python's range() behavior (where the second limit is exclusive).

    ---

    These color cycling ranges are hard-coded into the game:

    >>> JetpackColorCycle.stairs()
    JetpackColorCycle(first=247, last=250, direction=JetpackColorCycleDirection.Backward)
    >>> JetpackColorCycle.belts()
    JetpackColorCycle(first=251, last=254, direction=JetpackColorCycleDirection.Backward)
    >>> JetpackColorCycle.high_scores()
    JetpackColorCycle(first=32, last=47, direction=JetpackColorCycleDirection.Bounce)

    These objects are sortable.

    >>> JetpackColorCycle.stairs() < JetpackColorCycle.belts()
    True
    >>> JetpackColorCycle.stairs() > JetpackColorCycle.belts()
    False

    It's possible to create custom color cycling ranges, but these cannot be
    used in the game. Still, they are useful for testing and for demonstrating
    how this class works.

    >>> cycle = JetpackColorCycle(2, 5)
    >>> cycle
    JetpackColorCycle(first=2, last=5, direction=JetpackColorCycleDirection.Forward)
    >>> len(cycle)
    4
    >>> cycle.n_frames
    4
    >>> cycle[1]
    3
    >>> cycle[-1]
    5
    >>> 1 in cycle
    False
    >>> 2 in cycle
    True
    >>> 3 in cycle
    True
    >>> 5 in cycle
    True
    >>> 6 in cycle
    False

    For testing purposes, let's use a small 8-color palette.

    >>> pal = bytes(range(65, 65 + 8 * 3))
    >>> pal
    b'ABCDEFGHIJKLMNOPQRSTUVWX'
    >>> cycle.rotate_palette(pal)
    b'ABCDEFPQRGHIJKLMNOSTUVWX'
    >>> cycle.rotate_palette(pal, 2)
    b'ABCDEFMNOPQRGHIJKLSTUVWX'
    >>> cycle.rotate_palette(cycle.rotate_palette(pal))
    b'ABCDEFMNOPQRGHIJKLSTUVWX'
    >>> cycle.rotate_palette(pal, 0) == pal
    True
    >>> cycle.rotate_palette(pal, len(cycle)) == pal
    True
    >>> cycle.rotate_palette(pal, 1 + len(cycle)) == cycle.rotate_palette(pal, 1)
    True
    >>> cycle.rotate_palette(pal, len(cycle) - 1) == cycle.rotate_palette(pal, -1)
    True

    >>> -cycle
    JetpackColorCycle(first=2, last=5, direction=JetpackColorCycleDirection.Backward)
    >>> (-(-cycle))
    JetpackColorCycle(first=2, last=5, direction=JetpackColorCycleDirection.Forward)
    >>> (-(-cycle)) == cycle
    True

    >>> (-cycle).rotate_palette(pal)
    b'ABCDEFJKLMNOPQRGHISTUVWX'
    >>> (-cycle).rotate_palette(pal, 2)
    b'ABCDEFMNOPQRGHIJKLSTUVWX'
    >>> cycle.rotate_palette(pal, len(cycle) - 1) == (-cycle).rotate_palette(pal, 1)
    True

    >>> bounce = JetpackColorCycle(2, 5, JetpackColorCycleDirection.Bounce)
    >>> bounce
    JetpackColorCycle(first=2, last=5, direction=JetpackColorCycleDirection.Bounce)
    >>> len(bounce)
    4
    >>> bounce.n_frames
    8
    >>> bounce.rotate_palette(pal)
    b'ABCDEFJKLMNOPQRGHISTUVWX'
    >>> bounce.rotate_palette(pal, 2)
    b'ABCDEFMNOPQRGHIJKLSTUVWX'
    >>> bounce.rotate_palette(pal, 3)
    b'ABCDEFPQRGHIJKLMNOSTUVWX'
    >>> bounce.rotate_palette(pal, 4)
    b'ABCDEFGHIJKLMNOPQRSTUVWX'
    >>> bounce.rotate_palette(pal, 5)
    b'ABCDEFPQRGHIJKLMNOSTUVWX'
    >>> bounce.rotate_palette(pal, 6)
    b'ABCDEFMNOPQRGHIJKLSTUVWX'
    >>> bounce.rotate_palette(pal, 7)
    b'ABCDEFJKLMNOPQRGHISTUVWX'
    >>> bounce.rotate_palette(pal, 8)
    b'ABCDEFGHIJKLMNOPQRSTUVWX'
    >>> for i in range(8, 24):
    ...     assert bounce.rotate_palette(pal, i) == bounce.rotate_palette(pal, i % bounce.n_frames), i
    >>> for i in range(16):
    ...     assert bounce.rotate_palette(pal, i) == (-bounce).rotate_palette(pal, bounce.n_frames - i), i
    """

    first: int
    last: int
    direction: JetpackColorCycleDirection = JetpackColorCycleDirection.Forward

    def __len__(self) -> int:
        """How many colors are contained in this color cycling range?"""
        assert self.last >= self.first
        return self.last - self.first + 1

    def __getitem__(self, index: int) -> int:
        if index < 0:
            ret = self.last + 1 + index
        else:
            ret = self.first + index
        if self.first <= ret <= self.last:
            return ret
        else:
            raise IndexError("Index {} is out of range".format(index))

    def __iter__(self) -> Iterator[int]:
        for i in range(len(self)):
            yield self[i]

    def __contains__(self, value: int) -> bool:
        return self.first <= value <= self.last

    def __neg__(self) -> Self:
        return self.__class__(
            self.first, self.last, direction=JetpackColorCycleDirection(-self.direction)
        )

    @property
    def n_frames(self) -> int:
        """Returns how many frames (or steps) are needed for one entire loop of
        this color cycling animation.
        """
        match self.direction:
            case (
                JetpackColorCycleDirection.Forward | JetpackColorCycleDirection.Backward
            ):
                return len(self)
            case (
                JetpackColorCycleDirection.Bounce
                | JetpackColorCycleDirection.ReverseBounce
            ):
                return 2 * len(self)
            case _:
                raise ValueError("Unsupported direction: {!r}".format(self.direction))

    def rotate_palette(self, pal: bytes | bytearray, step: int = 1) -> bytes:
        """Given a palette, returns a new palette after applying the color
        cycling.

        The `step` parameter defines how many cycles of animation have to be
        applied. `step=0` returns the palette unchanged, `step=1` returns how
        the palette will look after one frame, and so on until
        `step=self.n_frames-1`, which is the last frame of animation.
        `step=self.n_frames` is equivalent to `step=0`.
        """
        sign = {
            JetpackColorCycleDirection.Forward: -1,
            JetpackColorCycleDirection.Backward: +1,
            JetpackColorCycleDirection.Bounce: +1,
            JetpackColorCycleDirection.ReverseBounce: -1,
        }[self.direction]

        match self.direction:
            case (
                JetpackColorCycleDirection.Forward | JetpackColorCycleDirection.Backward
            ):
                offset = (sign * step) % len(self)
            case (
                JetpackColorCycleDirection.Bounce
                | JetpackColorCycleDirection.ReverseBounce
            ):
                offset = (step) % (2 * len(self))
                if offset >= len(self):
                    # Reversing the sign for the second half of the bounce
                    # color cycling animation.
                    offset = (-offset) % len(self)
            case _:
                raise ValueError("Unsupported direction: {!r}".format(self.direction))

        assert 0 <= offset < len(self)
        delta = offset * 3
        start = self.first * 3
        end = (self.last + 1) * 3

        return bytes(
            # Static prefix
            pal[:start]
            # Cycling this region
            + pal[start + delta : end]
            + pal[start : start + delta]
            # Static suffix
            + pal[end:]
        )

    @classmethod
    def stairs(cls) -> Self:
        """Hard-coded color cycling range used for the stairs."""
        return cls(247, 250, JetpackColorCycleDirection.Backward)

    @classmethod
    def belts(cls) -> Self:
        """Hard-coded color cycling range used for the conveyor belts."""
        return cls(251, 254, JetpackColorCycleDirection.Backward)

    @classmethod
    def high_scores(cls) -> Self:
        """Hard-coded color cycling range used for the conveyor belts."""
        return cls(32, 47, JetpackColorCycleDirection.Bounce)


class JetpackGfx:
    r"""Class representing one gfx image from Jetpack.

    Most of these images are stored as `JETPACK?.DAT`, with numbers increasing
    from `0`. These images are used for drawing all the graphics on screen.

    ---

    We can create an empty image from scratch. For convenience, it contains the
    default palette and the default color cycles.

    >>> gfx = JetpackGfx()

    >>> len(gfx.palette_vga)
    768
    >>> all(0 <= c < 64 for c in gfx.palette_vga)
    True
    >>> list(gfx.palette_vga[0*3 : 1*3])  # Black/transparent
    [0, 0, 0]
    >>> list(gfx.palette_vga[31*3 : 32*3])  # White
    [63, 63, 63]
    >>> list(gfx.palette_vga[40*3 : 41*3])  # Red
    [63, 0, 0]
    >>> list(gfx.palette_vga[104*3 : 105*3])  # Green
    [0, 63, 0]
    >>> list(gfx.palette_vga[152*3 : 153*3])  # Blue
    [0, 0, 63]

    >>> list(gfx.palette_vga) == list(JetpackGfx.default_palette_vga)
    True

    >>> gfx.width, gfx.height
    (320, 200)

    >>> gfx.color_cycles == [JetpackColorCycle.stairs(), JetpackColorCycle.belts()]
    True
    """

    # Mode 13h, or 0x13, sometimes called MCGA mode.
    # 320x200 70Hz with 256 simultaneous colors (out of 18-bit RGB)
    default_width = 320
    default_height = 200

    # 4 frames at 70HZ VGA output is 17.5Hz or about 57ms.
    default_frame_delay = 57

    # Change this class variable to a zoom level comfortable to you, when using
    # the Jupyter notebook.
    _ipython_diplay_zoom = 1

    # This is the default palette from the game.
    default_palette_vga = bytes(
        chain(
            # Black or transparent
            (0, 0, 0),  # 0
            # Gray scale
            (2, 2, 2),  # 1
            (4, 4, 4),  # 2
            (6, 6, 6),  # 3
            (8, 8, 8),  # 4
            (10, 10, 10),  # 5
            (12, 12, 12),  # 6
            (14, 14, 14),  # 7
            (16, 16, 16),  # 8
            (18, 18, 18),  # 9
            (20, 20, 20),  # 10
            (22, 22, 22),  # 11
            (24, 24, 24),  # 12
            (26, 26, 26),  # 13
            (28, 28, 28),  # 14
            (30, 30, 30),  # 15
            (32, 32, 32),  # 16
            (34, 34, 34),  # 17
            (36, 36, 36),  # 18
            (38, 38, 38),  # 19
            (41, 41, 41),  # 20
            (43, 43, 43),  # 21
            (45, 45, 45),  # 22
            (47, 47, 47),  # 23
            (48, 48, 48),  # 24
            (51, 51, 51),  # 25
            (53, 53, 53),  # 26
            (55, 55, 55),  # 27
            (57, 57, 57),  # 28
            (59, 59, 59),  # 29
            (61, 61, 61),  # 30
            (63, 63, 63),  # 31
            # Red scale (e.g. the rectangular bricks)
            (8, 0, 0),  # 32
            (15, 0, 0),  # 33
            (22, 0, 0),  # 34
            (29, 0, 0),  # 35
            (35, 0, 0),  # 36
            (42, 0, 0),  # 37
            (49, 0, 0),  # 38
            (56, 0, 0),  # 39
            (63, 0, 0),  # 40
            (63, 8, 8),  # 41
            (63, 16, 16),  # 42
            (63, 23, 23),  # 43
            (63, 31, 31),  # 44
            (63, 39, 39),  # 45
            (63, 46, 46),  # 46
            (63, 54, 54),  # 47
            # Orange scale (e.g. the square bricks)
            (8, 4, 0),  # 48
            (14, 7, 0),  # 49
            (21, 9, 0),  # 50
            (28, 10, 0),  # 51
            (35, 11, 0),  # 52
            (42, 11, 0),  # 53
            (49, 10, 0),  # 54
            (56, 9, 0),  # 55
            (63, 7, 0),  # 56
            (63, 16, 6),  # 57
            (63, 25, 14),  # 58
            (63, 33, 22),  # 59
            (63, 40, 30),  # 60
            (63, 47, 38),  # 61
            (63, 53, 46),  # 62
            (63, 58, 54),  # 63
            # Gold/Amber scale (e.g. the gold block and the yellow teleporter)
            (8, 6, 0),  # 64
            (15, 11, 0),  # 65
            (22, 16, 0),  # 66
            (29, 21, 0),  # 67
            (35, 26, 0),  # 68
            (42, 31, 0),  # 69
            (49, 35, 0),  # 70
            (56, 40, 0),  # 71
            (63, 46, 0),  # 72
            (63, 48, 8),  # 73
            (63, 50, 16),  # 74
            (63, 52, 23),  # 75
            (63, 55, 31),  # 76
            (63, 57, 39),  # 77
            (63, 59, 46),  # 78
            (63, 61, 54),  # 79
            # Yellow/Lemon scale (e.g. the pick-up items)
            (8, 7, 0),  # 80
            (15, 13, 0),  # 81
            (22, 19, 0),  # 82
            (29, 26, 0),  # 83
            (35, 32, 0),  # 84
            (42, 39, 0),  # 85
            (49, 46, 0),  # 86
            (56, 54, 0),  # 87
            (63, 61, 0),  # 88
            (63, 61, 8),  # 89
            (63, 61, 16),  # 90
            (63, 62, 23),  # 91
            (63, 63, 31),  # 92
            (63, 63, 39),  # 93
            (63, 63, 46),  # 94
            (63, 63, 54),  # 95
            # Green/Lime scale (e.g. the green teleporter, the gems, plants)
            (0, 8, 0),  # 96
            (0, 15, 0),  # 97
            (0, 22, 0),  # 98
            (0, 29, 0),  # 99
            (0, 35, 0),  # 100
            (0, 42, 0),  # 101
            (0, 49, 0),  # 102
            (0, 56, 0),  # 103
            (0, 63, 0),  # 104
            (8, 63, 8),  # 105
            (16, 63, 16),  # 106
            (24, 63, 23),  # 107
            (32, 63, 31),  # 108
            (39, 63, 39),  # 109
            (47, 63, 46),  # 110
            (54, 63, 54),  # 111
            # Teal/Cyan scale (e.g. the togglable blocks and switches)
            (1, 8, 6),  # 112
            (2, 15, 11),  # 113
            (3, 21, 16),  # 114
            (4, 28, 21),  # 115
            (5, 35, 26),  # 116
            (7, 41, 32),  # 117
            (8, 48, 38),  # 118
            (10, 55, 43),  # 119
            (12, 62, 49),  # 120
            (18, 62, 50),  # 121
            (24, 62, 52),  # 122
            (30, 62, 54),  # 123
            (36, 62, 55),  # 124
            (42, 63, 57),  # 125
            (48, 63, 59),  # 126
            (55, 63, 61),  # 127
            # Sky Blue scale (e.g. the steel ball enemy)
            (1, 6, 8),  # 128
            (2, 11, 15),  # 129
            (3, 16, 21),  # 130
            (3, 22, 28),  # 131
            (4, 27, 35),  # 132
            (5, 32, 41),  # 133
            (6, 38, 48),  # 134
            (7, 44, 55),  # 135
            (8, 49, 62),  # 136
            (15, 51, 62),  # 137
            (21, 52, 62),  # 138
            (28, 54, 62),  # 139
            (34, 55, 62),  # 140
            (41, 57, 63),  # 141
            (48, 59, 63),  # 142
            (55, 61, 63),  # 143
            # Navy Blue scale (e.g. the togglable blocks and switches)
            (0, 0, 8),  # 144
            (0, 0, 15),  # 145
            (0, 0, 22),  # 146
            (0, 0, 29),  # 147
            (0, 0, 35),  # 148
            (0, 0, 42),  # 149
            (0, 1, 49),  # 150
            (0, 1, 56),  # 151
            (0, 0, 63),  # 152
            (8, 9, 63),  # 153
            (16, 16, 63),  # 154
            (23, 24, 63),  # 155
            (31, 32, 63),  # 156
            (39, 39, 63),  # 157
            (46, 47, 63),  # 158
            (54, 54, 63),  # 159
            # Purple/Violet scale (e.g. the spikes enemy)
            (5, 0, 8),  # 160
            (9, 0, 15),  # 161
            (14, 0, 22),  # 162
            (18, 0, 29),  # 163
            (23, 0, 35),  # 164
            (27, 0, 42),  # 165
            (32, 0, 49),  # 166
            (37, 0, 56),  # 167
            (42, 0, 63),  # 168
            (45, 8, 63),  # 169
            (47, 16, 63),  # 170
            (50, 23, 63),  # 171
            (52, 31, 63),  # 172
            (54, 39, 63),  # 173
            (57, 46, 63),  # 174
            (60, 54, 63),  # 175
            # Pink/Magenta scale (e.g. the steel barrier and the teleporter)
            (8, 0, 7),  # 176
            (15, 0, 13),  # 177
            (22, 0, 19),  # 178
            (29, 0, 25),  # 179
            (35, 0, 31),  # 180
            (42, 0, 37),  # 181
            (49, 0, 44),  # 182
            (56, 0, 50),  # 183
            (63, 0, 56),  # 184
            (63, 8, 57),  # 185
            (63, 16, 58),  # 186
            (63, 23, 59),  # 187
            (63, 31, 59),  # 188
            (63, 39, 60),  # 189
            (63, 46, 61),  # 190
            (63, 54, 62),  # 191
            # Hot/Deep Pink scale (e.g. the batbot and the flitzer)
            (0, 0, 0),  # 192
            (8, 0, 3),  # 193
            (16, 0, 7),  # 194
            (24, 0, 10),  # 195
            (31, 0, 14),  # 196
            (39, 0, 17),  # 197
            (47, 0, 21),  # 198
            (55, 0, 24),  # 199
            (63, 0, 28),  # 200
            (63, 9, 33),  # 201
            (63, 18, 38),  # 202
            (63, 27, 43),  # 203
            (63, 36, 48),  # 204
            (63, 45, 53),  # 205
            (63, 54, 58),  # 206
            (63, 63, 63),  # 207
            # Brown/Wood scale (e.g. the wooden boxes)
            (10, 5, 0),  # 208
            (13, 7, 1),  # 209
            (16, 9, 2),  # 210
            (20, 12, 4),  # 211
            (23, 15, 6),  # 212
            (27, 18, 8),  # 213
            (30, 21, 11),  # 214
            (33, 25, 14),  # 215
            (37, 28, 18),  # 216
            (40, 32, 22),  # 217
            (44, 36, 27),  # 218
            (47, 40, 32),  # 219
            (50, 45, 37),  # 220
            (54, 49, 43),  # 221
            (57, 54, 49),  # 222
            (61, 59, 56),  # 223
            # Brown/Skin scale (e.g. the player skin)
            (24, 13, 10),  # 224
            (28, 15, 12),  # 225
            (33, 17, 13),  # 226
            (37, 20, 15),  # 227
            (42, 23, 16),  # 228
            (47, 25, 18),  # 229
            (48, 27, 21),  # 230
            (50, 30, 24),  # 231
            (51, 33, 27),  # 232
            (53, 36, 30),  # 233
            (55, 39, 34),  # 234
            (56, 42, 37),  # 235
            (58, 45, 41),  # 236
            (60, 49, 45),  # 237
            (61, 52, 48),  # 238
            (63, 56, 53),  # 239
            # Slate Gray mini-scale (unused?)
            (20, 23, 38),  # 240
            (24, 27, 38),  # 241
            (28, 31, 39),  # 242
            # Cyan mini-scale (e.g. the togglable blocks)
            (0, 28, 26),  # 243
            (0, 35, 33),  # 244
            (0, 42, 38),  # 245
            (0, 50, 47),  # 246
            # Ladder color cycle
            (57, 57, 58),  # 247
            (26, 26, 26),  # 248
            (10, 10, 10),  # 249
            (26, 26, 26),  # 250
            # Conveyor belt color cycle
            (26, 26, 26),  # 251
            (32, 32, 32),  # 252
            (41, 41, 41),  # 253
            (48, 48, 48),  # 254
            # White
            (63, 63, 63),  # 255
        )
    )

    def __init__(
        self,
        *,
        width: int = default_width,
        height: int = default_height,
    ):
        self.width = width
        self.height = height
        self.pixels: bytes | bytearray = bytearray(self.width * self.height)
        self.color_cycles = [
            JetpackColorCycle.stairs(),
            JetpackColorCycle.belts(),
        ]
        self.palette_vga: bytes | bytearray = bytearray(self.default_palette_vga)

    def __repr__(self) -> str:
        return "<JetpackGfx {}x{} {!r}>".format(self.width, self.height, id(self))

    def _repr_png_(self) -> bytes:
        """Renders this image as PNG, for display in Jupyter notebooks.

        This is a lie. Since this image is passed directly to the browser, the
        browser can just render other raster formats beyond PNG.

        In this case, it can render as WEBP instead of PNG. And WEBP is much
        smaller than GIF, and also smaller than APNG.
        """
        with BytesIO() as img:
            self.save_as_webp_animated(img, zoom=self._ipython_diplay_zoom)
            return img.getvalue()

    @property
    def palette_8bit(self) -> bytes:
        """Returns the palette as RGB 8-bit (per channel) palette.

        The Jetpack game stores the palette in VGA-friendly format, which is 3
        bytes for RGB, but each channel only has 6 bits (from 0 until 63). Each
        palette contains 256 colors out of a total of 262144 different colors
        (18-bit RGB).

        Most systems after VGA, and most file formats, use 8 bits per channel,
        for a total of 16 million colors (24-bit RGB). This is also known as
        RGB8 format.

        This property converts the internal VGA-style palette into RGB8,
        returning a `bytes` object.
        """
        return bytes(color_6bit_to_8bit(c) for c in self.palette_vga)

    @property
    def n_frames(self) -> int:
        """Returns how many frames (or steps) are needed for one entire loop of
        all color cycling animations together.

        In case the color cycling animations have different lengths, we want to
        return the least common multiple of them. This ensures the whole
        animation loops properly.
        """
        if len(self.color_cycles) == 0:
            return 1
        return math.lcm(*[cycle.n_frames for cycle in self.color_cycles])

    def generate_color_cycle_vga_palettes(self) -> list[bytes]:
        r"""Returns a list of VGA palettes after color cycling has been applied.

        This method can be used to generate the palettes required to convert
        the static image into an animated GIF.

        ---

        >>> static = JetpackGfx()
        >>> static.color_cycles = []
        >>> static.palette_vga = bytes(range(65, 65 + 8 * 3))
        >>> static.generate_color_cycle_vga_palettes()
        [b'ABCDEFGHIJKLMNOPQRSTUVWX']

        >>> gfx = JetpackGfx()
        >>> gfx.color_cycles = [
        ...     JetpackColorCycle(1, 3, JetpackColorCycleDirection.Forward),
        ...     JetpackColorCycle(4, 5, JetpackColorCycleDirection.Backward),
        ... ]
        >>> gfx.palette_vga = bytes(range(65, 65 + 8 * 3))
        >>> gfx.palette_vga
        b'ABCDEFGHIJKLMNOPQRSTUVWX'
        >>> print('\n'.join(repr(p) for p in gfx.generate_color_cycle_vga_palettes()))
        b'ABCDEFGHIJKLMNOPQRSTUVWX'
        b'ABCJKLDEFGHIPQRMNOSTUVWX'
        b'ABCGHIJKLDEFMNOPQRSTUVWX'
        b'ABCDEFGHIJKLPQRMNOSTUVWX'
        b'ABCJKLDEFGHIMNOPQRSTUVWX'
        b'ABCGHIJKLDEFPQRMNOSTUVWX'

        The color cycling ranges must not intersect. If they do, the colors
        will end up in unexpected places.

        >>> bad = JetpackGfx()
        >>> bad.color_cycles = [
        ...     JetpackColorCycle(1, 4, JetpackColorCycleDirection.Forward),
        ...     JetpackColorCycle(4, 5, JetpackColorCycleDirection.Backward),
        ... ]
        >>> bad.generate_color_cycle_vga_palettes()
        Traceback (most recent call last):
        ...
        ValueError: Color cycles must not intersect

        """
        if len(self.color_cycles) == 0:
            return [bytes(self.palette_vga)]

        # Sanity check, avoiding intersecting ranges.
        cnt = Counter(chain.from_iterable(self.color_cycles))
        if any(v > 1 for v in cnt.values()):
            raise ValueError("Color cycles must not intersect")

        return [
            reduce(
                lambda pal, cycle: cycle.rotate_palette(pal, i),
                self.color_cycles,
                bytes(self.palette_vga),
            )
            for i in range(self.n_frames)
        ]

    def generate_color_cycle_8bit_palettes(self) -> list[bytes]:
        """Returns a list of RGB8 palettes after color cycling has been applied."""
        return [
            bytes(color_6bit_to_8bit(c) for c in pal)
            for pal in self.generate_color_cycle_vga_palettes()
        ]

    def get_image(self, zoom: int = 1) -> Image.Image:
        """Converts this object into a PIL.Image Image."""
        if zoom < 1:
            raise ValueError("Zoom must be a positive integer")

        img = Image.frombytes(
            mode="P",
            size=(self.width, self.height),
            data=self.pixels,
            decoder_name="raw",
        )
        img.putpalette(self.palette_8bit)

        if zoom > 1:
            img = img.resize(
                (img.width * zoom, img.height * zoom), resample=Image.Resampling.NEAREST
            )
        return img

    def get_images(self, zoom: int = 1) -> list[Image.Image]:
        """Converts this object into a list of PIL.Image Images, cycling their
        palettes each frame for a full animation loop.
        """
        images = [self.get_image(zoom)]
        palettes = self.generate_color_cycle_8bit_palettes()
        for pal in palettes[1:]:
            frame = images[0].copy()
            frame.putpalette(pal)
            images.append(frame)

        return images

    def save_as_bmp(self, fp: PILFileParameter, zoom: int = 1) -> None:
        # This preserves the palette.
        # This file format has no compression and leads to large file sizes.
        # It technically supports some compression, but many (old) applications
        # cannot open compressed BMP files.
        image = self.get_image(zoom)
        image.save(
            fp,
            format="bmp",
        )

    def save_as_pcx(self, fp: PILFileParameter, zoom: int = 1) -> None:
        # This preserves the palette.
        # This file format has a very basic compression and leads to large file
        # sizes.
        image = self.get_image(zoom)
        image.save(
            fp,
            format="pcx",
        )

    def save_as_gif(self, fp: PILFileParameter, zoom: int = 1) -> None:
        # This preserves the palette.
        # A single-frame GIF can keep the original palette.
        image = self.get_image(zoom)
        image.save(
            fp,
            format="gif",
            # Don't optimize the palette, keep it as is.
            optimize=False,
        )

    def save_as_gif_animated(self, fp: PILFileParameter, zoom: int = 1) -> None:
        # This discards the palette.
        # An animated GIF modifies the palette (e.g. by introducing a
        # transparent color) across multiple frames to optimize for file size.
        images = self.get_images(zoom)
        images[0].save(
            fp,
            format="gif",
            append_images=images[1:],
            duration=self.default_frame_delay,
            loop=0,
            # Let's not preserve the palette in animated GIFs. Instead, please
            # optimize the frames of animation for smaller file size.
            optimize=True,
        )

    def save_as_png(self, fp: PILFileParameter, zoom: int = 1) -> None:
        # This preserves the palette.
        image = self.get_image(zoom)
        image.save(
            fp,
            format="png",
            optimize=True,
            compress_level=9,
        )

    def save_as_webp(self, fp: PILFileParameter, zoom: int = 1) -> None:
        # This discards the palette.
        # WebP format has its own compression algorithms operating directly on
        # the RGB values and was never intended to preserve the original
        # palette. Even if internally the algorithm decides to create an
        # indexed palette, that internal palette won't preserve the original
        # color order. Additionally, it's an internal implementation detail and
        # is not exposed to applications.
        image = self.get_image(zoom)
        image.save(
            fp,
            format="webp",
            lossless=True,
            method=6,  # 0=fast, 6=slower
            minimize_size=True,
        )

    def save_as_webp_animated(self, fp: PILFileParameter, zoom: int = 1) -> None:
        # This discards the palette.
        images = self.get_images(zoom)
        images[0].save(
            fp,
            format="webp",
            append_images=images[1:],
            duration=self.default_frame_delay,
            loop=0,
            lossless=True,
            method=6,  # 0=fast, 6=slower
            minimize_size=True,
        )


def gfxdat_parser(rawdata: bytes) -> JetpackGfx:
    # Raw palette has one byte per channel (R, G, B).
    # Each channel is 6-bit (0..63), as per VGA palette limitation.
    rawpalette = rawdata[: 256 * 3]
    # Compressed stream of pixels.
    rawpixels = rawdata[256 * 3 :]

    # One byte per channel (R, G, B), 8-bit per channel.
    # palette = bytearray(round(c * 255 / 63) for c in rawpalette)

    # Our framebuffer where the compressed image will be uncompresed.
    # pixels = bytearray(320 * 200)
    with JetpackRLEDecoder(rawpixels) as decoder:
        pixels = decoder.read(320 * 200)
        assert len(pixels) == 320 * 200

    obj = JetpackGfx()
    obj.pixels = pixels
    obj.palette_vga = rawpalette
    return obj


# TODO: sanity check for tile consistency:
# - If the transparent tiles have a different sprite than the background tile, there will be graphical glitches. (e.g. the column, the vines, etc.). The non-transparent pixels should be exactly the same as the tile under it.
#
# TODO: level rendering: on the level editor, the transparent blocks always have a hard-coded 6x6 green square in the middle of the 12x12 tile. This is not part of the tileset.
#
# TODO: Fonts
# - Sanity check: If any font has a color value <=10, it will be rendered incorrectly. The original ones go from 11 to 31. (But often starting from 14.)
# - Sanity check: If the hyphen character has pixels of color 31, those pixels will become transparent at the main menu. In fact, anything under 15 probably looks wrong, and any mix between these groups will also look wrong: (15..17), (18..21), (22..29), (30)
#
# 45 characters: ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,-+:?!$/
#
# The main menu characters are drawn with an outline. The outline seems to be the same character sprite shape (i.e. color=0 stays 0), but with all the colors changed to the color=1. Then, the sprite is drawn 4 times: 1 pixel up, 1 pixel down, 1 pixel left, 1 pixel right. Finally the real sprite is drawn at the center.
#
# How to change the colors of the characters:
# - The initial font is in the top 32 colors of the palette, from 0 to 31.
# - Color 0 is the universal transparent color. It's also full black, but only when used at the background.
# - Color 1 is the darkest visible tone for a font.
# - Color 31 is full white.
# - Red goes from 32 to 47 (16 colors)
#   - 1 -> 31 (looks wrong)
#   - 2,3 -> 32
#   - 4,5 -> 33
#   - ...
#   - 28,29 -> 45
#   - 30,31 -> 46
#   - The value 47 is never reached with this formula
# - Formula seems to be: pixelcolor//2 + (basecolor-1)
# - The white main menu items also have a transformation, perhaps to make it brighter/bolder:
#   1 -> 255 (underflow?)
#   2 -> 1
#   3 -> 1
#   4 -> 2
#   (from 4 until 31) -> value - 2
# - But the original pixel color is shown at the bottom of the main menu.
#   from 1 to 31 -> 1 to 31
# - Even whiter (at the level description screen):
#   1 -> 254 (underflow)
#   2 -> 255 (underflow)
#   3 -> 0
#   4 -> 1
#   31 -> 28
#   (i.e. value - 3)
# - Bright blue (at the level saving screen)
#   1 -> 141 (looks wrong)
#   2,3 -> 142 (looks wrong)
#   4,5 -> 143 (looks wrong)
#   6,7 -> 144
#   ...
#   30,31 -> 156
# - Credits screen:
#   - In all cases, the color 1 is wrong (out-of-bounds). So, the values below are from 2 to 31.
#   - red: 32 to 46
#   - cyan: 128 to 142
#   - green: 96 to 110
#   - purple: 160 to 174
# - Help screen:
#   - gray color for most text, no color manipulation.
#   - Bright cyan/green:
#       1-5 -> underflows: 109 to 111
#       6,7 -> 112
#       30,31 -> 124
#   - Bright blue:
#       1-5 -> underflows: 125 to 127
#       6,7 -> 128
#       30,31 -> 140
# - Level editor and level test status bar and save screen:
#   - Blue:
#     1 -> 144
#     2,3 -> 145
#     30,31 -> 159
#   - Bright blue
#     1 to 9 -> 139 to 143 wrong colors
#     10,11 -> 144
#     30,31 -> 154
#   - Brightest green:
#     1 to 7 -> 108 to 111 (wrong!)
#     8,9 -> 112
#     30,31 -> 123
# - High scores
#   Gold (1st place):
#     1 to 3 -> 62 to 63 (wrong!)
#     4 to 31 -> 64 to 77
#   Silver (until 5th place):
#     as-is, no color shifting
#   Gray (until 15th place):
#     1 to 5 -> 251 to 255 (underflow)
#     6 -> 0 (wrong)
#     7 to 31 -> 1 to 25
#
# The dash from the level save cursor is peculiar. It seems to cycle (backwards) extremely fast while waiting for input (once per frame or even quicker) colors from 16 or 17 until 47. So, 32 colors, crossing the light grays and the reds. But this isn't a color palette cycle. It's changing the sprite color, likely changing the target offset color, using the same formula and logic as any other character.
#  starts: 1->17, 2,3->18 ... 30,31 -> 32
#  Then it +1 the destination range to start from 18
#  Then +1 again and again
#  Until 1->32 up to 31->47
#  Then it resets back to 1->17
# I'd guess this is updating as often as the game is trying to read input from the keyboard.
# Why is this a cycle of steps instead of 16? No idea.
#
# The dash from the main menu is also interesting.
#  0 -> 0 (transparent stays transparent)
#  1-> 226 (underflow)
#  21 -> 246 (underflow)
#  22 to 29 -> 247 to 254 (color cycling)
#  30 -> 255 (probably a mistake)
#  31 -> 0 (becomes transparent, oops!)
# The original graphics is a sequence of 31, 27, 23, 27, 31
#
# The text is written in plaintext in the `JETPACK.EXE`.
# The text is just C-style null-terminated strings.
# There is a simple formatting language:
#   {159}TAB{031}-{123}FILES
# This is the main menu:
#   "  {046}S{000}-{029}START      {110}H{000}-{029}HELP"
#   "  {062}E{000}-{029}EDITOR     {110}B{000}-{029}BEST"
#   "  {046}Q{000}-{029}QUIT"
# The number inside curly braces is the target color for the font color 31, AKA the maximum color to be displayed.
# Apparently, if the tag is 031 (or any value under 32, probably), the colors are NOT divided by 2.
#
# Upon printing the text on the screen, there is a 1 pixel gap between each character. (In addition to the baked-in 1px gap in the default graphics.)
