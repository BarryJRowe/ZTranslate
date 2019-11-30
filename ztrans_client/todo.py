"""

!DONE!-make screenshot key asynchronous
!DONE!-speed up screenshoting
!(SERVER)!-have option to only create a new image if there's new ocr information in it.
!DONE!-back and forth image keys only seem to go through the file list as it was at startup??
!DONE!-get basic funcationality working on windows
!DONE!-get image flipping working
!DONE!-convert repo to a git repo and have it hosed somewhere.
!OK-ISH!-make write function more efficient.
	!DONE!-either bypass the write, or make it binary searching like.
!DONE!-upate the backend code to do a better job matching the text on the screen to existing saves.
	!DONE!-text matching has to be smarter than just hsv matching, since similar text can appear in many places
	 and can move around.
!DONE!-manage images and flip through them
    !DONE!-save org_images in a directory, and make them sequential in name (timestamp-based)
    !DONE!-have the buttons flip through them
        !DONE!-add in extra mocked screen grabs
        !DONE!-get prev and next working correctly
            !DONE!-the point of this currently is to just allow the person to flip
             through the images only
        !NAH!-add in the screenshot time taken (self.curr_image) somewhere in the
         image section
        !DONE!-add in ocr and translation results to the screenshots directory
         with the same base filename as the original screenshot.
        !DONE!-add in hoteys:
            !DONE!-have hotkey to take screenshot
            !DONE!-have hotkey to go forward in user screenshots
            !DONE!-have hotkey to go backwards through user screenshots
            !DONE!-have hotkey to toggle bettwen raw and translated images.
!DONE!-get font to work, regardless of box size
!DONE!-get api to start working and recording data
    !DONE!-get the server to run and call appropriately
    !DONE!-get the data to be saved to the database
    !DONE!-get the server to check the indexes and try to bypass the ocr/translate

!DONE!-get flipping images to work
	!DONE!-get base flipping images working in windows
!DONE!-get custom translations to start working.
!DONE!-make server code to display image, ocred text, ocred boxes, and translated text
	!DONE!-make it display the information
	!DONE!-make it update the information
	!DONE!-make it scroll through the images.

!DONE!-add support for packages
!DONE!-add support for fast mode
!DONE!-add support for normal mode (as is now)
!DONE!-for packages, make the screenshoting go really, really fast automatically.

-add special json to match:
	-on the first screen:
		-check variable name == "none", if so:
              -set variable name.
              -set a bunch of delay boxes.
           -leave regular ocr going.
              -

-fix crashing bug
	-move pumpmessages to subprocess, so it doesn't interfer with tkinter
-make it so screenshoting with packages does not capture the main window
-fix problems with "switch" moving text
-fix ocr bugs on the first two puzzles.


-check to see if you can make the api calls faster
-play through hohlenwelt saga and capture as much images as possible.
	-create someway of organizing the images into a package and translating it.


-get key input to flip images working for customizable keys
-add a window to show the package information for a loaded package



-translate first game.
"""
