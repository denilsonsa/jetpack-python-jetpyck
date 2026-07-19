#pragma description Jetpack Level or LevelPack
#pragma author denilsonsa

// ImHex pattern for inspecting `JETLEV.DAT` level pack or `*.JET` custom
// levels from the MS-DOS game Jetpack.
//
// Custom levels `*.JET` have a fixed size, and all the elements are directly
// visible in predictable locations in the binary data.
//
// The built-in level pack is just a concatenation of multiple levels, prefixed
// by a mysterious two-byte magic number.
//
// See also:
// https://www.adeptsoftware.com/jetpack/
// https://github.com/WerWolv/ImHex
// https://github.com/WerWolv/ImHex-Patterns
// https://docs.werwolv.net/documentation

import std.io;
import std.mem;
import type.magic;

// Color palette based on the average color of each tile.
// This palette has been generated from this Python code:
//
// print("u32 tileset_palette[256] = {")
// for i in range(120):
//     (r, g, b, a) = tileset.get_tile(i).resize((1, 1), resample=Image.Resampling.BICUBIC).getpixel((0,0))
//     print("    0x{:02X}{:02X}{:02X}{:02X}, // {}".format(a, r, g, b, i))
// for i in range(120, 256):
//     print("    0x{:02X}{:02X}{:02X}{:02X}, // {}".format(0, 0, 0, 0, i))
// print("};")
//
// And then the trailing comma was manually removed from the last item.
u32 tileset_palette[256] = {
    0xFF282828, // 0
    0xFF686868, // 1
    0xFF828283, // 2
    0xFF828283, // 3
    0xFF374A37, // 4
    0xFF3B3B3B, // 5
    0xFF312F2A, // 6
    0xFF302830, // 7
    0xFF273027, // 8
    0xFF313142, // 9
    0xFF252539, // 10
    0xFF413030, // 11
    0xFF382424, // 12
    0xFF313E3B, // 13
    0xFF263430, // 14
    0xFF606060, // 15
    0xFF464646, // 16
    0xFF525252, // 17
    0xFF494949, // 18
    0xFF505050, // 19
    0xFF4D4B23, // 20
    0xFF383727, // 21
    0xFF4C4A27, // 22
    0xFF6A651B, // 23
    0xFF2A2A2A, // 24
    0xFF000000, // 25
    0xFF4E3A29, // 26
    0xFF868686, // 27
    0xFF68BB68, // 28
    0xFF0F5510, // 29
    0xFF4C5C09, // 30
    0xFF366809, // 31
    0xFF54A754, // 32
    0xFF272732, // 33
    0xFF312626, // 34
    0xFF272F2D, // 35
    0xFF4E4E4E, // 36
    0xFF5E5E5E, // 37
    0xFF4D4D4D, // 38
    0xFF565656, // 39
    0xFF6F0E0E, // 40
    0xFF6C0F0F, // 41
    0xFF6D0F0F, // 42
    0xFF6D0F0F, // 43
    0xFF6C0F0F, // 44
    0xFF681010, // 45
    0xFF6A1010, // 46
    0xFF6B1010, // 47
    0xFF691010, // 48
    0xFF641212, // 49
    0xFF50200D, // 50
    0xFF4D200F, // 51
    0xFF50200E, // 52
    0xFF4F200E, // 53
    0xFF4E200E, // 54
    0xFF4B2010, // 55
    0xFF4C200F, // 56
    0xFF4F210F, // 57
    0xFF4D200F, // 58
    0xFF4A2111, // 59
    0xFF7C7C7C, // 60
    0xFF787878, // 61
    0xFF767676, // 62
    0xFF797979, // 63
    0xFF797979, // 64
    0xFF757575, // 65
    0xFF727272, // 66
    0xFF747474, // 67
    0xFF767676, // 68
    0xFF6D6D6D, // 69
    0xFF755431, // 70
    0xFFA42295, // 71
    0xFF808F95, // 72
    0xFFC9940A, // 73
    0xFF000189, // 74
    0xFF000189, // 75
    0xFFA50000, // 76
    0xFFA50000, // 77
    0xFF03887B, // 78
    0xFF03887B, // 79
    0xFF752E2E, // 80
    0xFF732C2C, // 81
    0xFF701B1B, // 82
    0xFF731D1D, // 83
    0xFF752121, // 84
    0xFF701C1C, // 85
    0xFF732828, // 86
    0xFF762D2D, // 87
    0xFF762D2D, // 88
    0xFF702828, // 89
    0xFF733535, // 90
    0xFF763838, // 91
    0xFF773939, // 92
    0xFF763939, // 93
    0xFF7E3A51, // 94
    0xFF664650, // 95
    0xFF898AA1, // 96
    0xFF561D0B, // 97
    0xFF3B2B0B, // 98
    0xFF607260, // 99
    0xFF5B3B2E, // 100
    0xFF5B382B, // 101
    0xFF4F2A1C, // 102
    0xFF562D1D, // 103
    0xFF5C3020, // 104
    0xFF552B1C, // 105
    0xFF563628, // 106
    0xFF5F3A2C, // 107
    0xFF603A2C, // 108
    0xFF543528, // 109
    0xFF5B4035, // 110
    0xFF5F4337, // 111
    0xFF634438, // 112
    0xFF5F4439, // 113
    0xFF742020, // 114
    0xFF542F20, // 115
    0xFF808080, // 116
    0xFF742020, // 117
    0xFF542F20, // 118
    0xFF808080, // 119
    0x00000000, // 120
    0x00000000, // 121
    0x00000000, // 122
    0x00000000, // 123
    0x00000000, // 124
    0x00000000, // 125
    0x00000000, // 126
    0x00000000, // 127
    0x00000000, // 128
    0x00000000, // 129
    0x00000000, // 130
    0x00000000, // 131
    0x00000000, // 132
    0x00000000, // 133
    0x00000000, // 134
    0x00000000, // 135
    0x00000000, // 136
    0x00000000, // 137
    0x00000000, // 138
    0x00000000, // 139
    0x00000000, // 140
    0x00000000, // 141
    0x00000000, // 142
    0x00000000, // 143
    0x00000000, // 144
    0x00000000, // 145
    0x00000000, // 146
    0x00000000, // 147
    0x00000000, // 148
    0x00000000, // 149
    0x00000000, // 150
    0x00000000, // 151
    0x00000000, // 152
    0x00000000, // 153
    0x00000000, // 154
    0x00000000, // 155
    0x00000000, // 156
    0x00000000, // 157
    0x00000000, // 158
    0x00000000, // 159
    0x00000000, // 160
    0x00000000, // 161
    0x00000000, // 162
    0x00000000, // 163
    0x00000000, // 164
    0x00000000, // 165
    0x00000000, // 166
    0x00000000, // 167
    0x00000000, // 168
    0x00000000, // 169
    0x00000000, // 170
    0x00000000, // 171
    0x00000000, // 172
    0x00000000, // 173
    0x00000000, // 174
    0x00000000, // 175
    0x00000000, // 176
    0x00000000, // 177
    0x00000000, // 178
    0x00000000, // 179
    0x00000000, // 180
    0x00000000, // 181
    0x00000000, // 182
    0x00000000, // 183
    0x00000000, // 184
    0x00000000, // 185
    0x00000000, // 186
    0x00000000, // 187
    0x00000000, // 188
    0x00000000, // 189
    0x00000000, // 190
    0x00000000, // 191
    0x00000000, // 192
    0x00000000, // 193
    0x00000000, // 194
    0x00000000, // 195
    0x00000000, // 196
    0x00000000, // 197
    0x00000000, // 198
    0x00000000, // 199
    0x00000000, // 200
    0x00000000, // 201
    0x00000000, // 202
    0x00000000, // 203
    0x00000000, // 204
    0x00000000, // 205
    0x00000000, // 206
    0x00000000, // 207
    0x00000000, // 208
    0x00000000, // 209
    0x00000000, // 210
    0x00000000, // 211
    0x00000000, // 212
    0x00000000, // 213
    0x00000000, // 214
    0x00000000, // 215
    0x00000000, // 216
    0x00000000, // 217
    0x00000000, // 218
    0x00000000, // 219
    0x00000000, // 220
    0x00000000, // 221
    0x00000000, // 222
    0x00000000, // 223
    0x00000000, // 224
    0x00000000, // 225
    0x00000000, // 226
    0x00000000, // 227
    0x00000000, // 228
    0x00000000, // 229
    0x00000000, // 230
    0x00000000, // 231
    0x00000000, // 232
    0x00000000, // 233
    0x00000000, // 234
    0x00000000, // 235
    0x00000000, // 236
    0x00000000, // 237
    0x00000000, // 238
    0x00000000, // 239
    0x00000000, // 240
    0x00000000, // 241
    0x00000000, // 242
    0x00000000, // 243
    0x00000000, // 244
    0x00000000, // 245
    0x00000000, // 246
    0x00000000, // 247
    0x00000000, // 248
    0x00000000, // 249
    0x00000000, // 250
    0x00000000, // 251
    0x00000000, // 252
    0x00000000, // 253
    0x00000000, // 254
    0x00000000  // 255
};

using Tile = u8;

enum EnemyKind : u8 {
    Nothing = 0,
    Trackbot = 1,
    SteelBall = 2,
    Spring = 3,
    Missile = 4,
    Spikes = 5,
    Flitzer = 6,
    Homer = 7,
    Batbot = 8
};
struct Enemy {
    EnemyKind kind;
    u8 x, y;
} [[sealed, format("EnemyFormat"), color(EnemyColor(this))]];
fn EnemyFormat(Enemy e) {
    return std::format("{} @ {},{}", e.kind, e.x, e.y);
};
fn EnemyColor(Enemy e) {
    match(e.kind) {
        (EnemyKind::Nothing): return "000000";
        (EnemyKind::Trackbot): return "FF0000";
        (EnemyKind::SteelBall): return "55D3FB";
        (EnemyKind::Spring): return "8A8A8A";
        (EnemyKind::Missile): return "FF1C00";
        (EnemyKind::Spikes): return "AA00FF";
        (EnemyKind::Flitzer): return "0000AA";
        (EnemyKind::Homer): return "750000";
        (EnemyKind::Batbot): return "FF499A";
        (_): return "FF00FF";
    }
};

struct XY {
    u8 x, y;
} [[sealed, format("XYFormat")]];;
fn XYFormat(XY p) {
    return std::format("{},{}", p.x, p.y);
};

struct Level {
    Tile tilemap[16*26] [[hex::visualize("bitmap", this, 26, 16, tileset_palette)]];
    XY door [[color("533313")]];
    XY player [[color("C7BB00")]];
    Enemy enemies[20] [[format("EnemiesFormat")]];
    char desc1[13];
    char desc2[13];
} [[format("LevelFormat"), hex::visualize("bitmap", this.tilemap, 26, 16, tileset_palette)]];
fn EnemiesFormat(Enemy arr) {
    u8 active = 0;
    for (u8 i = 0, i < 20, i += 1) {
        if (arr[i].kind != EnemyKind::Nothing) {
            active += 1;
        }
    }
    if (active == 1) {
        return std::format("No enemies");
    } else if (active == 1) {
        return std::format("{} enemy", active);
    } else {
        return std::format("{} enemies", active);
    }
};
fn LevelFormat(Level lvl) {
    return lvl.desc1 + lvl.desc2;
};

struct LevelPack {
    be u16 magic;  // 0x86E6
    // type::Magic<"\x86\xE6"> magic;
    Level levels[while(!std::mem::eof())];
};

u16 magic = std::mem::read_unsigned(0x00, 2, std::mem::Endian::Big);

struct JETLEVorJET {
    if (magic == 0x86E6) {
        LevelPack pack @ 0x00;
        std::print("LevelPack detected");
    } else {
        Level level @ 0x00;
        std::print("Level detected");
    }
} [[inline]];

JETLEVorJET jetlev_or_jet @ 0x00;
