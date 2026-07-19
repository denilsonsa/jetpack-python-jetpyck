## TODO

* Idea for code organization:
    * `gfxdat.py` module should have a few classes. They can read/write `JETPACK?.DAT` gfx files, using `PIL.Image` while in-memory. The classes should also have an alternative constructor receiving a `PIL.Image` directly.
    * `render.py` module that should contain a few functions, but likely no classes. It would combine the gfxdat instance with the `JetpackLevel` instance to actually render a level preview.
    * The level preview has several options:
        * Render separate layers: background, sprites, foreground
        * Render scaled versions (x1, x2, x3, x4, …), for nice crisp rendering even on Discord
        * Save as animated GIF, or animated WebP, or perhaps APNG (which is likely obsolete)
    * The `render` module can have a function to generate 3 additional `Image` instances by rotating the colors in the palette.
    * Bonus features:
        * Export as ILBM PBM IFF file (for use in PyDPainter, Deluxe Paint, DPaint-js). I should check the PyDPainter license for [this code](https://github.com/mriale/PyDPainter/blob/master/libs/picio.py)
    * We could have an additional `shortcuts` module for common use-cases:
        * Convert a `.DAT` file to `.GIF`, or vice-versa
        * Render a level to an image, using a certain tileset.
        * This `shortcuts` module could become sub-commands on the command-line. (e.g. `python -m jetpyck gfxdat-to-webp _JET_A0.DAT foo.webp`)

* Move code out of the jupyter notebooks and into proper Python modules.
* Write code (or tool) to convert `.DAT` files to PNG files.
* Write code (or tool) to convert PNG files back to `.DAT` files. Be careful with the palette.
* Generate the level image from the actual game gfx, extracted using the tools above.
* Look at the other TODO items inside the other files.

## Jetpack level collection

Ideas for another repository:

* Use some template engine to generate HTML pages for each levelset. This will be awesome!
* Configure GitHub actions to render the static files and make them available online.

* Use <https://js-dos.com/dos-api.html> to add DOSBox to the webpage.
    * Use the API to inject the chosen level files into the DOSBox.
    * Potentially use the API to extract any newly created level from the DOSBox.
    * Figure out if we have any command-line argument to JETPACK to directly launch a level.
    * We can even try replacing the original `JETLEV.DAT` and `JETDEMO.DAT` and even the graphics.
