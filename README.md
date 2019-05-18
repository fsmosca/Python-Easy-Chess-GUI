# Python Easy Chess GUI
A Chess GUI based from Python using PySimpleGUI and Python-Chess modules. Users can also load a chess engine and play with it. This program is based on a [demo chess against ai](https://github.com/PySimpleGUI/PySimpleGUI/tree/master/Chess) from PySimpleGUI.<br>

![](https://i.imgur.com/H4FzPdk.png)

![](https://i.imgur.com/MdKGWHO.png)

### Requirements
I have not yet build an exe file for this GUI, not sure either if I can create it. In the meantime to get it running the following are required.
* Python 3.7 and up
* Python-chess v0.27.3 and up
* PySimpleGUI
* Pyperclip

### Installation
* Python Easy Chess GUI<br>
Download the files including the Images and Engines dir. You can use your favorite uci chess engine like stockfish by copying it into the engines dir.
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
* Game->New Game
* Move the piece you want to move
* Press the square you want the piece to move to

#### To play as black
* Game->Exit Game
* Board->Flip
* Game->New Game
* Engine->Go

#### To paste a FEN
* Game->Exit Game
* FEN->Paste
* If you play as white, make your move
* If you play as black, Engine->Go

### Credits
* PySimpleGUI<br>
https://github.com/PySimpleGUI/PySimpleGUI
* Python-Chess<br>
https://github.com/niklasf/python-chess
* Pyperclip
https://github.com/asweigart/pyperclip
