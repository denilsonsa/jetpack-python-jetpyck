## TODO

* Move code out of the jupyter notebooks and into proper Python modules.
* Write code (or tool) to convert `.DAT` files to PNG files.
* Write code (or tool) to convert PNG files back to `.DAT` files. Be careful with the palette.
* Generate the level image from the actual game gfx, extracted using the tools above.
* Look at the other TODO items inside the Jupyter notebooks.

* Move the ImHex pattern code into a separate hexpat file.

* Use some template engine to generate HTML pages for each levelset. This will be awesome!
* Configure GitHub actions to render the static files and make them available online.

* Use <https://js-dos.com/dos-api.html> to add DOSBox to the webpage.
    * Use the API to inject the chosen level files into the DOSBox.
    * Potentially use the API to extract any newly created level from the DOSBox.
    * Figure out if we have any command-line argument to JETPACK to directly launch a level.
