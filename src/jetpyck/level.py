"""jetpyck.level is a module for handling Jetpack levels.

The game is distributed with a pack of built-in levels at the `JETLEV.DAT`
file. The shareware version has 10 levels, the Christmas Special version has
another 10 levels, and the full game has 100 levels. The file format is
identical across these versions.

User-created levels are saved individually as `LEVELS/*.JET` files. The game
does not support subdirectories, all user-created levels are stored inside the
same directory. The shareware version can only save or load a single custom
level, with the name `REGISTER.JET`. The Christmas Special version is the same,
but with the `XMASLEVL.JET` name. The full version can save many levels with
any name (respecting the DOS limit of 8 characters plus the `.JET` extension).

## Serialization

Most classes have a pair of methods: `unpack` and `pack`.

For such classes, `unpack` is a classmethod that returns a new instance,
decoded from a byte stream. In other workds, `unpack` will create an object
instance from a serialized byte stream (e.g. from a file).

The opposite action is `pack`, which is an instance method to return an
encoded version as `bytes`. In other words, `pack` will serialize the object
into `bytes`, which can later be combined with other bytes and written to a
file.

There is a slight asymmetry in those methods. `unpack` expects to read from a
BinaryIO (e.g. from a file-like object). That's because it increments the
position in the stream while consuming the data. However, `pack` returns a
static `bytes` object, which is just a binary sequence. That's because this
binary data will likely be concatenated with others and further processed
before being written to a file.

## Naming is hard

Although the in-game help describes enemy "types", the word "type" has a very
specific meaning in programming languages. Thus, this module refers the enemy
"types" as "kinds". We have 8 enemy "kinds" in the game.
"""

__all__ = [
    "JetpackEnemyKind",
    "JetpackEnemy",
    "JetpackLevelTilemap",
    "JetpackLevel",
    "JetpackLevelPack",
]

import struct

from collections.abc import Iterable
from dataclasses import dataclass, field, KW_ONLY, InitVar
from enum import IntEnum
from io import BytesIO
from pathlib import Path
from warnings import warn

from typing import BinaryIO, ClassVar, Iterator, Optional, Self, overload

from .utils import unpack_int, unpack_ints, unpack_bytes


class JetpackEnemyKind(IntEnum):
    """There are 8 enemies in Jetpack.
    Enemies are active sprites that move in the level.

    As per the built-in help screens:
    > Eight different types of enemies
    > will try to put an end to your quest
    """

    NONE = 0
    # This guy will track you down
    TRACKBOT = 1
    # Rolls around crushing everything in its path
    STEEL_BALL = 2
    # Bounces up and down
    SPRING = 3
    # The fastest enemy, flies in a set pattern
    MISSILE = 4
    # Bounces in a diagonal path of destruction
    SPIKES = 5
    # Flitzes around randomly
    FLITZER = 6
    # Travels through bricks straight toward you
    HOMER = 7
    # Uses radar to hunt you down
    BATBOT = 8

    # TODO: Found in level 52 for some reason.
    # TODO: Likely leftover garbage data.
    UNKNOWN1 = 0x10
    UNKNOWN2 = 0x19


@dataclass(order=True)
class JetpackEnemy:
    r"""A single enemy instance in a level.

    Each enemy is encoded as 3 bytes:

    - 1 byte for the enemy kind.
    - 1 byte for the enemy x position
    - 1 byte for the enemy y position

    >>> e = JetpackEnemy(JetpackEnemyKind.FLITZER, 2, 3)
    >>> e.x, e.y
    (2, 3)
    >>> bindata = e.pack()
    >>> bindata
    b'\x06\x02\x03'
    >>> with BytesIO(bindata) as stream:
    ...     other = JetpackEnemy.unpack(stream)
    >>> e is other
    False
    >>> e == other
    True
    """

    kind: JetpackEnemyKind = JetpackEnemyKind.NONE
    x: int = 0
    y: int = 0

    @classmethod
    def unpack(cls, stream: BinaryIO) -> Self:
        obj = cls()
        obj.kind = JetpackEnemyKind(unpack_int("B", stream))
        obj.x, obj.y = unpack_ints("BB", stream)
        return obj

    def pack(self) -> bytes:
        return struct.pack("BBB", self.kind, self.x, self.y)


@dataclass
class JetpackLevelTilemap:
    r"""The static portion of the level (background+foreground) is a tilemap.
    Each level is a grid of 26 x 16 tiles, and each tile is a single byte.

    There are 120 different kinds of tiles.
    Each tile is represented as a single byte from 0 until 119.
    The tile selection screen from the level editor has all 120 tiles in order,
    from 0 until 119.

    The tilemap of each level is stored sequentially, left-to-right,
    top-to-bottom. First with the top-most row of tiles, then the next one,
    until the entire grid is serialized.

    For simplicity and convenience, this JetpackLevelTilemap class also behaves
    as a sequence. There is no need to access the internal `.data` structure.
    It also supports (x,y) as indexes.

    ---

    Creating a random-ish level binary data, including tiles beyond 119.

    >>> allbytes = bytes(i for i in range(256)) * 2
    >>> len(allbytes)
    512
    >>> allbytes[42]
    42
    >>> allbytes[42 + 256]
    42

    Reading that binary tilemap as a proper Tilemap object.

    >>> with BytesIO(allbytes) as stream:
    ...     othermap = JetpackLevelTilemap.unpack(stream)
    >>> othermap.width, othermap.height
    (26, 16)
    >>> len(othermap)
    416
    >>> len(othermap.data)  # Internal structure
    416

    Convenience function for iterating the tilemap.

    >>> for x, y, t in othermap.items():
    ...     if x > 4:
    ...         continue
    ...     if y > 2:
    ...         break
    ...     print('{},{}->{}'.format(x, y, t))
    0,0->0
    1,0->1
    2,0->2
    3,0->3
    4,0->4
    0,1->26
    1,1->27
    2,1->28
    3,1->29
    4,1->30
    0,2->52
    1,2->53
    2,2->54
    3,2->55
    4,2->56

    There are multiple ways to access the tile data.

    >>> othermap[4, 2]  # x,y indexing
    56
    >>> othermap[4 + 2 * 26]  # linear indexing
    56
    >>> othermap[65:70]  # linear indexing slice
    bytearray(b'ABCDE')

    Just like normal bytearray slices, the returned slice is a copy.
    Just like normal bytearray slices, it is possible to use the slice notation
    to replace a portion of the tilemap.

    But it is not allowed to mix the slice notation with the x,y coordinates.

    >>> othermap[1, 2:3]  # x,y indexing is not compatible with slices
    Traceback (most recent call last):
    ...
    TypeError: ...
    >>> othermap[(1, 2):3]  # x,y indexing is not compatible with slices
    Traceback (most recent call last):
    ...
    TypeError: ...
    >>> othermap[1, slice(2, 3)]  # x,y indexing is not compatible with slices
    Traceback (most recent call last):
    ...
    TypeError: ...

    Out-of-bounds are correctly checked.

    >>> othermap[othermap.width, 2]
    Traceback (most recent call last):
    ...
    IndexError: Out-of-bounds ...
    >>> othermap[3, othermap.height]
    Traceback (most recent call last):
    ...
    IndexError: Out-of-bounds ...
    >>> othermap[-1, 2]
    Traceback (most recent call last):
    ...
    IndexError: Out-of-bounds ...
    >>> othermap[3, -1]
    Traceback (most recent call last):
    ...
    IndexError: Out-of-bounds ...

    For the linear indexing, negative values are allowed.

    >>> othermap[len(othermap)]
    Traceback (most recent call last):
    ...
    IndexError: Out-of-bounds ...
    >>> othermap[-1]  # The last tile
    159

    Let's create another tilemap, this one from scratch.

    >>> editedmap = JetpackLevelTilemap()
    >>> editedmap.width, editedmap.height
    (26, 16)
    >>> len(editedmap)
    416
    >>> len(editedmap.data)  # Internal structure
    416
    >>> othermap == editedmap
    False

    Let's paint tiles into this new tilemap.

    >>> for i in range(len(editedmap)):
    ...     editedmap[i] = i % 256
    >>> othermap == editedmap
    True

    The serialized version of this tilemap should be identical.
    (The initial `allbytes` had trailing data beyond the tilemap.)

    >>> savedmap = editedmap.pack()
    >>> savedmap[:4]
    b'\x00\x01\x02\x03'
    >>> allbytes[0:len(savedmap)] == savedmap
    True

    For convenience, it is also possible to iterate the tilemap row-by-row.

    >>> from string import ascii_uppercase
    >>> editedmap[26:2*26] = ascii_uppercase.encode('ascii')
    >>> len(editedmap.data) == editedmap.width * editedmap.height
    True
    >>> rows = list(editedmap.rows())
    >>> len(rows)
    16
    >>> rows[1]
    bytearray(b'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    >>> rows[2]
    bytearray(b'456789:;<=>?@ABCDEFGHIJKLM')

    Although the original game has fixed level dimensions, this class supports
    other sizes as well.

    >>> normalmap = JetpackLevelTilemap()
    >>> normalmap  # doctest: +ELLIPSIS
    JetpackLevelTilemap(b'...')
    >>> normalmap.width, normalmap.height
    (26, 16)
    >>> small = JetpackLevelTilemap(width=6, height=4)
    >>> small  # doctest: +ELLIPSIS
    JetpackLevelTilemap(b'...', width=6, height=4)
    >>> len(small)
    24
    >>> len(small.data)
    24

    And if you ever edit the tile data, please make sure the amount of tiles is
    correct.

    >>> small.pack()  # doctest: +ELLIPSIS
    b'...'
    >>> small[0:5] = [1, 2, 3, 4]  # Oops! Too few tiles!
    >>> len(small.data)
    23
    >>> small.pack()
    Traceback (most recent call last):
    ...
    ValueError: ...
    >>> small[0:4] = [1, 2, 3, 4, 5, 6]  # Oops! Too many tiles!
    >>> len(small.data)
    25
    >>> small.pack()
    Traceback (most recent call last):
    ...
    ValueError: ...

    The tile data can be passed during initialization.

    >>> import random
    >>> JetpackLevelTilemap(random.randrange(40, 120) for i in range(26 * 16))  # doctest: +ELLIPSIS
    JetpackLevelTilemap(b'...')
    >>> JetpackLevelTilemap([0, 1, 2, 3], width=2, height=2)
    JetpackLevelTilemap(b'\x00\x01\x02\x03', width=2, height=2)
    >>> JetpackLevelTilemap(b'ABCDEF', width=3, height=2)
    JetpackLevelTilemap(b'ABCDEF', width=3, height=2)

    It doesn't matter if the parameter is mutable. The initialization always
    makes a copy of the parameter. This makes the code more predictable with
    fewer surprises.

    >>> mutable_param = bytearray(b'GHIJKL')
    >>> level = JetpackLevelTilemap(mutable_param, width=2, height=3)
    >>> level
    JetpackLevelTilemap(b'GHIJKL', width=2, height=3)
    >>> mutable_param[0] = b'XY'[0]
    >>> level[1] = b'XY'[1]
    >>> mutable_param
    bytearray(b'XHIJKL')
    >>> level
    JetpackLevelTilemap(b'GYIJKL', width=2, height=3)
    """

    # This internal data could have been implemented in several ways:
    # - bytes (immutable)
    # - bytearray (mutable array of bytes)
    # - array (mutable array of 8-bit integers or other word sizes)
    # I had to pick one, but any of these would have worked.
    data: bytearray = field(init=False)

    # The internal data structure is a bytearray, but the __init__ parameter is
    # an Iterable[int]. This "tiledata" parameter is converted to the internal
    # format in __post_init__.
    tiledata: InitVar[Optional[Iterable[int]]] = None

    # The other __init__ parameters are keyword-only.
    _: KW_ONLY

    # The original Jetpack levels are hard-coded to 26x16 tiles.
    default_width: ClassVar[int] = 26
    default_height: ClassVar[int] = 16
    width: int = default_width
    height: int = default_height

    def __post_init__(self, tiledata: Optional[Iterable[int]]) -> None:
        if tiledata is None:
            self.data = bytearray(self.width * self.height)
        else:
            self.data = bytearray(tiledata)

    def __repr__(self) -> str:
        if self.width == self.default_width and self.height == self.default_height:
            return "JetpackLevelTilemap({!r})".format(bytes(self.data))
        else:
            return "JetpackLevelTilemap({!r}, width={!r}, height={!r})".format(
                bytes(self.data), self.width, self.height
            )

    @classmethod
    def unpack(
        cls,
        stream: BinaryIO,
        *,
        width: Optional[int] = None,
        height: Optional[int] = None
    ) -> Self:
        obj = cls()

        # Allow overriding the original hard-coded level dimensions
        if width is not None:
            obj.width = width
        if height is not None:
            obj.height = height

        obj.data = bytearray(unpack_bytes("{}s".format(len(obj)), stream))
        return obj

    def pack(self) -> bytes:
        assert len(self) == self.width * self.height
        if len(self.data) != len(self):
            raise ValueError(
                "Data length mismatch. {} tiles found, but expected {}x{}={}".format(
                    len(self.data), self.width, self.height, self.width * self.height
                )
            )
        return bytes(self.data)

    def __len__(self) -> int:
        return self.width * self.height

    def __iter__(self) -> Iterator[int]:
        return iter(self.data)

    @overload
    def _subscript_to_index(self, subscript: int | tuple[int, int]) -> int: ...

    @overload
    def _subscript_to_index(self, subscript: slice) -> slice: ...

    def _subscript_to_index(
        self, subscript: int | slice | tuple[int, int]
    ) -> int | slice:
        """Supports multiple syntaxes:
        tilemap[123]   -> int in range 0..len(tilemap)-1
        tilemap[-123]  -> int in range -1..-len(tilemap)
        tilemap[4, 6]  -> separate coordinates for x and y
        tilemap[12:34] -> slice of two (or three) integers
        """
        if isinstance(subscript, (int, slice)):
            # Single integer, or a slice.
            return subscript
        elif isinstance(subscript, tuple):
            x, y = subscript
            if not isinstance(x, int) or not isinstance(y, int):
                raise TypeError(
                    "Expected x,y coordinates as int, got {!r},{!r}".format(x, y)
                )
            elif 0 <= x < self.width and 0 <= y < self.height:
                # Single integer.
                return x + y * self.width
            else:
                raise IndexError(
                    "Out-of-bounds x or y coordinates: {}, {}".format(x, y)
                )
        else:
            raise TypeError("Expected int or tuple, got {!r}".format(subscript))

    @overload
    def __getitem__(self, subscript: int | tuple[int, int]) -> int: ...

    @overload
    def __getitem__(self, subscript: slice) -> bytearray: ...

    def __getitem__(self, subscript: int | slice | tuple[int, int]) -> int | bytearray:
        index_or_slice = self._subscript_to_index(subscript)
        return self.data[index_or_slice]

    @overload
    def __setitem__(self, subscript: int | tuple[int, int], value: int) -> None: ...

    @overload
    def __setitem__(self, subscript: slice, value: Iterable[int]) -> None: ...

    def __setitem__(
        self, subscript: int | slice | tuple[int, int], value: int | Iterable[int]
    ) -> None:
        index_or_slice = self._subscript_to_index(subscript)
        # Duplication to make the `mypy` type checker happy.
        if isinstance(index_or_slice, int) and isinstance(value, int):
            self.data[index_or_slice] = value
        elif isinstance(index_or_slice, slice) and isinstance(value, Iterable):
            self.data[index_or_slice] = value
        else:
            raise TypeError(
                "Invalid types in the assignment: [{}] = {}.".format(
                    type(index_or_slice), type(value)
                )
            )

    def items(self) -> Iterable[tuple[int, int, int]]:
        """Generator of tuples (x, y, tile), for each of the tiles in this tilemap."""
        for y in range(self.height):
            for x in range(self.width):
                yield (x, y, self[x, y])

    def rows(self) -> Iterable[bytes | bytearray]:
        """Convenience function that returns (a copy of) each row separately."""
        for y in range(self.height):
            yield self.data[y * self.width : (y + 1) * self.width]


@dataclass
class JetpackLevel:
    r"""A Jetpack level is stored in a `.JET` file. The file structure is very
    straightforward.

    - 416 bytes for the 26x16
    - 2 bytes for the x,y position of the exit door (in range ??..??)
    - 2 bytes for the x,y the player start position (in range ??..??)
    - 60 bytes for the enemies (20 enemies in total)
    - 26 bytes for the level name (AKA description)

    For a total of 506 bytes.

    Thanks to https://gist.github.com/downerj/0bd0664cd407da0eb4d438531176fd37
    for the documentation of the format.

    ---

    TODO: Add tests loading a real-world level.

    >>> lvl = JetpackLevel(description=b'This is a test level      ')
    >>> print(lvl)
    <JetpackLevel "This is a test level      ">
    >>> lvl.door_x = 4
    >>> lvl.door_y = 5
    >>> lvl.player_x = 8
    >>> lvl.player_y = 9
    >>> lvl.tilemap.width, lvl.tilemap.height
    (26, 16)
    >>> for i in range(len(lvl.tilemap)):
    ...     lvl.tilemap[i] = i % 120
    >>> lvl.enemies[0].kind = JetpackEnemyKind.TRACKBOT
    >>> lvl.enemies[0].x = 15
    >>> lvl.enemies[0].y = 11
    >>> len(lvl.enemies)
    20

    >>> bindata = lvl.pack()
    >>> len(bindata)
    506
    >>> with BytesIO(bindata) as stream:
    ...     # Simulating a file object opened from a real file.
    ...     stream.name = 'EXAMPLE.JET'
    ...     loadedlvl = JetpackLevel.unpack(stream)
    >>> lvl.filename = 'EXAMPLE.JET'
    >>> lvl == loadedlvl
    True

    There are a couple of shortcuts for convenience.

    >>> lvl.tilemap.width
    26
    >>> lvl.width
    26
    >>> lvl.tilemap.height
    16
    >>> lvl.height
    16
    >>> lvl.width = 20
    Traceback (most recent call last):
    ...
    AttributeError: property 'width' of 'JetpackLevel' object has no setter
    >>> lvl.height = 20
    Traceback (most recent call last):
    ...
    AttributeError: property 'height' of 'JetpackLevel' object has no setter

    If for some reason the list of enemies is shorter than expected, the list
    is automatically expanded upon packing.

    >>> len(lvl.enemies)
    20
    >>> lvl.enemies = [JetpackEnemy(JetpackEnemyKind(i), i, i) for i in range(1,9)]
    >>> len(lvl.enemies)
    8
    >>> lvl.enemies[-1]
    JetpackEnemy(kind=<JetpackEnemyKind.BATBOT: 8>, x=8, y=8)
    >>> bindata = lvl.pack()
    >>> len(lvl.enemies)
    20
    >>> lvl.enemies[-1]
    JetpackEnemy(kind=<JetpackEnemyKind.NONE: 0>, x=0, y=0)
    >>> lvl.enemies.append(JetpackEnemy)
    >>> len(lvl.enemies)
    21
    >>> lvl.pack()
    Traceback (most recent call last):
    ...
    ValueError: ...
    """

    tilemap: JetpackLevelTilemap = field(default_factory=JetpackLevelTilemap)
    door_x: int = 0
    door_y: int = 0
    player_x: int = 0
    player_y: int = 0
    max_enemies: ClassVar[int] = 20
    # TODO: Perhaps make a copy of this list to reduce surprises?
    enemies: list[JetpackEnemy] = field(
        default_factory=lambda: [
            JetpackEnemy() for _ in range(JetpackLevel.max_enemies)
        ]
    )
    # TODO: Maybe the description should be `str` instead of `bytes`.
    # TODO: Maybe we should have a desc getter/setter that would automatically convert/pad/trim the description string.
    # TODO: Make a copy of this during initialization. Or perhaps just the setter is enough.
    description: bytes | bytearray = b" " * 26

    # Filename is optional, and is added here just for convenience.
    # It's an easy way to identify a level among many others inside any data structure.
    # TODO: Should it also support a Path in addition to str? I should pick one type and stick to it.
    filename: str | Path = ""

    # TODO: Idea: we can have a .sprites() function that returns a list of all sprites in the level.
    # In other words, it returns both enemies and the player and the door (with their respective coords).
    # To implement that, I can create a new class JetpackSpriteKind that derives from JetpackEnemyKind.
    # Why? Just because it simplifies the renderer.

    def __str__(self) -> str:
        return '<JetpackLevel {}"{}">'.format(
            "{:>12} ".format(self.filename) if self.filename else "",
            self.description.decode("ascii"),
        )

    @property
    def width(self) -> int:
        return self.tilemap.width

    @property
    def height(self) -> int:
        return self.tilemap.height

    @classmethod
    def unpack(cls, stream: BinaryIO, filename: Optional[str | Path] = None) -> Self:
        obj = cls()
        if filename is None:
            # Try getting the filename from the file-like object.
            name = getattr(stream, "name", None)
            obj.filename = name or ""
        else:
            # Preference for the explicit filename.
            obj.filename = filename

        obj.tilemap = JetpackLevelTilemap.unpack(stream)
        obj.door_x, obj.door_y = unpack_ints("BB", stream)
        obj.player_x, obj.player_y = unpack_ints("BB", stream)
        obj.enemies = [JetpackEnemy.unpack(stream) for _ in range(cls.max_enemies)]
        obj.description = unpack_bytes("26s", stream)
        return obj

    def pack(self) -> bytes:
        while len(self.enemies) < self.max_enemies:
            self.enemies.append(JetpackEnemy())
        if len(self.enemies) > self.max_enemies:
            raise ValueError(
                "Expected {} enemies, but {} are defined".format(
                    self.max_enemies, len(self.enemies)
                )
            )
        return b"".join(
            [
                self.tilemap.pack(),
                struct.pack("BB", self.door_x, self.door_y),
                struct.pack("BB", self.player_x, self.player_y),
                *(e.pack() for e in self.enemies),
                struct.pack("26s", self.description),
            ]
        )

    @classmethod
    def load_from_filename(cls, filename: str | Path) -> Self:
        """Creates a new JetpackLevel instance, loading from a file.

        These files are found at `LEVELS/*.JET`.
        """
        with Path(filename).open('rb') as f:
            return cls.unpack(f)

    @classmethod
    def load_from_bytes(cls, data: Sequence[int], filename: Optional[str | Path] = None) -> Self:
        """Creates a new JetpackLevel instance, loading from a `bytes` object.

        ---

        TODO: Add tests loading a real-world file.
        """
        with BytesIO(data) as stream:
            return cls.unpack(stream, filename=filename)

    def as_printable_text(self) -> str:
        """Returns a textual representation of the level.

        This could be named an ASCII Art rendering of the level, but it is
        using Unicode characters beyond the ASCII charset.
        """
        tileset = (
            " ‡†⸸●◌___◦•◦•◦•′″░░◎"
            "▴▴▴▲.  ♜█ ▒▒▓...▔▕▁▏"
            "▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒"
            "▓▓▓▓▓▓▓▓▓▓╳╳██▥▤▥▤▥▤"
            "▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▒▒▓"
            "▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▒▒▓"
        )
        return "\n".join(
            [
                str(self.description, encoding="ascii"),
                *("".join(tileset[t] for t in row) for row in self.tilemap.rows()),
            ]
        )

    def as_printable_half_blocks(self) -> str:
        """Returns a textual representation of the level.

        The level is rendered using "Block Elements" Unicode characters. Since
        fonts are usually taller than wider, this renders two tiles per
        character.
        """
        # Bit 0: top half
        # Bit 1: bottom half
        tileset = " ▀▄█"
        is_block = (
            "                    "
            "        # ###       "
            "####################"
            "####################"
            "####################"
            "####################"
        )
        ret = [str(self.description, encoding="ascii")]
        prev = bytearray(self.width)
        for n, row in enumerate(self.tilemap.rows()):
            bit = n % 2
            for x, tile in enumerate(row):
                if is_block[tile] != " ":
                    prev[x] |= 1 << bit
            if bit == 1 or n == self.tilemap.height - 1:
                ret.append("".join(tileset[c] for c in prev))
                for x in range(len(prev)):
                    prev[x] = 0

        return "\n".join(ret)

    def as_printable_sextant_blocks(self) -> str:
        """Returns a textual representation of the level.

        The level is rendered using "Symbols for Legacy Computing" Unicode
        characters. Each of these mosaic terminal graphic characters have a 2x3
        grid. This has been a recent addition to the Unicode standard, and many
        systems can't render it correctly.
        """
        # Bits:
        # 01 Top left and right
        # 23 Middle left and right
        # 45 Bottom left and right
        #
        # This lookup table contains characters from these ranges:
        #
        # * SPACE [U+0020]
        # * FULL BLOCK [U+2588]
        # * 2 HALF BLOCK [U+258C..U+2590]
        # * 60 BLOCK SEXTANT [U+1FB00..U+1FB3B]
        tileset = (
            " 🬀🬁🬂🬃🬄🬅🬆"
            "🬇🬈🬉🬊🬋🬌🬍🬎"
            "🬏🬐🬑🬒🬓▌🬔🬕"
            "🬖🬗🬘🬙🬚🬛🬜🬝"
            "🬞🬟🬠🬡🬢🬣🬤🬥"
            "🬦🬧▐🬨🬩🬪🬫🬬"
            "🬭🬮🬯🬰🬱🬲🬳🬴"
            "🬵🬶🬷🬸🬹🬺🬻█"
        )
        is_block = (
            "                    "
            "        # ###       "
            "####################"
            "####################"
            "####################"
            "####################"
        )
        ret = [
            str(line, encoding="ascii")
            for line in [self.description[:13], self.description[13:]]
        ]
        prev = bytearray(self.width // 2)
        for n, row in enumerate(self.tilemap.rows()):
            for x, tile in enumerate(row):
                bit = (n % 3) * 2 + (x % 2)
                if is_block[tile] != " ":
                    prev[x // 2] |= 1 << bit
            if (n % 3) == 2 or n == self.tilemap.height - 1:
                ret.append("".join(tileset[c] for c in prev))
                for x in range(len(prev)):
                    prev[x] = 0
        return "\n".join(ret)

    def as_printable_octant_blocks(self) -> str:
        """Returns a textual representation of the level.

        The level is rendered using "Symbols for Legacy Computing Supplement"
        Unicode characters. Each of these mosaic terminal graphic characters
        have a 2x4 grid. This has been a recent addition to the Unicode
        standard, and many systems can't render it correctly.

        See also: https://arewelegacycomputingyet.com/
        """
        # Bits:
        # 01 Top left and right
        # 23 Top-middle left and right
        # 45 Bottom-middle left and right
        # 67 Bottom left and right
        #
        # This is a lookup table because the list of OCTANT characters is
        # incomplete, because some of them are redundant. For instance,
        # "OCTANT-13" doesn't exist, as it is redundant to "QUADRANT UPPER
        # LEFT". Thus, instead of having 256 continuous values that we could
        # easily map using bit manipulation, Unicode decided we must use a
        # lookup table.
        #
        # This lookup table contains characters from these ranges:
        #
        # * SPACE [U+0020]
        # * FULL BLOCK [U+2588]
        # * 4 HALF BLOCK [U+2580..U+2590]
        # * 2 LOWER (ONE|THREE) QUARTER BLOCK [U+2582..U+2586]
        # * 2 UPPER (ONE|THREE) QUARTERS BLOCK [U+1FB82..U+1FB85]
        # * 10 QUADRANT [U+2596..U+259F]
        # * 4 (LEFT|RIGHT) HALF (UPPER|LOWER) ONE QUARTER BLOCK [U+1CEA0..U+1CEAB]
        # * 2 MIDDLE (LEFT|RIGHT) ONE QUARTER BLOCK [U+1FBE6..U+1FBE7]
        # * 230 OCTANT [U+1CD00..U+1CDE5]
        tileset = (
            " 𜺨𜺫🮂𜴀▘𜴁𜴂𜴃𜴄▝𜴅𜴆𜴇𜴈▀"
            "𜴉𜴊𜴋𜴌🯦𜴍𜴎𜴏𜴐𜴑𜴒𜴓𜴔𜴕𜴖𜴗"
            "𜴘𜴙𜴚𜴛𜴜𜴝𜴞𜴟🯧𜴠𜴡𜴢𜴣𜴤𜴥𜴦"
            "𜴧𜴨𜴩𜴪𜴫𜴬𜴭𜴮𜴯𜴰𜴱𜴲𜴳𜴴𜴵🮅"
            "𜺣𜴶𜴷𜴸𜴹𜴺𜴻𜴼𜴽𜴾𜴿𜵀𜵁𜵂𜵃𜵄"
            "▖𜵅𜵆𜵇𜵈▌𜵉𜵊𜵋𜵌▞𜵍𜵎𜵏𜵐▛"
            "𜵑𜵒𜵓𜵔𜵕𜵖𜵗𜵘𜵙𜵚𜵛𜵜𜵝𜵞𜵟𜵠"
            "𜵡𜵢𜵣𜵤𜵥𜵦𜵧𜵨𜵩𜵪𜵫𜵬𜵭𜵮𜵯𜵰"
            "𜺠𜵱𜵲𜵳𜵴𜵵𜵶𜵷𜵸𜵹𜵺𜵻𜵼𜵽𜵾𜵿"
            "𜶀𜶁𜶂𜶃𜶄𜶅𜶆𜶇𜶈𜶉𜶊𜶋𜶌𜶍𜶎𜶏"
            "▗𜶐𜶑𜶒𜶓▚𜶔𜶕𜶖𜶗▐𜶘𜶙𜶚𜶛▜"
            "𜶜𜶝𜶞𜶟𜶠𜶡𜶢𜶣𜶤𜶥𜶦𜶧𜶨𜶩𜶪𜶫"
            "▂𜶬𜶭𜶮𜶯𜶰𜶱𜶲𜶳𜶴𜶵𜶶𜶷𜶸𜶹𜶺"
            "𜶻𜶼𜶽𜶾𜶿𜷀𜷁𜷂𜷃𜷄𜷅𜷆𜷇𜷈𜷉𜷊"
            "𜷋𜷌𜷍𜷎𜷏𜷐𜷑𜷒𜷓𜷔𜷕𜷖𜷗𜷘𜷙𜷚"
            "▄𜷛𜷜𜷝𜷞▙𜷟𜷠𜷡𜷢▟𜷣▆𜷤𜷥█"
        )
        is_block = (
            "                    "
            "        # ###       "
            "####################"
            "####################"
            "####################"
            "####################"
        )
        ret = [
            str(line, encoding="ascii")
            for line in [self.description[:13], self.description[13:]]
        ]
        prev = bytearray(self.width // 2)
        for n, row in enumerate(self.tilemap.rows()):
            for x, tile in enumerate(row):
                bit = (n % 4) * 2 + (x % 2)
                if is_block[tile] != " ":
                    prev[x // 2] |= 1 << bit
            if (n % 4) == 3 or n == self.tilemap.height - 1:
                ret.append("".join(tileset[c] for c in prev))
                for x in range(len(prev)):
                    prev[x] = 0
        return "\n".join(ret)

    def as_printable_braille(self) -> str:
        """Returns a textual representation of the level.

        The level is rendered using "Braille Patterns" from Unicode. These are
        rendered as tiny dots in a 2x4 grid, per character, resulting in a very
        compact level render.
        """

        def to_braille(dots: int) -> str:
            # Input dots:
            # 01 Bits 0 and 1: top left and top right
            # 23 Bits 2 and 3: second row
            # 45 Bits 4 and 5: third row
            # 67 Bits 6 and 7: bottom row
            #
            # Braille:
            # 03
            # 14
            # 25
            # 67
            b0 = 1 if dots & (1 << 0) else 0
            b1 = 1 if dots & (1 << 2) else 0
            b2 = 1 if dots & (1 << 4) else 0
            b3 = 1 if dots & (1 << 1) else 0
            b4 = 1 if dots & (1 << 3) else 0
            b5 = 1 if dots & (1 << 5) else 0
            b6 = 1 if dots & (1 << 6) else 0
            b7 = 1 if dots & (1 << 7) else 0
            return chr(
                0x2800
                | (b0 << 0)
                | (b1 << 1)
                | (b2 << 2)
                | (b3 << 3)
                | (b4 << 4)
                | (b5 << 5)
                | (b6 << 6)
                | (b7 << 7)
            )

        is_block = (
            "                    "
            "        # ###       "
            "####################"
            "####################"
            "####################"
            "####################"
        )
        ret = [
            str(line, encoding="ascii")
            for line in [self.description[:13], self.description[13:]]
        ]
        prev = bytearray(self.width // 2)
        for n, row in enumerate(self.tilemap.rows()):
            for x, tile in enumerate(row):
                bit = (n % 4) * 2 + (x % 2)
                if is_block[tile] != " ":
                    prev[x // 2] |= 1 << bit
            if (n % 4) == 3 or n == self.tilemap.height - 1:
                ret.append("".join(to_braille(c) for c in prev))
                for x in range(len(prev)):
                    prev[x] = 0

        return "\n".join(ret)


@dataclass
class JetpackLevelPack:
    r"""A level pack is the collection of built-in standard Jetpack levels,
    located inside `JETLEV.DAT`.

    The format is simple:

    - 2 bytes matching exactly b'\x86\xE6'
    - JetpackLevel, 506 bytes each.

    The total filesize is (2 + 506 * how_many_levels) bytes.

    The exact same format is used for the freeware 1.5 version with 100 levels,
    for the Christmas Special with 10 levels, and for the shareware version
    with 10 levels.

    The meaning of the first two bytes is unknown.

    ---

    TODO: Add tests loading a real-world levelpack.

    >>> pack1 = JetpackLevelPack(levels=[
    ...     JetpackLevel(description=b'This is the first level   '),
    ...     JetpackLevel(description=b'This is the second level  '),
    ...     JetpackLevel(description=b'This is the fourth level  '),
    ...     JetpackLevel(description=b'This is the third level   '),
    ... ])

    For simplicity and convenience, this JetpackLevelPack class also behaves as
    a sequence.

    >>> pack1[2].description
    b'This is the fourth level  '
    >>> pack1[3].description
    b'This is the third level   '
    >>> pack1[2:4] = reversed(pack1[2:4])
    >>> pack1[2].description
    b'This is the third level   '
    >>> pack1[3].description
    b'This is the fourth level  '
    >>> pack1[-1].description
    b'This is the fourth level  '

    >>> for n, lvl in enumerate(pack1):
    ...     for i in range(len(lvl.tilemap)):
    ...         lvl.tilemap[i] = (i * (n+1)) % 120
    >>> pack1[2].tilemap[1]
    3
    >>> pack1[3].tilemap[2]
    8

    >>> bindata = pack1.pack()
    >>> 2 + 506 * 4
    2026
    >>> len(bindata)
    2026
    >>> bindata[0:2]
    b'\x86\xe6'

    >>> with BytesIO(bindata) as stream:
    ...     pack2 = JetpackLevelPack.unpack(stream)
    >>> pack1 == pack2
    True
    """

    magic: bytes = b"\x86\xe6"
    # TODO: Perhaps make a copy of this list to reduce surprises?
    levels: list[JetpackLevel] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.levels)

    def __iter__(self) -> Iterator[JetpackLevel]:
        return iter(self.levels)

    @overload
    def __getitem__(self, index_or_slice: int) -> JetpackLevel: ...

    @overload
    def __getitem__(self, index_or_slice: slice) -> list[JetpackLevel]: ...

    def __getitem__(
        self, index_or_slice: int | slice
    ) -> JetpackLevel | list[JetpackLevel]:
        return self.levels[index_or_slice]

    @overload
    def __setitem__(self, index_or_slice: int, value: JetpackLevel) -> None: ...

    @overload
    def __setitem__(
        self, index_or_slice: slice, value: Iterable[JetpackLevel]
    ) -> None: ...

    def __setitem__(
        self, index_or_slice: int | slice, value: JetpackLevel | Iterable[JetpackLevel]
    ) -> None:
        # Duplication to make the `mypy` type checker happy.
        if isinstance(index_or_slice, int) and isinstance(value, JetpackLevel):
            self.levels[index_or_slice] = value
        elif isinstance(index_or_slice, slice) and isinstance(value, Iterable):
            self.levels[index_or_slice] = value
        else:
            raise TypeError(
                "Invalid types in the assignment: [{}] = {}.".format(
                    type(index_or_slice), type(value)
                )
            )

    @classmethod
    def unpack(cls, stream: BinaryIO) -> Self:
        obj = cls()
        magic = unpack_bytes("2s", stream)
        if magic != obj.magic:
            warn(
                "Level pack magic number mismatch, expected {!r} but got {!r}.".format(
                    obj.magic, magic
                )
            )
        obj.magic = magic

        start_position = stream.tell()
        try:
            while True:
                level = JetpackLevel.unpack(stream)
                start_position = stream.tell()
                obj.levels.append(level)
        except EOFError:
            last_position = stream.tell()

        if start_position != last_position:
            warn(
                "Ignored {} bytes of trailing data at the end of the file.".format(
                    last_position - start_position
                )
            )

        return obj

    def pack(self) -> bytes:
        # TODO: I should implement some kind of "is_valid" check on all classes.
        # I should not prevent writing invalid levels, but I should be able to detect those cases.
        return b"".join(
            [
                struct.pack("2s", self.magic),
                *(level.pack() for level in self.levels),
            ]
        )

    @classmethod
    def load_from_filename(cls, filename: str | Path) -> Self:
        """Creates a new JetpackLevelPack instance, loading from a file.

        The game has a `JETLEV.DAT` file with the level pack.
        """
        with Path(filename).open('rb') as f:
            return cls.unpack(f)

    @classmethod
    def load_from_bytes(cls, data: Sequence[int]) -> Self:
        """Creates a new JetpackLevelPack instance, loading from a `bytes` object.

        ---

        TODO: Add tests loading a real-world file.
        """
        with BytesIO(data) as stream:
            return cls.unpack(stream)
