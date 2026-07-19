import struct
from typing import BinaryIO, TypeIs

__all__ = ["unpack_stream", "unpack_int", "unpack_ints", "unpack_bytes"]


# Why isn't this a built-in function already?
def unpack_stream(format: str, stream: BinaryIO) -> tuple[object, ...]:
    r"""Given a struct format string and a binary file-like stream,
    reads from that stream the exact amount of bytes required for that format
    and unpacks those bytes, returning a tuple.

    Raises an EOFError if not enough bytes could be read
    (i.e. trying to read from beyond the end-of-file).
    I'm reusing the built-in EOFError exception.
    Not the cleanest solution, but works well enough for this case.

    >>> from io import BytesIO

    Some examples of successes:

    >>> with BytesIO(b'\xde\xad\xbe\xef') as stream:
    ...     assert stream.tell() == 0
    ...     print(unpack_stream('>HH', stream))
    ...     assert stream.tell() == 4
    (57005, 48879)
    >>> with BytesIO(b'\xde\xad\xbe\xef') as stream:
    ...     print(unpack_stream('>H', stream))
    ...     print(unpack_stream('>H', stream))
    (57005,)
    (48879,)
    >>> with BytesIO(b'\x01\x02') as stream:
    ...     print(unpack_stream('B', stream))
    ...     print(stream.read(1))
    (1,)
    b'\x02'

    Some examples of failures:

    >>> with BytesIO(b'\x01\x00') as stream:
    ...     print(unpack_stream('L', stream))
    Traceback (most recent call last):
    ...
    EOFError: ...

    >>> stream = BytesIO(b'\x01\x00')
    >>> print(unpack_stream('>H', stream))
    (256,)
    >>> print(unpack_stream('B', stream))
    Traceback (most recent call last):
    ...
    EOFError: ...
    >>> stream.close()
    """

    size = struct.calcsize(format)
    buf = stream.read(size)
    if len(buf) != size:
        raise EOFError(
            "Wanted {} bytes, but only {} bytes were read".format(size, len(buf))
        )
    return struct.unpack(format, buf)


# More specific functions just to make the `mypy` type checker happy.
# https://github.com/python/mypy/issues/20869
# https://github.com/microsoft/pyright/issues/4727


def is_tuple_of_ints(val: tuple[object, ...]) -> TypeIs[tuple[int, ...]]:
    return all(isinstance(x, int) for x in val)


def unpack_int(format: str, stream: BinaryIO) -> int:
    (out,) = unpack_stream(format, stream)
    assert isinstance(out, int)
    return out


def unpack_ints(format: str, stream: BinaryIO) -> tuple[int, ...]:
    out = unpack_stream(format, stream)
    assert is_tuple_of_ints(out)
    return out


def unpack_bytes(format: str, stream: BinaryIO) -> bytes:
    (out,) = unpack_stream(format, stream)
    assert isinstance(out, bytes)
    return out
