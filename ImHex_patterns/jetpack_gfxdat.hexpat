#pragma description Jetpack graphics .DAT files
#pragma author denilsonsa
#pragma endian big

// ImHex pattern for inspecting JETPACK?.DAT files from the MS-DOS game Jetpack.
//
// These files have a simple VGA-style palette at the top followed by a bit
// stream of compressed pixels.
//
// The palette is properly highlighted and shows the correct colors.
//
// The compression is relatively simple, but it works with bits directly
// instead of bytes. I was unable to properly describe this compression in this
// hexpat file (either because I don't know the Pattern language well enough,
// or because it is currently impossible). Thus, the highlighting of the pixel
// bit stream is incorrect.

import std.io;
import std.mem;

// 6-bit RGB
struct RGB {
    u8 r, g, b;
} [[sealed, format("RGBHex"), color(RGBHex(this))]];
fn RGBHex(RGB color) {
    // Converting 6-bit to 8-bit.
    return std::format(
        "{:02X}{:02X}{:02X}",
        color.r * 255 / 63,
        color.g * 255 / 63,
        color.b * 255 / 63);
};

struct Palette {
    RGB palette[256];
};

bitfield Bit {
    bit: 1;
};
bitfield Byte {
    byte: 8;
};
bitfield Count {
    count: 5;
};

// !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
// !! WARNING! THIS IS INCORRECT!                                !!
// !! ImHex "bitfield" type always goes from the LSB to the MSB. !!
// !! However, the bit order in this file is the opposite.       !!
// !! Thus, this Pixel pattern here is WRONG.                    !!
// !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
struct Pixel {
    Bit is_repeating;
    if (is_repeating.bit == 1) {
        Count n;
    }
    Byte color;  // Palette index
} [[
    sealed,
    format("PixelFormat"),
    // Choose one:
    // - PixelFakeColor is faster, but uglier
    // - PixelColorFromDefaultPalette is slower
    color(PixelFakeColor(this))
    //color(PixelColorFromDefaultPalette(this))
]];
fn PixelFormat(Pixel p) {
    if (p.is_repeating.bit == 1) {
        return std::format("{:02X} x {:d}", p.color.byte, p.n.count + 2);
    } else {
        return std::format("{:02X}", p.color.byte);
    }
};
fn PixelFakeColor(Pixel p) {
    // Red channel: how many times it is repeated
    // Green channel: unused
    // Blue channel: the index in the palette
    return std::format(
        "{:02X}{:02X}{:02X}",
        (p.is_repeating.bit ? (p.n.count + 2) * 255 / 33 : 0),
        0,
        p.color.byte);
};
fn PixelColorFromDefaultPalette(Pixel p) {
	// This section was generated from this Python code:
	//
    // from itertools import batched
	// def hexpat_color_from_palette(palette):
    //     return '\n'.join([
    //         '    match(p.color.byte) {',
    //         *(
    //             '        ({:>3}): return "{:02X}{:02X}{:02X}";'.format(i, r, g, b)
    //             for i, (r, g, b) in enumerate(batched(palette, 3))
    //         ),
    //         '    }',
    //     ])
	//
	// However, this very long match() statement is very slow.
    match(p.color.byte) {
        (  0): return "000000";
        (  1): return "080808";
        (  2): return "101010";
        (  3): return "181818";
        (  4): return "202020";
        (  5): return "282828";
        (  6): return "303030";
        (  7): return "383838";
        (  8): return "404040";
        (  9): return "484848";
        ( 10): return "505050";
        ( 11): return "585858";
        ( 12): return "606060";
        ( 13): return "686868";
        ( 14): return "707070";
        ( 15): return "787878";
        ( 16): return "808080";
        ( 17): return "888888";
        ( 18): return "909090";
        ( 19): return "989898";
        ( 20): return "A4A4A4";
        ( 21): return "ACACAC";
        ( 22): return "B4B4B4";
        ( 23): return "BCBCBC";
        ( 24): return "C0C0C0";
        ( 25): return "CCCCCC";
        ( 26): return "D4D4D4";
        ( 27): return "DCDCDC";
        ( 28): return "E4E4E4";
        ( 29): return "ECECEC";
        ( 30): return "F4F4F4";
        ( 31): return "FCFCFC";
        ( 32): return "200000";
        ( 33): return "3C0000";
        ( 34): return "580000";
        ( 35): return "740000";
        ( 36): return "8C0000";
        ( 37): return "A80000";
        ( 38): return "C40000";
        ( 39): return "E00000";
        ( 40): return "FC0000";
        ( 41): return "FC2020";
        ( 42): return "FC4040";
        ( 43): return "FC5C5C";
        ( 44): return "FC7C7C";
        ( 45): return "FC9C9C";
        ( 46): return "FCB8B8";
        ( 47): return "FCD8D8";
        ( 48): return "201000";
        ( 49): return "381C00";
        ( 50): return "542400";
        ( 51): return "702800";
        ( 52): return "8C2C00";
        ( 53): return "A82C00";
        ( 54): return "C42800";
        ( 55): return "E02400";
        ( 56): return "FC1C00";
        ( 57): return "FC4018";
        ( 58): return "FC6438";
        ( 59): return "FC8458";
        ( 60): return "FCA078";
        ( 61): return "FCBC98";
        ( 62): return "FCD4B8";
        ( 63): return "FCE8D8";
        ( 64): return "201800";
        ( 65): return "3C2C00";
        ( 66): return "584000";
        ( 67): return "745400";
        ( 68): return "8C6800";
        ( 69): return "A87C00";
        ( 70): return "C48C00";
        ( 71): return "E0A000";
        ( 72): return "FCB800";
        ( 73): return "FCC020";
        ( 74): return "FCC840";
        ( 75): return "FCD05C";
        ( 76): return "FCDC7C";
        ( 77): return "FCE49C";
        ( 78): return "FCECB8";
        ( 79): return "FCF4D8";
        ( 80): return "201C00";
        ( 81): return "3C3400";
        ( 82): return "584C00";
        ( 83): return "746800";
        ( 84): return "8C8000";
        ( 85): return "A89C00";
        ( 86): return "C4B800";
        ( 87): return "E0D800";
        ( 88): return "FCF400";
        ( 89): return "FCF420";
        ( 90): return "FCF440";
        ( 91): return "FCF85C";
        ( 92): return "FCFC7C";
        ( 93): return "FCFC9C";
        ( 94): return "FCFCB8";
        ( 95): return "FCFCD8";
        ( 96): return "002000";
        ( 97): return "003C00";
        ( 98): return "005800";
        ( 99): return "007400";
        (100): return "008C00";
        (101): return "00A800";
        (102): return "00C400";
        (103): return "00E000";
        (104): return "00FC00";
        (105): return "20FC20";
        (106): return "40FC40";
        (107): return "60FC5C";
        (108): return "80FC7C";
        (109): return "9CFC9C";
        (110): return "BCFCB8";
        (111): return "D8FCD8";
        (112): return "042018";
        (113): return "083C2C";
        (114): return "0C5440";
        (115): return "107054";
        (116): return "148C68";
        (117): return "1CA480";
        (118): return "20C098";
        (119): return "28DCAC";
        (120): return "30F8C4";
        (121): return "48F8C8";
        (122): return "60F8D0";
        (123): return "78F8D8";
        (124): return "90F8DC";
        (125): return "A8FCE4";
        (126): return "C0FCEC";
        (127): return "DCFCF4";
        (128): return "041820";
        (129): return "082C3C";
        (130): return "0C4054";
        (131): return "0C5870";
        (132): return "106C8C";
        (133): return "1480A4";
        (134): return "1898C0";
        (135): return "1CB0DC";
        (136): return "20C4F8";
        (137): return "3CCCF8";
        (138): return "54D0F8";
        (139): return "70D8F8";
        (140): return "88DCF8";
        (141): return "A4E4FC";
        (142): return "C0ECFC";
        (143): return "DCF4FC";
        (144): return "000020";
        (145): return "00003C";
        (146): return "000058";
        (147): return "000074";
        (148): return "00008C";
        (149): return "0000A8";
        (150): return "0004C4";
        (151): return "0004E0";
        (152): return "0000FC";
        (153): return "2024FC";
        (154): return "4040FC";
        (155): return "5C60FC";
        (156): return "7C80FC";
        (157): return "9C9CFC";
        (158): return "B8BCFC";
        (159): return "D8D8FC";
        (160): return "140020";
        (161): return "24003C";
        (162): return "380058";
        (163): return "480074";
        (164): return "5C008C";
        (165): return "6C00A8";
        (166): return "8000C4";
        (167): return "9400E0";
        (168): return "A800FC";
        (169): return "B420FC";
        (170): return "BC40FC";
        (171): return "C85CFC";
        (172): return "D07CFC";
        (173): return "D89CFC";
        (174): return "E4B8FC";
        (175): return "F0D8FC";
        (176): return "20001C";
        (177): return "3C0034";
        (178): return "58004C";
        (179): return "740064";
        (180): return "8C007C";
        (181): return "A80094";
        (182): return "C400B0";
        (183): return "E000C8";
        (184): return "FC00E0";
        (185): return "FC20E4";
        (186): return "FC40E8";
        (187): return "FC5CEC";
        (188): return "FC7CEC";
        (189): return "FC9CF0";
        (190): return "FCB8F4";
        (191): return "FCD8F8";
        (192): return "000000";
        (193): return "20000C";
        (194): return "40001C";
        (195): return "600028";
        (196): return "7C0038";
        (197): return "9C0044";
        (198): return "BC0054";
        (199): return "DC0060";
        (200): return "FC0070";
        (201): return "FC2484";
        (202): return "FC4898";
        (203): return "FC6CAC";
        (204): return "FC90C0";
        (205): return "FCB4D4";
        (206): return "FCD8E8";
        (207): return "FCFCFC";
        (208): return "281400";
        (209): return "341C04";
        (210): return "402408";
        (211): return "503010";
        (212): return "5C3C18";
        (213): return "6C4820";
        (214): return "78542C";
        (215): return "846438";
        (216): return "947048";
        (217): return "A08058";
        (218): return "B0906C";
        (219): return "BCA080";
        (220): return "C8B494";
        (221): return "D8C4AC";
        (222): return "E4D8C4";
        (223): return "F4ECE0";
        (224): return "603428";
        (225): return "703C30";
        (226): return "844434";
        (227): return "94503C";
        (228): return "A85C40";
        (229): return "BC6448";
        (230): return "C06C54";
        (231): return "C87860";
        (232): return "CC846C";
        (233): return "D49078";
        (234): return "DC9C88";
        (235): return "E0A894";
        (236): return "E8B4A4";
        (237): return "F0C4B4";
        (238): return "F4D0C0";
        (239): return "FCE0D4";
        (240): return "505C98";
        (241): return "606C98";
        (242): return "707C9C";
        (243): return "007068";
        (244): return "008C84";
        (245): return "00A898";
        (246): return "00C8BC";
        (247): return "E4E4E8";
        (248): return "686868";
        (249): return "282828";
        (250): return "686868";
        (251): return "686868";
        (252): return "808080";
        (253): return "A4A4A4";
        (254): return "C0C0C0";
        (255): return "FCFCFC";
    }
};

struct JetpackGFX {
    Palette palette;
    Pixel pixels[while(!std::mem::eof())];
};

JetpackGFX gfx @ 0x0;
