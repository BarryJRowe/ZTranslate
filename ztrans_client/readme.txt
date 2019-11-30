/*************************\
*     ZTranslate v1.01    *
*                         *
*      By: Barry Rowe     *
*                         *
\*************************/


-------------------
How to Run Packages
-------------------

Run ztranslate.exe, then select File->Load Package-> and then select 
your package file.

At this point ztranslate will be grabing images from the window in 
focus.  Depending on the game, different rendering options might have
to be used to ensure that it can grab the image, or grab the image
faster.  For example, in the PPSSPP emulator, Direct 3D 9/11 will
work, but Open GL/Vulkan will not (they give a black screen).  If
your game doesn't work, there may be other work arounds until 
ZTranslate can be updated.

-------------------------
How to Run Automatic Mode
-------------------------

In order to run in automatic translation mode, you'll need tp modify the
config.json file and include an API key in the "user_api_key" field.
You can get one by signing up to ztranslate.net, going to settings, and
copying the api key in the "Quota" section.  After this, start 
ztranslate.exe, and when you press "~", it will grab a screenshot of the
 in-focus window, send it to the ztranslate.net server, and update the 
ztranslate client's window with the translated screenshot.  Depending
on your internet speed and the size of the game window, this may take
3-4 seconds or 10 seconds.

Similiarily to package mode, if the client can't grab the game screen,
then it won't be able to translate the window.  Modifing the video options
may make it work.


-------------
Linux Support
-------------

The linux version requires a few additional steps to work correctly.
First, you need to install imagemagick, which has the "import" command
that will grab the screen, and xdotool, which allows the client to select
the window in focus.  You'll aldo need xbindkeys installed to capture
key input while in automatic mode.

For xbindkeys to work, you need to set it up to write to particular files
when you press your desired keys.  An example is located in the xbindkeysrc
file.  In some cases, you'll have to modify game behavior to get things
to work.  For example, in dosbox, if autolock=true, then xbindkeys won't
be able to capture input.  Setting autolock=false will fix the issue.

Finally, you'll need to install tesseract version 3.05 to be able to
use packages that use it.  Tesseract 4.00+ is not (yet) recommended.


Commands for Ubuntu:

apt-get install -y imagemagick xdotool xbindkeys 
cp xbindkeysrc ~/.xbindkeysrc


See tesseract-ocr docs for installing tessearct 3.05.



Once installed, run ztranslate.sh to start.

-----------
Change log
----------- 

v1.02:
   -Fixed window clipping bug (windows)
   -Added config options for key binds in windows
   -Added config options for language preferences
   -Added config options for font
   -Added some Text-to-Speech options

v1.01:
   -Linux supported
   -Added in translation server support.
   -Moving textbox algorithm supported.

v1.0:
   -First release.
