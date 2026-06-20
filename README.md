# Python Easy Chess GUI
A Chess GUI based from Python using FreeSimpleGUI and Python-Chess modules. Users can also load a chess engine and play with it. This program is based on a [demo chess against ai](https://github.com/PySimpleGUI/PySimpleGUI/tree/master/Chess) from [PySimpleGUI](https://github.com/PySimpleGUI/PySimpleGUI).

![](https://i.imgur.com/DT0lOO2.png)

Command line to compile the source to exe using pyinstaller.

```
pyinstaller python_easy_chess_gui.py -F -w
```

Then add the folders for the exe to work.

### A. Requirements
If you want to run from the python source the following are required or see the installation section below.
* Python 3.7 and up
* Python-chess v0.28.0 and up
* FreeSimpleGUI 5.0.0 and up
* Pyperclip
* Download this repo

Or you can just download the [executable file](https://github.com/fsmosca/Python-Easy-Chess-GUI/releases) along with other files such as book and images.

### B. Features
#### 1. Save games to repertoire pgn files
![](https://i.imgur.com/iXO2abq.png)

#### 2. Install uci engine of your choice
![](https://i.imgur.com/GErKZFy.png)

#### 2.1 It is recommended to configure the engine setting after installation
Configure engine via Engine->Manage->Edit, select engine and press modify.

![](https://i.imgur.com/PmDzCvz.png)

#### 3. Need book assistance? Right-click on BOOK 2 and press show
![](https://i.imgur.com/SdgNdr6.png)

#### 4. Need what engine adviser will think about the position? Right-click on Adviser and press start
![](https://i.imgur.com/Jziws5W.png)

#### 5. Replay game with engine analysis in Review Mode

<img width="1352" height="868" alt="image" src="https://github.com/user-attachments/assets/212351b8-f62d-4782-a287-cff63193b4d7" />

### C. Installation
1. If you want to run from the source code
* Python Easy Chess GUI<br>
Download the files including the Images, Engines and Book directories. You can use your favorite uci chess engine like stockfish by copying it into the engines dir.
* Python 3<br>
https://www.python.org/downloads/
* Python-Chess<br>
https://github.com/niklasf/python-chess<br>
pip install python-chess
* FreeSimpleGUI<br>
https://github.com/spyoungtech/FreeSimpleGUI<br>
pip install FreeSimpleGUI
* Pyperclip<br>
https://github.com/asweigart/pyperclip<br>
pip install pyperclip
2. If you want to run from the exe
* Download the exe file from the release link

#### Note

If you are on linux be sure to give permission to uci engine with:
`chmod +x uci_engine_fn`.

### D. How to use

This is the detailed manual. Inside the app, the **Help** menu gives short,
task-focused versions of these topics (adapted to the current mode), and
**Help → Online Help** opens this page.

**Contents**
* [Modes](#modes)
* [Start the GUI](#start-the-gui)
* [Play a game](#play-a-game)
* [Engine setup and management](#engine-setup-and-management)
* [Review mode — replay and analyse](#review-mode--replay-and-analyse)
* [Settings / Game](#settings--game)
* [Opponent book](#opponent-book)
* [Show / hide info panels](#show--hide-info-panels)
* [Board appearance](#board-appearance)
* [Files the app writes](#files-the-app-writes)

#### Modes
The GUI has three modes, switched from the **Mode** menu:
* **Neutral** — the default after startup; engine/board/settings setup is done here.
* **Play** — play a game against the opponent engine.
* **Review** — step through a saved game with optional engine analysis and threat.

#### Start the GUI
* From source: `python python_easy_chess_gui.py`
* Or run the prebuilt `.exe`.

#### Play a game
* **As white:** `Mode → Play`, then click the piece and the destination square (or drag the piece).
* **As black:** in Neutral mode `Board → Flip` (black at the bottom), then `Mode → Play` and `Engine → Go` so the engine moves first. (If already in Play, switch to Neutral first.)
* **Force the engine to move now:** `Engine → Move Now`.
* **Start a new game:** `Game → New`.
* **Paste a position (FEN):** in Play mode `FEN → Paste`. If it is black to move, then `Engine → Go`.
* **End a game manually:** `Game → Resign`, `User Wins`, or `User Draws`.
* **Save games:** every game auto-saves to `pecg_auto_save_games.pgn`. The `Game` menu also offers *Save to My Games* and *Save to White / Black Repertoire*.
* **Time control:** `Time → User` (your clock) and `Time → Engine` (opponent clock).

#### Engine setup and management
Only **UCI** engines are supported. All engine actions are done in **Neutral** mode.
* **Install:** `Engine → Manage → Install`, press **Add** and locate the engine executable. On Linux make it executable first: `chmod +x your_engine`.
* **Configure options:** `Engine → Manage → Edit`, select the engine and press **Modify** (set Hash, Threads, etc.). Recommended right after installing.
* **Delete:** `Engine → Manage → Delete`.
* **Set the opponent:** `Engine → Set Engine Opponent` — the engine you play against.
* **Set the adviser:** `Engine → Set Engine Adviser`. During a game, right-click the **Adviser** label and press **Start** for a suggested move and score.
* **Set the analysis engine:** `Engine → Set Engine Analysis` — used by the **Analysis** button in Review mode.
* **Set the threat engine:** `Engine → Set Engine Threat` — used by the **Threat** button in Review mode.
* **Search depth:** `Engine → Set Depth` caps the depth of the playing and adviser engines. Review analysis/threat are limited by **time** instead (see Settings).

#### Review mode — replay and analyse
* **Open a game:** `Mode → Review`, choose a PGN file, select a game and press **OK**. Switch games later with `Game → Load PGN` or `Game → Select Game`.
* **Navigate:** use **First / Previous / Next / Last** below the board, or click a move in the move list to jump to that position.
* **Analysis:** press the **Analysis** button to evaluate the current position (multi-line principal variations). The search stops after the *analysis time* (default 60s) and restarts automatically when you change position.
* **Threat:** press the **Threat** button to see what the opponent would play if the side to move passed (a null move). It is unavailable when the side to move is in check, and stops after the *threat time* (default 30s).
* **Flip the board:** `Board → Flip` within Review mode.

Both analysis and threat run their engines for at most their configured time and then go idle, so they do not keep the CPU busy after a position has been evaluated.

#### Settings / Game
Open with `Settings → Game` (Neutral mode). **All values are saved to `pecg_settings.json` and restored on the next startup.**
* **Save time left in game notation** — adds `[%clk h:mm:ss]` move comments, shown in the move list and saved to the PGN.
* **Adjudicate game on time forfeit** — ends the game when a player runs out of time.
* **Review analysis time (sec)** — time cap for the Review **Analysis** engine. Default **60**, range 1–3600.
* **Review threat time (sec)** — time cap for the Review **Threat** engine. Default **30**, range 1–3600.

#### Opponent book
* `Book → Set Book` (Neutral mode) sets the opponent's polyglot book. It is named `pecg_book.bin` and lives in the `Book` folder. Build your own polyglot book, name it `pecg_book.bin` and replace the default to change it.

#### Show / hide info panels
These work in **Play** mode by right-clicking the panel's label:
* **Engine search info:** right-click *Opponent Search Info* → **Show** / **Hide**.
* **Opening books:** right-click *BOOK 1* or *BOOK 2* → **Show** / **Hide**.

#### Board appearance
* **Flip:** Neutral mode `Board → Flip` (or `Mode → Neutral` first if you are in Play).
* **Colors / theme:** `Board → Color` for square colors and `Board → Theme` for the overall GUI theme (Neutral mode).

#### Files the app writes
* `pecg_auto_save_games.pgn` — every game played.
* `pecg_engines.json` — installed engines and their options.
* `pecg_user.json` — user name(s).
* `pecg_settings.json` — Settings/Game values (checkboxes and review times).
* `pecg_log.txt` — log file.

### E. Credits
* FreeSimpleGUI<br>
https://github.com/spyoungtech/FreeSimpleGUI
* Python-Chess<br>
https://github.com/niklasf/python-chess
* Pyperclip<br>
https://github.com/asweigart/pyperclip
* The Week in Chess<br>
https://theweekinchess.com/
* PyInstaller<br>
https://github.com/pyinstaller/pyinstaller
* pgn-extract<br>
https://www.cs.kent.ac.uk/people/staff/djb/pgn-extract/
