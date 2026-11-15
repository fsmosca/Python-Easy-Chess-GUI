# Python Easy Chess GUI
A Chess GUI based from Python using FreeSimpleGUI and Python-Chess modules. Users can also load a chess engine and play with it. This program is based on a [demo chess against ai](https://github.com/PySimpleGUI/PySimpleGUI/tree/master/Chess) from [PySimpleGUI](https://github.com/PySimpleGUI/PySimpleGUI).

![](https://i.imgur.com/DT0lOO2.png)

### A. Requirements
If you want to run from the python source the following are required or see the installation section below.
* Python 3.8 and up
* Python-chess v0.28.0 and up
* FreeSimpleGUI 5.0.0 and up
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
* [Panels and layout](#panels-and-layout)
* [Board appearance](#board-appearance)
* [Files the app writes](#files-the-app-writes)

#### Modes
The GUI opens directly in **Play** mode, ready to play. There are two modes:
* **Play** — the default; play a game against the opponent engine. All setup (engine, time, book, settings, board colors) is done from the same menubar **before a game starts**; the setup menu items are grayed out while a game is running and come back after `Game → New` or when the game ends.
* **Review** — step through a saved game with optional engine analysis and threat. Enter with `Mode → Review` (before a game starts), leave with `Mode → Play`.

#### Start the GUI
* From source: `python python_easy_chess_gui.py`
* Or run the prebuilt `.exe`.

#### Play a game
* **As white:** just click the piece and the destination square (or drag the piece). Your first move starts the game and the clocks.
* **As black:** press `Engine → Go` before making a move — the engine takes White and moves first, and the board flips so Black is at the bottom. `Game → New` returns you to White.
* **Flip the board:** `Board → Flip`, at any time — before, during or after a game. The game is not affected.
* **Force the engine to move now:** `Engine → Move Now`.
* **Start a new game:** `Game → New`.
* **Paste a position (FEN):** `Game → Paste FEN` (before a game starts). If the side to move is not yours, press `Engine → Go`.
* **End a game manually:** `Game → Resign`, `User Wins`, or `User Draws`.
* **Save games:** every game auto-saves to `pecg_auto_save_games.pgn`. During a game the `Game` menu also offers *Save to My Games* and *Save to White / Black Repertoire*.
* **Time control:** `Settings → Time → User` (your clock) and `Settings → Time → Engine` (opponent clock), set before a game starts.

#### Engine setup and management
Only **UCI** engines are supported. All engine actions are available **before a game starts**.
* **Install:** `Engine → Manage → Install`, press **Add** and locate the engine executable. On Linux make it executable first: `chmod +x your_engine`.
* **Configure options:** `Engine → Manage → Edit`, select the engine and press **Modify** (set Hash, Threads, etc.). Recommended right after installing.
* **Delete:** `Engine → Manage → Delete`.
* **Set the opponent:** `Engine → Set Engine Opponent` — the engine you play against.
* **Set the adviser:** `Engine → Set Engine Adviser`. During a game, right-click the **Adviser** label and press **Start** for a suggested move and score.
* **Set the analysis engine:** `Engine → Set Engine Analysis` — used by the **Analysis** button in Review mode.
* **Set the threat engine:** `Engine → Set Engine Threat` — used by the **Threat** button in Review mode.
* **Search depth:** `Engine → Set Depth` caps the depth of the playing and adviser engines. Review analysis/threat are limited by **time** instead (see Settings).

#### Review mode — replay and analyse
* **Open a PGN file:** `Mode → Review`, then `Game → Select Game`: choose a PGN file (or pick one from the **Recent** drop-down), then select a game and press **OK** — or double-click it. Click a column heading (White, Black, Result, Date, Event) to sort the game list. The file opened last is loaded again the next time.
* **Switch games:** the **Game list** panel shows the games of the PGN file. Click a game to put it on the board, or use the **Up / Down** keys in the list. Click a column heading to sort, and again to reverse the order. Analysis and Threat, if they are on, follow the board to the new game.
* **Navigate:** use the arrow buttons under the board (first, previous, next, last), the **Left / Right** arrow keys (**Home / End** for first/last position), or click a move in the move list to jump to that position.
* **Analysis:** press the **Analysis** button (in the Analysis panel) to evaluate the current position (multi-line principal variations). The search stops after the *analysis time* (default 60s) and restarts automatically when you change position.
* **Threat:** press the **Threat** button (in the Threat panel) to see what the opponent would play if the side to move passed (a null move). It is unavailable when the side to move is in check, and stops after the *threat time* (default 30s).
* **Reading the output:** each box starts with the search figures (depth and selective depth, time, nodes, nodes per second), followed by one line per variation: the score, then the moves with move numbers. The score is in pawns for the side to move (for Threat that is the opponent, who moves after the pass); `#3` means that side mates in 3 and `-#3` that it is mated in 3. A line is as long as the panel is wide (a cut line ends with `…`), so widen the panel or put it under the board to see more moves.
* **Hash, Threads and MultiPV:** set them in the Analysis panel (Hash and Threads also in the Threat panel). MultiPV is the number of lines shown, 1 to 10. The values are saved, and a running search restarts with the new value. A setting the engine does not have is greyed out.
* **Auto-Analyze Game:** `Game → Auto-Analyze Game` annotates every move with the engine and time per move you choose. Each move gets an evaluation comment, from the point of view of the side that played it (positive is good for that side); bad moves are marked `?!` `?` `??`. When the engine's move is at least 25cp better than the game move (and its own score stays within ±300cp), the better line is replayed engine-vs-engine for up to 5 plies and added as a *Better is* variation labeled with the evaluation after the line's last move, from the same side's point of view. The annotated game is appended to `pecg_analyzed_games.pgn` and replaces the current review game. `Game → Cancel Analysis` stops early.
* **Flip the board:** the flip button at the end of the bar under the board, or `Board → Flip`.

Both analysis and threat run their engines for at most their configured time and then go idle, so they do not keep the CPU busy after a position has been evaluated.

#### Settings / Game
Open with `Settings → General` (before a game starts). **All values are saved to `pecg_settings.json` and restored on the next startup.**
* **Save time left in game notation** — adds `[%clk h:mm:ss]` move comments, shown in the move list and saved to the PGN.
* **Adjudicate game on time forfeit** — ends the game when a player runs out of time.
* **Review analysis time (sec)** — time cap for the Review **Analysis** engine. Default **60**, range 1–3600.
* **Review threat time (sec)** — time cap for the Review **Threat** engine. Default **30**, range 1–3600.

#### Opponent book
* `Settings → Set Book` (before a game starts) sets the opponent's polyglot book. It is named `pecg_book.bin` and lives in the `Book` folder. Build your own polyglot book, name it `pecg_book.bin` and replace the default to change it.

#### Show / hide info panels
These work in **Play** mode by right-clicking the panel's label:
* **Engine search info:** right-click *Opponent Search Info* → **Show** / **Hide**.
* **Opening books:** right-click *BOOK 1* or *BOOK 2* → **Show** / **Hide**.

#### Panels and layout
Both windows are made of panels around the board.
* **Play:** Players, Move list, Comment, Opening books and Engine.
* **Review:** Game list, Game details, Book moves, Move list, Threat and Analysis. The Threat and Analysis buttons sit in their own panels. The bar of buttons under the board (first, previous, next, last and flip) is part of the board: it stays under it, and panels placed below the board come under it.

Each mode keeps its own arrangement.
* **Move a panel:** drag it by its title bar to the left of the board, to the right, or below it. A green bar shows where it will land. `View → Move Panel` does the same from the menu.
* **Ready-made arrangements:** `View → Board Left`, `Board Centre` or `Board Right`, plus `Engine Below Board` in Play and `Analysis Below Board` in Review.
* **Resize:** drag the divider between two panels, or between the board and the panels beside it. The board takes the largest size that fits. Beside the board, spare height goes to the Move list, or to the last panel of a column without it.
* **Several panels under the board:** drop a panel on the top or bottom edge of a panel that is already there to put it above or below it (for example board, Analysis, Threat), or on its middle to put it beside it. `View → Move Panel → Below Board` adds it as a new row at the bottom.
* **Height of the panels under the board:** drag the divider between the board and those panels up or down to make them taller or shorter. The board keeps its size and the window changes height instead. In a maximized window the divider stays where you drop it, and the board takes the largest size that fits above it.
* **Saved:** the arrangement, the sizes and the window size are saved in `pecg_settings.json` and restored at the next start. `View → Reset Layout` goes back to the default.
* **Whose turn:** two dots beside the board, level with each player's back rank; the green one marks the side to move.

All of this works at any time, including during a game or while an analysis is running.

#### Board appearance
* **Flip:** `Board → Flip`, at any time — including while a game is running or the engine is thinking. The game is not affected.
* **Size:** `Board → Size` picks a board size — Small (360), Medium (480), Large (600), X-Large (720), XX-Large (840) or Huge (960) pixels — at any time, like Flip. On first start the largest board that fits the screen is chosen automatically; the size is saved and restored.
* **Resizable windows:** the Play and Review windows can be maximized or drag-resized. The board switches to the largest of these sizes that fits and the side panels absorb the remaining space.
* **Colors / theme:** `Board → Color` for square colors and `Board → Theme` for the overall GUI theme (before a game starts).

#### Files the app writes
* `pecg_auto_save_games.pgn` — every game played.
* `pecg_analyzed_games.pgn` — games annotated by Review mode's Auto-Analyze.
* `pecg_engines.json` — installed engines and their options.
* `pecg_user.json` — user name(s).
* `pecg_settings.json` — Settings/Game values (checkboxes and review times).
* `pecg_log.txt` — log file.

### E. Credits
* FreeSimpleGUI<br>
https://github.com/spyoungtech/FreeSimpleGUI
* Python-Chess<br>
https://github.com/niklasf/python-chess
* The Week in Chess<br>
https://theweekinchess.com/
* PyInstaller<br>
https://github.com/pyinstaller/pyinstaller
* pgn-extract<br>
https://www.cs.kent.ac.uk/people/staff/djb/pgn-extract/
