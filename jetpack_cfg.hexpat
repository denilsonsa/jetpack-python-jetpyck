#pragma description Jetpack configuration JETPACK.CFG
#pragma author denilsonsa

// ImHex pattern for inspecting `JETPACK.CFG` from the MS-DOS game Jetpack.
//
// This file is very simple, it only contains 5 bytes.
//
// See also:
// https://www.adeptsoftware.com/jetpack/
// https://github.com/WerWolv/ImHex
// https://github.com/WerWolv/ImHex-Patterns
// https://docs.werwolv.net/documentation

import std.io;

struct JetpackCFG {
    // 0 = Auto
    // 1 = Disabled
    // 2 = Force 1
    u8 joysticks [[format("JoysticksFormat")]];
    
    // 0 = single-player
    // 1 = two players
    // ...
    // 7 = 8 players
    u8 players [[format("PlayersFormat")]];
    
    // The starting level selected at the main menu.
    // Always a multiple of 10.
    u8 start_level [[format("StartFormat")]];

    // 0 = Standard
    // 1 = Custom (load custom level)
    // 2 = Savegame
    u8 game_type [[format("GameTypeFormat")]];
    
    // The in-game speed, selectable via plus/minus keys.
    // From 0 to 9.
    u8 speed [[format("SpeedFormat")]];
};

fn JoysticksFormat(u8 j) {
    match(j) {
        (0): return std::format("(F5) Auto (Joysticks)", j);
        (1): return std::format("(F5) Disabled (Joysticks)", j);
        (2): return std::format("(F5) Force 1 (Joysticks)", j);
        (_): return std::format("(F5) {} (Joysticks)", j);
    }
};
fn PlayersFormat(u8 p) {
    return std::format("(F2) {} player{}", p + 1, p > 0 ? "s" : "");
};
fn StartFormat(u8 lvl) {
    match(lvl) {
        // What happens if JETLEV.DAT has less than 100 levels?
        (100): return std::format("(F3) Random level", lvl);
        (_): return std::format("(F3) {}th level", lvl);
    }
};
fn GameTypeFormat(u8 gt) {
    match(gt) {
        (0): return std::format("(F4) Standard", gt);
        (1): return std::format("(F4) Custom", gt);
        (2): return std::format("(F4) Savegame", gt);
        (_): return std::format("(F4) {} (game type)", gt);
    }
};
fn SpeedFormat(u8 spd) {
    return std::format("(-+) {} speed", spd);
};

JetpackCFG config @ 0x00;
