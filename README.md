# Python Easy Chess GUI
A Chess GUI based from Python using PySimpleGUI and Python-Chess modules. Users can also load a chess engine and play with it. This program is based on a [demo chess against ai](https://github.com/PySimpleGUI/PySimpleGUI/tree/master/Chess) from PySimpleGUI.<br>

![](https://i.imgur.com/X2DoJRd.png)

### Requirements
Windows exe file will be available upon release. In the meantime to get it running the following are required.
* Python 3.7 and up
* Python-chess v0.28.0 and up
* PySimpleGUI
* Pyperclip

### Installation
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

### How to play
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

#### To Unhide engine search info
* You should be in Play mode, Engine->Unhide Search Info

### Credits
* PySimpleGUI<br>
https://github.com/PySimpleGUI/PySimpleGUI
* Python-Chess<br>
https://github.com/niklasf/python-chess
* Pyperclip<br>
https://github.com/asweigart/pyperclip
