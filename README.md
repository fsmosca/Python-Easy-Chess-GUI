# Python Easy Chess GUI
A Chess GUI based from Python using PySimpleGUI and Python-Chess modules. Users can also load a chess engine and play with it. This program is based on a [demo chess against ai](https://github.com/PySimpleGUI/PySimpleGUI/tree/master/Chess) from PySimpleGUI.<br>

![](https://i.imgur.com/J09H5GX.png)

### A. Requirements
Windows exe file will be available upon release. In the meantime to get it running the following are required.
* Python 3.7 and up
* Python-chess v0.28.0 and up
* PySimpleGUI 4.0.0
* Pyperclip

### B. Installation
* Python Easy Chess GUI<br>
Download the files including the Images, Engines and Book directories. You can use your favorite uci chess engine like stockfish by copying it into the engines dir.
* Python 3<br>
https://www.python.org/downloads/
* Python-Chess<br>
https://github.com/niklasf/python-chess<br>
pip install python-chess
* PySimpleGUI<br>
https://github.com/PySimpleGUI/PySimpleGUI<br>
pip install pysimplegui
* Pyperclip<br>
https://github.com/asweigart/pyperclip<br>
pip install pyperclip

### C. How to play
* Execute python_easy_chess_gui.py<br>
Typical command line:<br>
`python python_easy_chess_gui.py`

#### To play as white
* Mode->Play
* Move the piece you want to move
* Press the square you want the piece to move to

#### To play as black
* If current mode is Neutral, Board->Flip, flip such that black pieces are at the bottom
* If current mode is Play, Mode->Neutral, then Board->Flip
* Mode->Play
* Engine->Go

#### To paste a FEN
* You should be in Play mode. If not, then Mode->Play
* FEN->Paste
* If you play as white, you can make your move
* If you play as black, Engine->Go

#### To flip board
* If current mode is Neutral, Board->Flip
* If current mode is Play, Mode->Neutral, then Board->Flip

#### To set book options
* Book->Set Book

#### To select engine
* Engine->Set Engine

#### To Hide/Unhide engine search info
* Press the ENGINE SEARCH INFO text

#### To Hide/Unhide Book info
* Press the Book 1 or Book 2 text

### D. GUI/User process flow
1. This app has 2 modes Neutral and Play. After executing the app the user is brought to Neutral mode.

2. In Neutral mode user can
  * Flip the board
    * If user wants to play as black
  * Quit the app
  * Set engine opponent
    * Select engine
    * Set Threads
    * Set Hash
  * Set opponent engine opening book settings
    * Enable/disable book
    * Set best move / random book moves
  * Set opponent engine thinking time and maximum search depths
  * Set engine adviser
    * Select engine
    * Set Threads
    * Set Hash
    * Set thinking time
  + Change to Play mode <br>
    Play mode has 2 main states
    1. User to move
      * User can make a move on the board by pressing the from square and the to square
      * User can make the engine think and play a move by pressing Engine->Go
      * Paste a FEN
        * Use wants to play from a different position than the usual startposition
      * Set engine opponent
        * Select engine
        * Set Threads
        * Set Hash
      * Set opponent engine opening book settings
        * Enable/disable book
        * Set best move / random book moves
      * Set opponent engine thinking time and maximum search depths
      * Can ask opening book assistance
      * Can ask adviser engine on its best move and/or principal variation
        * After pressing the text Advise button, the adviser will search for best move. Once the color of pv line becomes blue that means it is done thinking and the user can now make a move on the board.
      * Can Save game
      * Change to Neutral mode
    2. Engine opponent to move
      * User can interrupt engine while thinking by
        * Move now
        * New Game
        * Quit the app
        * Hide/unhide engine search info
        * Hide/unhide 2 user books
        * Change mode back to neutral

### E. Credits
* PySimpleGUI<br>
https://github.com/PySimpleGUI/PySimpleGUI
* Python-Chess<br>
https://github.com/niklasf/python-chess
* Pyperclip<br>
https://github.com/asweigart/pyperclip
* The Week in Chess<br>
https://theweekinchess.com/
* PyInstaller<br>
https://github.com/pyinstaller/pyinstaller
