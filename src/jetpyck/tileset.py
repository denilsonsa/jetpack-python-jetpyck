from PIL import Image
from PIL._typing import StrOrBytesPath

__all__ = []


def _calc_tile_box(
    id: int,
    *,
    left: int,
    top: int,
    width: int,
    height: int,
    delta_x: int,
    delta_y: int,
    tiles_per_row: int,
    total: int,
    min_id: int = 0,
) -> tuple[int, int, int, int]:
    if not min_id <= id < min_id + total:
        raise ValueError(
            "Invalid tile id {!r}, expected in range {}..{}".format(
                id, min_id, min_id + total
            )
        )

    x = (id - min_id) % tiles_per_row
    y = (id - min_id) // tiles_per_row

    px = left + x * delta_x
    py = top + y * delta_y
    return (px, py, px + width, py + height)


class JetpackTileset:
    # TODO! Incomplete and experimental code!

    def _get_tile_box(self, id: int) -> tuple[int, int, int, int]:
        return _calc_tile_box(
            id,
            left=1,
            top=8,
            width=12,
            height=12,
            delta_x=13,
            delta_y=13,
            tiles_per_row=20,
            total=120,
        )

    def _get_foreground_tile_box(self, id: int) -> tuple[int, int, int, int]:
        return _calc_tile_box(
            id,
            left=222,
            top=108,
            width=12,
            height=12,
            delta_x=13,
            delta_y=13,
            tiles_per_row=24,
            total=6,
            min_id=27,  # Perhaps start at 26 to include the black tile
        )

    def _get_char_box(self, id: int) -> tuple[int, int, int, int]:
        return _calc_tile_box(
            id,
            left=0,
            top=0,
            width=7,
            height=7,
            delta_x=7,
            delta_y=7,
            tiles_per_row=45,
            total=45,
        )

    def _get_door_box(self, id: int) -> tuple[int, int, int, int]:
        return _calc_tile_box(
            id,
            left=265,
            top=8,
            width=24,
            height=24,
            delta_x=25,
            delta_y=25,
            tiles_per_row=2,
            total=8,
        )

    def _get_sprite_box(self, id: int) -> tuple[int, int, int, int]:
        return _calc_tile_box(
            id,
            left=1,
            top=122,
            width=12,
            height=12,
            delta_x=13,
            delta_y=13,
            tiles_per_row=24,
            total=168,
        )
