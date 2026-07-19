#pragma description Jetpack demo JETDEMO.DAT
#pragma author denilsonsa

// ImHex pattern for inspecting `JETDEMO.DAT` from the MS-DOS game Jetpack.
//
// When the game is left on the main menu for long enough, it will play a
// pre-recorded demo of gameplay. This is also known as "attract mode", a term
// coming from arcade games.
//
// The format for this demo file is extremely simple. One byte for the level
// number, followed by one byte for each frame of input.
//
// Unfortunately, I'm not aware of any tool for recording demos.

import std.io;
import std.mem;

bitfield Input {
    right : 1;  // bit 0, 0x01, LSB
    left  : 1;  // bit 1, 0x02
    down  : 1;  // bit 2, 0x04
    up    : 1;  // bit 3, 0x08
    jump  : 1;  // bit 4, 0x10
    phaser: 1;  // bit 5, 0x20, MSB
    zeroes: 2;  // padding
}[[sealed, format("InputFormat"), color(InputColor(this))]];
fn InputColor(Input x) {
	// I'm not happy with these colors.
	// If you have a better color scheme, please contribute!
    return (
        0
        // RED
        | (x.left   ? 0x7F0000 : 0)
        | (x.right  ? 0xFF0000 : 0)
        // GREEN
        | (x.down   ? 0x007F00 : 0)
        | (x.up     ? 0x00FF00 : 0)
        // BLUE
        | (x.jump   ? 0x00007F : 0)
        | (x.phaser ? 0x0000FF : 0)
    );
};
fn InputFormat(Input x) {
    return std::format(
        "{}{}{}{}{}{}{}",
        (x.zeroes ? std::format("!{}! ", x.zeroes) : ""),
        (x.phaser ? "P" : " "),
        (x.jump   ? "J" : " "),
        (x.up     ? "^" : " "),
        (x.down   ? "v" : " "),
        (x.left   ? "<" : " "),
        (x.right  ? ">" : " ")
    );
};

struct JetpackDemo {
    u8 level [[format("LevelFormat")]];
    Input recording[while(!std::mem::eof())];
};
fn LevelFormat(u8 level) {
    return std::format("Level {}", level + 1);
};

JetpackDemo demo @ 0x00;
