"""jetpyck.rle is a module for implementing Jetpack's RLE algorithm.

RLE (Run-Length Encoding) is a simple idea. Count duplicate pieces of data.
Instead of storing repeated copies of the same data, store instead a single
copy and a count.

For Jetpack's own implementation, each individual piece of raw data is a byte
(i.e. 8 bits), and the encoded data works bit-by-bit. Here's the algorithm for
decoding the data:

* Consider the sequence of bytes as a stream of bits to be consumed.
* For each byte of encoded data, consume the 8 bits from the MSB (most
  significant bit) first. Look at some examples:
    * `0xF0` = `0b11110000` → (first bit) 1 1 1 1 0 0 0 0 (last bit)
    * `0xB2` = `0b10110010` → (first bit) 1 0 1 1 0 0 1 0 (last bit)
* Algorithm starts, receiving a byte stream (or a file) as input
* Keep reading bits from the input until decided to stop.
    * Read one bit, let's call it `mode`.
    * If this `mode` bit is 0, then consider the `byte_count` as 1.
    * If this `mode` bit is 1, then consume 5 more bits.
    * Make an integer out of these 5 bits, then add 2. The first bit is the
      MSB. Save this integer as `byte_count`. Examples:
        * 0 0 0 0 0 → 0  + 2 → 2
        * 0 0 0 0 1 → 1  + 2 → 3
        * 0 1 0 0 0 → 8  + 2 → 10
        * 1 0 0 0 0 → 16 + 2 → 18
        * 1 1 1 1 1 → 31 + 2 → 33
    * Consume 8 bits to form a `data_byte`. The first bit is the MSB. (Note that
      these 8 bits may be spread over two bytes in encoded data.)
    * Produce the `data_byte` repeated `byte_count` times.
* Any leftover bits are left unused (and zero).

This RLE algorithm is used for the graphics of these games:

* OLD_JET (early Jetpack version, before Wayne Timmerman)
* Shareware Jetpack
* Freeware Jetpack (full version)

The following games use a different encoding, not supported by this module:

* xjetpack (Christmas Special!)
* Squarez
* OLD_SQZ (early Squarez version)

"""

import warnings
from collections import deque
from collections.abc import Sequence
from contextlib import contextmanager
from types import TracebackType
from typing import Iterator, Literal, Self, overload
from warnings import warn

__all__ = ["JetpackRLEDecoder", "JetpackRLEEncoder"]


def bits_from_value(qty: int, value: int) -> Sequence[int]:
    """Returns the lower `qty` bits from `value`, in order from MSB to LSB.

    ---

    >>> list(bits_from_value(0, 0b0))
    []
    >>> list(bits_from_value(1, 0b0))
    [0]
    >>> list(bits_from_value(1, 0b1))
    [1]
    >>> list(bits_from_value(4, 0b0010))
    [0, 0, 1, 0]
    >>> list(bits_from_value(4, 0b1000))
    [1, 0, 0, 0]
    >>> list(bits_from_value(4, 0b1011))
    [1, 0, 1, 1]
    >>> list(bits_from_value(4, 0b1111))
    [1, 1, 1, 1]
    >>> list(bits_from_value(8, 0b10011100))
    [1, 0, 0, 1, 1, 1, 0, 0]

    If value is larger than the amount of bits requested, the higher bits are
    discarded. This usage is discouraged, though.

    >>> list(bits_from_value(1, 0b10))
    [0]
    >>> list(bits_from_value(2, 0b1100))
    [0, 0]
    >>> list(bits_from_value(3, 0b101010))
    [0, 1, 0]

    """
    if qty < 0:
        raise ValueError(f"Negative values are not allowed")
    if value < 0:
        raise ValueError(f"Negative values are not allowed")
    bits = bytearray(qty)
    for i in range(qty):
        bits[i] = (value >> (qty - i - 1)) & 1
    return bits


class BitStream:
    r"""Given a `bytes` object (or any sequence of bytes), this BitStream object
    will return bits from it. As a comparison, if a file-like object reads
    bytes sequentially, this BitStream object reads bits sequentially.

    ---

    >>> bs = BitStream(b'\x32\x55\xF0')
    >>> bs.remaining_bits()
    24
    >>> bs.is_empty()
    False
    >>> bs.get_bit(), bs.remaining_bits()
    (0, 23)
    >>> bs.get_bit(), bs.remaining_bits()
    (0, 22)
    >>> bs.get_bit(), bs.remaining_bits()
    (1, 21)
    >>> bs.get_bit(), bs.remaining_bits()
    (1, 20)
    >>> bs.get_bits(3), bs.remaining_bits()
    (1, 17)
    >>> bs.get_bits(1), bs.remaining_bits()
    (0, 16)
    >>> bs.get_bits(4), bs.remaining_bits()
    (5, 12)
    >>> hex(bs.get_byte()), bs.remaining_bits()
    ('0x5f', 4)
    >>> bs.is_empty()
    False
    >>> bs.get_bits(4), bs.remaining_bits()
    (0, 0)
    >>> bs.is_empty()
    True

    Cannot read past the end of the data stream.

    >>> bs.get_bit()
    Traceback (most recent call last):
    ...
    IndexError: ...

    For `bytes` and `bytearray` objects, all elements are unsigned bytes. But
    that may not be the case for other sequences.

    >>> bad = BitStream([-1])
    >>> bad.get_bit()
    Traceback (most recent call last):
    ...
    ValueError: ...

    >>> bad = BitStream([256])
    >>> bad.get_bit()
    Traceback (most recent call last):
    ...
    ValueError: ...

    """

    def __init__(self, data: Sequence[int]):
        # Read bits from this array of bytes:
        self.data = data
        # Points to the next byte to be consumed inside self.data:
        self.pointer = 0
        # Stream of bits from the byte(s) being consumed but not yet returned:
        self.bitbuffer: deque[int] = deque()

    def remaining_bits(self) -> int:
        """Returns the amount of bits remaining to be consumed."""
        return len(self.bitbuffer) + 8 * (len(self.data) - self.pointer)

    def is_empty(self) -> bool:
        """Are there any remaining bits to be consumed?"""
        return self.pointer >= len(self.data) and len(self.bitbuffer) == 0

    def _consume_byte(self) -> None:
        """Consumes one byte from the input data and put its bits onto
        the internal bitbuffer.
        """
        byte = self.data[self.pointer]
        if not 0 <= byte < 256:
            raise ValueError(
                f"Integer at position {self.pointer} is not an unsigned byte: {byte}"
            )
        self.pointer += 1
        self.bitbuffer.extend(bits_from_value(8, byte))

    def get_bit(self) -> int:
        """Returns one bit from the bit stream."""
        if len(self.bitbuffer) == 0:
            self._consume_byte()
        return self.bitbuffer.popleft()

    def get_bits(self, how_many: int) -> int:
        """Returns an integer made of a sequence consumed bits.

        Most often, we only need up to 8 bits, thus the return value is less
        than 256 in such cases.
        """
        out = 0
        for i in range(how_many):
            out <<= 1
            out |= self.get_bit()
        return out

    def get_byte(self) -> int:
        """Returns one byte (i.e. 8 bits)."""
        return self.get_bits(8)


@contextmanager
def warnings_to_stdout() -> Iterator[None]:
    """Context manager that temporarily print warnings to stdout.

    Useful in doctests.
    See: https://stackoverflow.com/questions/2418570/testing-warnings-with-doctest
    """
    with warnings.catch_warnings():
        warnings.showwarning = lambda message, *args: print(message)
        yield


class JetpackRLEDecoder:
    r"""Given a `bytes` object (or any sequence of bytes), decodes is using
    Jetpack's RLE algorithm.

    ---

    This class includes a few sanity checks that trigger warnings, but not
    errors. Inside doctests, we have to re-route warnings to stdout to make
    them testable.

    >>> with warnings_to_stdout():
    ...     with JetpackRLEDecoder([0b01000111, 0b11000000]) as dec:
    ...         print(dec.read(1).hex())
    8f
    Warning: Expected trailing padding bits to be zero, but got 1000000
    >>> with warnings_to_stdout():
    ...     with JetpackRLEDecoder([0b01000111, 0b10000000, 0]) as dec:
    ...         print(dec.read(1).hex())
    8f
    Warning: 1 trailing bytes (15 bits) are being ignored.

    Real-world use-cases don't need the `warnings_to_stdout()`.

    Simple cases with non-repeating data:

    >>> with warnings_to_stdout():
    ...     with JetpackRLEDecoder([0b01000111, 0b10000000]) as dec:
    ...         print(dec.read(1).hex())
    8f
    >>> with warnings_to_stdout():
    ...     with JetpackRLEDecoder([0b01000111, 0b10111100, 0b11000000]) as dec:
    ...         print(dec.read(2).hex())
    8ff3
    >>> with warnings_to_stdout():
    ...     with JetpackRLEDecoder([0b01000111, 0b10111100, 0b11000000]) as dec:
    ...         print(dec.read(1).hex())
    ...         print(dec.read(1).hex())
    8f
    f3

    Simple cases of repeated data:

    >>> with warnings_to_stdout():
    ...     with JetpackRLEDecoder([0b10000010, 0b00111100]) as dec:
    ...         print(dec.read(1).hex())
    8f8f
    >>> with warnings_to_stdout():
    ...     with JetpackRLEDecoder([0b10000110, 0b00111100]) as dec:
    ...         print(dec.read(1).hex())
    8f8f8f
    >>> with warnings_to_stdout():
    ...     with JetpackRLEDecoder([0b10001110, 0b00111100]) as dec:
    ...         print(dec.read(1).hex())
    8f8f8f8f8f
    >>> with warnings_to_stdout():
    ...     with JetpackRLEDecoder([0b11111110, 0b00111100]) as dec:
    ...         print(dec.read(1).hex() == '8f' * 33)
    True
    >>> with warnings_to_stdout():
    ...     with JetpackRLEDecoder([0b10000110, 0b00111110, 0b00101100, 0b10100000]) as dec:
    ...         print(dec.read(4).hex())
    8f8f8fcacacaca
    >>> with warnings_to_stdout():
    ...     with JetpackRLEDecoder([0b10000110, 0b00111110, 0b00101100, 0b10100000]) as dec:
    ...         print(dec.read(7).hex())
    8f8f8fcacacaca

    And mixing non-repeating with repeating data:

    >>> with warnings_to_stdout():
    ...     with JetpackRLEDecoder([0b10000110, 0b00111101, 0b10010100]) as dec:
    ...         print(dec.read(4).hex())
    8f8f8fca

    Passing zero will read until EOF:

    >>> with warnings_to_stdout():
    ...     with JetpackRLEDecoder([0b10000110, 0b00111110, 0b00101100, 0b10100111, 0b00111000]) as dec:
    ...         print(dec.read(1).hex())
    ...         print(dec.read(1).hex())
    ...         print(dec.read(1).hex())
    8f8f8f
    cacacaca
    e7
    >>> with warnings_to_stdout():
    ...     with JetpackRLEDecoder([0b10000110, 0b00111110, 0b00101100, 0b10100111, 0b00111000]) as dec:
    ...         print(repr(dec.read(0).hex()))
    ...         print(repr(dec.read(0).hex()))  # Already EOF, returns empty.
    '8f8f8fcacacacae7'
    ''
    """

    def __init__(self, data: Sequence[int]):
        self.bitstream = BitStream(data)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        remaining_bits = self.bitstream.remaining_bits()
        if not self.is_eof():
            warn(
                f"Warning: {remaining_bits // 8} trailing bytes ({remaining_bits} bits) are being ignored."
            )
        else:
            # EOF, we cannot decode anything extra from the bit stream.
            # But what's the state of the trailing padding bits?
            trailing_bits = self.bitstream.get_bits(remaining_bits)
            if trailing_bits != 0:
                trailing_bitstring = "{:0{}b}".format(trailing_bits, remaining_bits)
                warn(
                    f"Warning: Expected trailing padding bits to be zero, but got {trailing_bitstring}"
                )
        return False

    def is_eof(self) -> bool:
        """Are we at the end-of-file?

        In other words, do we have enough bits to be able to fully decode at
        least one more byte? The minimum we need is 9 bits: 1 bit zero followed
        by the 8 data bits.
        """
        return self.bitstream.remaining_bits() < (1 + 8)

    def items(self) -> Iterator[tuple[int, int]]:
        while not self.is_eof():
            is_repeating = self.bitstream.get_bit()
            if is_repeating:
                qty = 2 + self.bitstream.get_bits(5)
            else:
                qty = 1
            databyte = self.bitstream.get_byte()
            yield qty, databyte

    def read(self, how_many_bytes: int) -> bytearray:
        """Reads (at least) the specified amount of bytes.

        If zero bytes are asked, read until EOF.
        """
        if how_many_bytes == 0:
            buffer = bytearray()
            if self.is_eof():
                return buffer
            for qty, value in self.items():
                buffer.extend([value] * qty)
                if self.is_eof():
                    break
            return buffer
        else:
            buffer = bytearray(how_many_bytes)
            pointer = 0
            for qty, value in self.items():
                buffer[pointer : pointer + qty] = [value] * qty
                pointer += qty
                if pointer >= how_many_bytes:
                    break
            return buffer


class BitWriter:
    r"""Receives bits over time, and then groups them into bytes. As a
    comparison, if an io.BinaryIO object receives bytes sequentially and
    accumulates them in a buffer, this BitWriter object receives bits
    sequentially and accumulates them into bytes.

    ---

    It is necessary to add padding bits at the end. This can be done manually
    or using a context manager.

    >>> bw = BitWriter()
    >>> bw.put_bits(2, 0b11)
    >>> bw.put_bits(2, 0b00)
    >>> bw.put_bits(4, 0b1001)
    >>> len(bw)
    1
    >>> bytes(bw)
    b'\xc9'

    >>> bw = BitWriter()
    >>> bw.put_bits(2, 0b11)
    >>> bw.add_padding_bits()
    >>> bytes(bw)
    b'\xc0'

    >>> with BitWriter() as bw:
    ...     bw.put_bits(3, 0b101)
    >>> bytes(bw)
    b'\xa0'

    >>> with BitWriter() as bw:
    ...     bw.put_bits(1, 0b1)
    ...     bw.put_bits(5, 0b11011)
    ...     bw.put_bits(8, 0b01010101)
    >>> bytes(bw).hex()
    'ed54'
    >>> len(bw)
    2
    >>> hex(bw[0])
    '0xed'
    """

    def __init__(self) -> None:
        self.data = bytearray()
        # Stream of bits waiting to be grouped into a byte.
        self.bitbuffer: deque[int] = deque()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        self.add_padding_bits()
        return False

    def __bytes__(self) -> bytes:
        return bytes(self.data)

    def __len__(self) -> int:
        return len(self.data)

    @overload
    def __getitem__(self, index_or_slice: int) -> int: ...

    @overload
    def __getitem__(self, index_or_slice: slice) -> Sequence[int]: ...

    def __getitem__(self, index_or_slice: int | slice) -> int | Sequence[int]:
        return self.data[index_or_slice]

    def add_padding_bits(self) -> None:
        if len(self.bitbuffer) == 0:
            return
        self.put_bits(8 - len(self.bitbuffer), 0)
        assert len(self.bitbuffer) == 0

    def put_bits(self, qty: int, value: int) -> None:
        """Appends `qty` bits to the data, represented by `value`."""
        if qty <= 0:
            raise ValueError(
                f"The amount of bits must be positive and greater than zero"
            )
        if value < 0:
            raise ValueError(f"Negative values are not allowed")
        if not 0 <= value < (1 << qty):
            raise ValueError(
                f"Out-of-range value, {value} cannot be represented in {qty} bits"
            )

        self.bitbuffer.extend(bits_from_value(qty, value))
        while len(self.bitbuffer) >= 8:
            byte = 0
            for i in range(8):
                bit = self.bitbuffer.popleft()
                assert bit in {0, 1}
                byte = (byte << 1) | bit
            self.data.append(byte)


class JetpackRLEEncoder: ...
