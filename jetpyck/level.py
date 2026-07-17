'''jetpyck.level is a module for handling Jetpack levels.

## Serialization

Most classes have a pair of methods: `unpack` and `pack`.

For such classes, `unpack` is a classmethod that returns a new instance,
decoded from a byte stream. In other workds, `unpack` will create an object
instance from a serialized byte stream (e.g. from a file).

The opposite action is `pack`, which is an instance method to return an
encoded version as `bytes`. In other words, `pack` will serialize the object
into `bytes`, which can later be combined with other bytes and written to a
file.

## Naming is hard

Although the in-game help describes enemy "types", the word "type" has a very
specific meaning in programming languages. Thus, this module refers the enemy
"types" as "kinds". We have 8 enemy "kinds" in the game.
'''

__all__ = ['JetpackEnemyKind', 'JetpackEnemy', 'JetpackLevelTilemap', 'JetpackLevel']

import struct

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import BinaryIO

from PIL.ImagePalette import ImagePalette
from PIL import Image, ImageSequence

from .utils import unpack_stream

class JetpackEnemyKind(IntEnum):
    '''There are 8 enemies in Jetpack.
    Enemies are active sprites that move in the level.

    As per the buil-in help screens:
    > Eight different types of enemies
    > will try to put an end to your quest
    '''

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
    # Uses radar to hunt you down
    HOMER = 7
    # Travels through bricks straight toward you
    BATBOT = 8


@dataclass
class JetpackEnemy:
    r'''A single enemy instance in a level.

    Each enemy is encoded as 3 bytes:
    1. The enemy kind.
    2. The enemy X position.
    3. The enemy Y position.

    >>> e = JetpackEnemy(JetpackEnemyKind.FLITZER, 2, 3)
    >>> e.x, e.y
    (2, 3)
    >>> buf = e.pack()
    >>> buf
    b'\x06\x02\x03'
    >>> from io import BytesIO
    >>> with BytesIO(buf) as stream:
    ...     other = JetpackEnemy.unpack(stream)
    >>> e is other
    False
    >>> e == other
    True
    '''

    kind: JetpackEnemyKind = JetpackEnemyKind.NONE
    x: int = 0
    y: int = 0

    @classmethod
    def unpack(cls, stream: BinaryIO) -> JetpackEnemy:
        obj = cls()
        obj.kind = JetpackEnemyKind(*unpack_stream('B', stream))
        obj.x, obj.y = unpack_stream('BB', stream)
        return obj

    def pack(self) -> bytes:
        return struct.pack('BBB', self.kind, self.x, self.y)


@dataclass
class JetpackLevelTilemap:
    r'''The static portion of the level (background+foreground) is a tilemap.
    Each level is a grid of 26 x 16 tiles, and each tile is a single byte.

    There are 120 different kinds of tiles.
    Each tile is represented as a single byte from 0 until 119.
    The tile selection screen from the level editor has all 120 tiles in order,
    from 0 until 119.

    The tilemap of each level is stored sequentially, left-to-right,
    top-to-bottom. First with the top-most row of tiles, then the next one,
    until the entire grid is serialized.

    For simplicity and convenience, this JetpackLevelTilemap class also behaves
    as a sequence. There is no need to acces the internal `.data` structure.
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

    >>> from io import BytesIO
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
    '''

    # This internal data could have been implemented in several ways:
    # - bytes (immutable)
    # - bytearray (mutable array of bytes)
    # - array (mutable array of 8-bit integers or other word sizes)
    # I had to pick one, but any of these would have worked.
    data: bytearray = field(default_factory=lambda: bytearray(26 * 16))
    # The original Jetpack levels are hard-coded to 26x16 tiles.
    width: int = 26
    height: int = 16

    @classmethod
    def unpack(cls, stream: BinaryIO, *, width=None, height=None) -> JetpackTilemap:
        obj = cls()

        # Allow overriding the original hard-coded level dimensions
        if width is not None:
            obj.width = width
        if height is not None:
            obj.height = height

        (data,) = unpack_stream('{}s'.format(len(obj)), stream)
        obj.data = bytearray(data)
        return obj

    def pack(self) -> bytes:
        return bytes(self.data)

    def __len__(self) -> int:
        return self.width * self.height

    def _subscript_to_index(self, subscript: int|slice|tuple[int]) -> int|slice:
        '''Supports multiple syntaxes:
        tilemap[123]   -> int in range 0..len(tilemap)
        tilemap[4, 6]  -> separate coordinates for x and y
        tilemap[12:34] -> slice of two (or three) integers
        '''
        if isinstance(subscript, (int, slice)):
            # Single integer, or a slice.
            return subscript
        elif isinstance(subscript, tuple):
            x, y = subscript
            if not isinstance(x, int) or not isinstance(y, int):
                raise TypeError('Expected x,y coordinates as int, got {!r},{!r}'.format(x, y))
            elif 0 <= x < self.width and 0 <= y < self.height:
                # Single integer.
                return x + y * self.width
            else:
                raise IndexError('Out-of-bounds x or y coordinates: {}, {}'.format(x, y))
        else:
            raise TypeError('Expected int or tuple, got {!r}'.format(subscript))

    def __getitem__(self, subscript: int|slice|tuple[int]) -> int|bytearray:
        index_or_slice = self._subscript_to_index(subscript)
        return self.data[index_or_slice]

    def __setitem__(self, subscript: int|slice|tuple[int], value: int|bytes|bytearray):
        index_or_slice = self._subscript_to_index(subscript)
        self.data[index_or_slice] = value

    def items(self) -> Iterable[tuple[int]]:
        '''Generator of tuples (x, y, tile), for each of the tiles in this tilemap.
        '''
        for y in range(self.height):
            for x in range(self.width):
                yield (x, y, self[x, y])

    def rows(self) -> Iterable[bytes|bytearray]:
        '''Convenience function that returns (a copy of) each row separately.
        '''
        for y in range(self.height):
            yield self.data[y * self.width : (y+1) * self.width]


@dataclass
class JetpackLevel:
    r'''A Jetpack level is stored in a `.JET` file. The file structure is very
    straightforward.

    - 416 bytes for the 26x16
    - 2 bytes for the x,y position of the exit door (in range ??..??)
    - 2 bytes for the x,y the player start position (in range ??..??)
    - 60 bytes for the enemies (20 enemies in total)
    - 26 bytes for the the level name (AKA description)

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

    >>> buf = lvl.pack()
    >>> len(buf)
    506
    >>> from io import BytesIO
    >>> with BytesIO(buf) as stream:
    ...     # Simulating a file object opened from a real file.
    ...     stream.name = 'EXAMPLE.JET'
    ...     loadedlvl = JetpackLevel.unpack(stream)
    >>> lvl.filename = 'EXAMPLE.JET'
    >>> lvl == loadedlvl
    True
    '''

    tilemap: JetpackTilemap = field(default_factory=JetpackLevelTilemap)
    door_x: int = 0 
    door_y: int = 0
    player_x: int = 0
    player_y: int = 0
    enemies: list[JetpackEnemy] = field(default_factory=lambda: [JetpackEnemy() for _ in range(20)])
    # TODO: Maybe the description should be `str` instead of `bytes`.
    # TODO: Maybe we should have a desc getter/setter that would automatically convert/pad/trim the description string.
    description: bytes|bytearray = b' ' * 26

    # Filename is optional, and is added here just for convenience.
    # It's an easy way to identify a level among many others inside any data structure.
    # TODO: Should it also support a Path in addition to str?
    filename: str = ''

    def __str__(self) -> str:
        return '<JetpackLevel {}"{}">'.format(
            '{:>12} '.format(self.filename) if self.filename else '',
            self.description.decode('ascii')
        )

    @classmethod
    def unpack(cls, stream: BinaryIO, filename: str|Path = None) -> JetpackLevel:
        obj = cls()
        if filename is None:
            # Try getting the filename from the file-like object.
            name = getattr(stream, 'name', None)
            obj.filename = name or ''
        else:
            # Preference for the explicit filename.
            obj.filename = filename

        obj.tilemap = JetpackLevelTilemap.unpack(stream)
        obj.door_x, obj.door_y = unpack_stream('BB', stream)
        obj.player_x, obj.player_y = unpack_stream('BB', stream)
        obj.enemies = [JetpackEnemy.unpack(stream) for _ in range(20)]
        (obj.description,) = unpack_stream('26s', stream)
        return obj

    def pack(self) -> bytes:
        return b''.join([
            self.tilemap.pack(),
            struct.pack('BB', self.door_x, self.door_y),
            struct.pack('BB', self.player_x, self.player_y),
            *(e.pack() for e in self.enemies),
            struct.pack('26s', self.description)
        ])
