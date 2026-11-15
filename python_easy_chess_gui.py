#!/usr/bin/env python3
"""
python_easy_chess_gui.py

Requirements:
    Python 3.8 and up

PySimpleGUI Square Mapping
board = [
    56, 57, ... 63
    ...
    8, 9, ...
    0, 1, 2, ...
]

row = [
    0, 0, ...
    1, 1, ...
    ...
    7, 7 ...
]

col = [
    0, 1, 2, ... 7
    0, 1, 2, ...
    ...
    0, 1, 2, ... 7
]


Python-Chess Square Mapping
board is the same as in PySimpleGUI
row is reversed
col is the same as in PySimpleGUI

"""

import FreeSimpleGUI as sg
import os
import sys
import subprocess
import threading
from pathlib import Path, PurePath  # Python 3.4 and up
import queue
import copy
import time
from datetime import datetime
import json
import chess
import chess.pgn
import chess.engine
import chess.polyglot
import logging
import webbrowser
import tkinter as tk
import tkinter.font as tkfont
import platform as sys_plat


log_format = '%(asctime)s :: %(funcName)s :: line: %(lineno)d :: %(levelname)s :: %(message)s'
logging.basicConfig(
    filename='pecg_log.txt',
    filemode='w',
    level=logging.INFO,
    format=log_format
)

# python-chess logs every UCI line exchanged with the engine at DEBUG level.
# During live (infinite/long) analysis this floods pecg_log.txt with thousands
# of lines and adds constant disk I/O, so keep the engine-communication logger
# quiet regardless of the root level.
logging.getLogger('chess.engine').setLevel(logging.WARNING)


APP_NAME = 'Python Easy Chess GUI'
APP_VERSION = 'v2.41.1'
BOX_TITLE = f'{APP_NAME} {APP_VERSION}'
REVIEW_MAX_DISPLAY_GAMES = 10000
REVIEW_ANALYSIS_MULTIPV_LINES = 3   # lines of analysis, until changed
REVIEW_ANALYSIS_MULTIPV_MAX = 10    # most lines the Analysis panel offers
# Hash sizes in MB offered by the Analysis and Threat panels (those the
# engine accepts, plus the size it has now).
REVIEW_HASH_CHOICES_MB = [16, 32, 64, 128, 256, 512, 1024, 2048, 4096,
                          8192, 16384]
# Colour of the line of search figures (depth, time, nodes) in the
# Analysis and Threat boxes; readable on light and dark themes.
REVIEW_INFO_COLOR = '#7a7f87'
REVIEW_NAV_DEBOUNCE_SEC = 0.3
REVIEW_MOVE_LIST_HEIGHT = 4   # lines, until its panel is made taller
REVIEW_GAME_LIST_ROWS = 4     # games, until its panel is made taller
# Columns of the Game list panel and their widths in characters. The
# first four fit a panel of the default width; the rest is reached with
# the scrollbar under the list, or by making the panel wider.
REVIEW_GAME_LIST_HEADINGS = ['#', 'White', 'Black', 'Result', 'Date', 'Event']
REVIEW_GAME_LIST_WIDTHS = [5, 14, 14, 8, 11, 16]
# Lines of the Analysis and Threat boxes until their panel is made
# taller: the search figures, then one line per variation.
REVIEW_ANALYSIS_BOX_HEIGHT = 1 + REVIEW_ANALYSIS_MULTIPV_LINES
REVIEW_THREAT_BOX_HEIGHT = 2
# Output file for games annotated by the Review-mode auto-analyzer.
AUTO_ANALYSIS_OUTPUT_FILE = 'pecg_analyzed_games.pgn'
# How many recently opened review PGN paths to remember in the settings.
MAX_RECENT_PGN_FILES = 10
# Engine variations are rebuilt by replaying the line engine vs engine for
# up to this many plies - a search PV can be as short as a single move, so
# the reported PV is not trusted for the variation moves. The replay always
# searches with MultiPV 1 (best line only); user-settable in the dialog.
AUTO_ANALYSIS_REPLAY_PLIES = 5
AUTO_ANALYSIS_REPLAY_PLIES_MIN = 1
AUTO_ANALYSIS_REPLAY_PLIES_MAX = 20
# Number of engine lines (MultiPV) per analyzed move. Disabled (kept at 1)
# for now; praise NAGs and Alt: lines need MultiPV >= 2 to reappear.
AUTO_ANALYSIS_MULTIPV = 1
AUTO_ANALYSIS_MULTIPV_MAX = 5
# The engine's line is added as a variation when its score beats the game
# move by at least this many centipawns (mover POV). Below this gap the
# variation is skipped entirely.
AUTO_ANALYSIS_ALT_MIN_CP = 5
# At or above this gap the variation gets the "Better is" pre-comment; a
# gap between ALT_MIN and this is written as a bare line (no pre-comment).
AUTO_ANALYSIS_BETTER_MIN_CP = 15
# Variations are only added when the engine's own score is within this many
# centipawns of equal (mover POV) - skip variations in already-decided
# positions.
AUTO_ANALYSIS_BETTER_MAX_ABS_CP = 300
# Auto-analysis time per move, in milliseconds. UCI engines are fine with
# very short searches, so the floor is 100 ms; the value is handed to the
# engine as a seconds float via chess.engine.Limit.
AUTO_ANALYSIS_TIME_MS = 1000
AUTO_ANALYSIS_TIME_MS_MIN = 100
AUTO_ANALYSIS_TIME_MS_MAX = 60000
# Time caps (seconds) for Review-mode searches. Without a cap these run
# "go infinite" and peg the CPU until the user navigates away. Editable via
# Settings/Game and persisted in the settings file.
REVIEW_ANALYSIS_TIME_SEC = 60   # default analysis time cap
REVIEW_THREAT_TIME_SEC = 30     # default threat time cap
REVIEW_ANALYSIS_TIME_MIN = 1
REVIEW_ANALYSIS_TIME_MAX = 3600


platform = sys.platform
sys_os = sys_plat.system()


# Consolas ships with Windows but not with stock Linux. Without a real monospace
# font, Tk silently falls back to a proportional one, which breaks the
# character-based right-edge alignment of the info panels (every element is sized
# in character units). Pick a monospace font that exists on each platform.
def _default_mono_font():
    try:
        temp_root = tk.Tk()
        temp_root.withdraw()
        import tkinter.font as tkfont
        available = tkfont.families(temp_root)
        temp_root.destroy()

        if platform == 'win32':
            preferred = ['Consolas', 'Courier New', 'Courier']
        elif platform == 'darwin':
            preferred = ['Menlo', 'Monaco', 'Courier New', 'Courier']
        else:
            preferred = ['DejaVu Sans Mono', 'Liberation Mono', 'Ubuntu Mono', 'Courier New', 'Courier', 'monospace']

        for f in preferred:
            if f in available:
                return f
    except Exception:
        pass

    if platform == 'win32':
        return 'Consolas'
    if platform == 'darwin':
        return 'Menlo'
    return 'DejaVu Sans Mono'   # present on essentially every Linux desktop


FONT_NAME = _default_mono_font()
if platform == 'win32':
    FONT_BASE = (FONT_NAME, 10)
    FONT_SMALL = (FONT_NAME, 9)
elif platform == 'darwin':
    FONT_BASE = (FONT_NAME, 10)
    FONT_SMALL = (FONT_NAME, 9)
else:
    FONT_BASE = (FONT_NAME, 9)
    FONT_SMALL = (FONT_NAME, 8)
# Title bar of a panel.
FONT_PANEL_TITLE = (FONT_NAME, FONT_BASE[1], 'bold')
FONT_NAV_ICON = (FONT_NAME, FONT_BASE[1] + 4, 'bold')   # Review nav bar

# Small font for the board coordinate labels drawn on the canvas.
# Board edge coordinate labels use FONT_NAME at a size scaled with the
# board (see paint_square).


# The top menu BAR font can't be set through FreeSimpleGUI (its font= only styles
# the drop-down submenus). The native Windows menubar uses Segoe UI 9; on Linux
# Tk draws the menubar itself with its own default (DejaVu Sans 10), so it looks
# bigger and a different family. Match Windows' size/class on Linux; leave the
# native menubar untouched elsewhere (None -> no change).
def _default_menu_font():
    if platform == 'win32':
        return None
    if platform == 'darwin':
        return None
    return ('DejaVu Sans', 9)


MENU_FONT = _default_menu_font()


ico_path = {
    'win32': {'pecg': 'Icon/pecg.ico', 'enemy': 'Icon/enemy.ico', 'adviser': 'Icon/adviser.ico'},
    'linux': {'pecg': 'Icon/pecg.png', 'enemy': 'Icon/enemy.png', 'adviser': 'Icon/adviser.png'},
    'darwin': {'pecg': 'Icon/pecg.png', 'enemy': 'Icon/enemy.png', 'adviser': 'Icon/adviser.png'}
}


MIN_DEPTH = 1
MAX_DEPTH = 1000
# Numbers in the setup dialogs are picked from drop-down lists or up/down
# arrows, never typed, so a dialog cannot be handed an invalid value. These
# are the choices offered. (Engine UCI options are the exception: their
# ranges are too wide for a list, so they stay typed and are validated.)
TC_BASE_MAX_MIN = 180    # base time: 0..180 minutes plus 0..59 seconds
TC_INC_MAX_SEC = 60      # increment: 0..60 seconds
MAX_BOOK_PLY = 32        # opponent book: 1..32 plies
DEPTH_CHOICE_MAX = 100   # Set Depth: 1..100, or no limit (MAX_DEPTH)
DEPTH_NO_LIMIT = 'No limit'
# Seconds offered for the review analysis/threat and adviser move times.
TIME_CHOICES_SEC = [1, 2, 3, 5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 300,
                    600, 900, 1800, 3600]
# Milliseconds per move offered by the Auto-Analyze dialog.
AUTO_ANALYSIS_TIME_CHOICES_MS = [100, 200, 300, 500, 1000, 2000, 3000, 5000,
                                 10000, 15000, 30000, 60000]


def choices_with(choices, current):
    """Return ``choices`` as a sorted list that also offers ``current``.

    Keeps a previously saved value selectable when it is not one of the
    standard choices.
    """
    return sorted(set(choices) | {current})


# PGN files are written as UTF-8 on every platform. Without an explicit
# encoding Windows uses its legacy code page, which cannot store most
# non-English names and does not match what Review reads.
PGN_ENCODING = 'utf-8'


def pgn_file_encoding(path):
    """Return the encoding to read (and rewrite) an existing PGN file with.

    UTF-8 when the whole file decodes as UTF-8. Otherwise None, the system
    default: older versions of this app, and some other tools, wrote PGN
    in the system code page, and such a file must be rewritten the same
    way to keep its names intact.
    """
    try:
        with open(path, encoding=PGN_ENCODING) as f:
            for _ in f:
                pass
    except UnicodeDecodeError:
        return None
    return PGN_ENCODING
MANAGED_UCI_OPTIONS = ['ponder', 'uci_chess960', 'multipv', 'uci_analysemode', 'ownbook']
# Engine role -> (active id-name attr, file attr, path attr, icon key, title).
ROLE_META = {
    'opponent': ('opp_id_name', 'opp_file', 'opp_path_and_file', 'enemy', 'Opponent'),
    'adviser': ('adviser_id_name', 'adviser_file', 'adviser_path_and_file', 'adviser', 'Adviser'),
    'analysis': ('analysis_id_name', 'analysis_file', 'analysis_path_and_file', 'pecg', 'Analysis'),
    'threat': ('threat_id_name', 'threat_file', 'threat_path_and_file', 'pecg', 'Threat'),
}
GUI_THEME = [
    'Green', 'GreenTan', 'LightGreen', 'BluePurple', 'Purple', 'BlueMono', 'GreenMono', 'BrownBlue',
    'BrightColors', 'NeutralBlue', 'Kayak', 'SandyBeach', 'TealMono', 'Topanga', 'Dark', 'Black', 'DarkAmber'
]

IMAGE_DIR = 'Images'      # one folder of piece images per square size
IMAGE_PATH = 'Images/60'  # the original set; also the fallback
BASE_SQUARE_PX = 60       # square size of the original set
# Board -> Size menu: label to square size in px (labels show the board
# width; the board is 8 squares wide). Each size has its own ready-made
# piece images in Images/<square size>, so no image library is needed at
# run time. Resizing a window picks the largest of these sizes that fits.
BOARD_SIZE_LABELS = {
    'Small (360)': 45,
    'Medium (480)': 60,
    'Large (600)': 75,
    'X-Large (720)': 90,
    'XX-Large (840)': 105,
    'Huge (960)': 120,
}
BOARD_SQUARE_SIZES = sorted(BOARD_SIZE_LABELS.values())
BOARD_SQUARE_MIN_PX = BOARD_SQUARE_SIZES[0]
BOARD_SQUARE_MAX_PX = BOARD_SQUARE_SIZES[-1]


def fit_square_px(square_px, min_px=BOARD_SQUARE_MIN_PX):
    """Return the largest available square size not above ``square_px``.

    The result is never below ``min_px`` (rounded up to an available
    size), even if that is more than ``square_px``.
    """
    lowest = min((s for s in BOARD_SQUARE_SIZES if s >= min_px),
                 default=BOARD_SQUARE_MAX_PX)
    fitting = [s for s in BOARD_SQUARE_SIZES if lowest <= s <= square_px]
    return fitting[-1] if fitting else lowest


# A narrow strip on the right of the board canvas holds the turn marker:
# one dot level with each player's back rank, green for the side to move.
TURN_MARKER_PX = 16
TURN_MARKER_ON = '#2e9e3f'
TURN_MARKER_OFF = '#9aa0a6'

# Panels of the Play window, in their default order in the right zone.
PLAY_PANEL_KEYS = ('play_players_panel_k', 'play_moves_panel_k',
                   'play_comment_panel_k', 'play_books_panel_k',
                   'play_engine_panel_k')
# Panel key -> name shown in its title bar and in the View menu.
PLAY_PANEL_TITLES = {
    'play_players_panel_k': 'Players',
    'play_moves_panel_k': 'Move list',
    'play_comment_panel_k': 'Comment',
    'play_books_panel_k': 'Opening books',
    'play_engine_panel_k': 'Engine',
}
# Ready-made arrangements offered in the View menu: name -> where the
# panels go around the board. 'Board Left' is the default.
PLAY_ARRANGEMENTS = {
    'Board Left': {'right': list(PLAY_PANEL_KEYS)},
    'Board Centre': {'left': ['play_players_panel_k', 'play_engine_panel_k'],
                     'right': ['play_moves_panel_k', 'play_comment_panel_k',
                               'play_books_panel_k']},
    'Board Right': {'left': list(PLAY_PANEL_KEYS)},
    'Engine Below Board': {'right': ['play_players_panel_k',
                                     'play_moves_panel_k',
                                     'play_comment_panel_k',
                                     'play_books_panel_k'],
                           'bottom': ['play_engine_panel_k']},
}

# Panels of the Review window, in their default order.
REVIEW_PANEL_KEYS = ('review_gamelist_panel_k', 'review_game_panel_k',
                     'review_books_panel_k', 'review_moves_panel_k',
                     'review_threat_panel_k', 'review_analysis_panel_k')
REVIEW_PANEL_TITLES = {
    'review_gamelist_panel_k': 'Game list',
    'review_game_panel_k': 'Game details',
    'review_books_panel_k': 'Book moves',
    'review_moves_panel_k': 'Move list',
    'review_threat_panel_k': 'Threat',
    'review_analysis_panel_k': 'Analysis',
}
REVIEW_ARRANGEMENTS = {
    'Board Left': {'right': list(REVIEW_PANEL_KEYS)},
    'Board Centre': {'left': ['review_gamelist_panel_k',
                              'review_game_panel_k', 'review_books_panel_k',
                              'review_threat_panel_k'],
                     'right': ['review_moves_panel_k',
                               'review_analysis_panel_k']},
    'Board Right': {'left': list(REVIEW_PANEL_KEYS)},
    'Analysis Below Board': {'right': ['review_gamelist_panel_k',
                                       'review_game_panel_k',
                                       'review_books_panel_k',
                                       'review_moves_panel_k',
                                       'review_threat_panel_k'],
                             'bottom': ['review_analysis_panel_k']},
}

# What differs between the panel layouts of the two windows: the key of
# the board box, what is fixed under the board inside that box (None:
# nothing), the panels, the ready-made arrangements, the panels that take
# the spare height of their zone, and the name the layout is saved under
# in the settings file.
PANEL_LAYOUTS = {
    'play': {'board': 'play_board_box_k', 'below_board': None,
             'panels': PLAY_PANEL_KEYS,
             'titles': PLAY_PANEL_TITLES, 'arrangements': PLAY_ARRANGEMENTS,
             'stretch': ('play_moves_panel_k',), 'setting': 'play_layout'},
    'review': {'board': 'review_board_box_k',
               'below_board': 'review_nav_bar_k',
               'panels': REVIEW_PANEL_KEYS,
               'titles': REVIEW_PANEL_TITLES,
               'arrangements': REVIEW_ARRANGEMENTS,
               'stretch': ('review_moves_panel_k',),
               'setting': 'review_layout'},
}
# Buttons of the bar under the Review board: (event key, icon, tooltip).
REVIEW_NAV_BUTTONS = (
    ('First', '|\u25c4', 'First position (Home)'),
    ('Previous', '\u25c4', 'Previous move (Left arrow)'),
    ('Next', '\u25ba', 'Next move (Right arrow)'),
    ('Last', '\u25ba|', 'Last position (End)'),
    ('Flip', '\u21c5', 'Flip the board'),
)
# Name of the arrangement a window starts with (in every mode).
DEFAULT_ARRANGEMENT = 'Board Left'
PANEL_ZONE_LABELS = {'Left of Board': 'left', 'Right of Board': 'right',
                     'Below Board': 'bottom'}


def build_view_menu(mode):
    """The View menu of the 'play' or 'review' window: panel arrangement.

    Every item carries '::layout_k:<action>:...' so the event loops can
    pass it to handle_layout_event(). Usable at any time, like Board ->
    Flip.
    """
    spec = PANEL_LAYOUTS[mode]
    move_items = []
    for key in spec['panels']:
        move_items += [spec['titles'][key],
                       ['{}::layout_k:move:{}:{}'.format(label, zone, key)
                        for label, zone in PANEL_ZONE_LABELS.items()]]
    return ['&View', ['{}::layout_k:preset:{}'.format(name, name)
                      for name in spec['arrangements']]
            + ['---', 'Move Panel', move_items,
               '---', 'Reset Layout::layout_k:reset']]
PANEL_BORDER_COLOR = '#9aa0a6'


BLANK = 0  # piece names
PAWNB = 1
KNIGHTB = 2
BISHOPB = 3
ROOKB = 4
KINGB = 5
QUEENB = 6
PAWNW = 7
KNIGHTW = 8
BISHOPW = 9
ROOKW = 10
KINGW = 11
QUEENW = 12


# Absolute rank based on real chess board, white at bottom, black at the top.
# This is also the rank mapping used by python-chess modules.
RANK_8 = 7
RANK_7 = 6
RANK_6 = 5
RANK_5 = 4
RANK_4 = 3
RANK_3 = 2
RANK_2 = 1
RANK_1 = 0


initial_board = [[ROOKB, KNIGHTB, BISHOPB, QUEENB, KINGB, BISHOPB, KNIGHTB, ROOKB],
                 [PAWNB, ] * 8,
                 [BLANK, ] * 8,
                 [BLANK, ] * 8,
                 [BLANK, ] * 8,
                 [BLANK, ] * 8,
                 [PAWNW, ] * 8,
                 [ROOKW, KNIGHTW, BISHOPW, QUEENW, KINGW, BISHOPW, KNIGHTW, ROOKW]]


white_init_promote_board = [[QUEENW, ROOKW, BISHOPW, KNIGHTW]]

black_init_promote_board = [[QUEENB, ROOKB, BISHOPB, KNIGHTB]]


# ---------------------------------------------------------------------------
# Help system
# ---------------------------------------------------------------------------
# Brief, topic-focused help shown in small popups from the Help menu. The full
# reference lives in the project README (its section D.10 lists this menu).
# Each dict key doubles as the "::key" suffix of its Help menu item.
HELP_TOPICS = {
    'help_start': (
        'Getting Started',
        'Python Easy Chess GUI opens in Play mode, ready to play.\n\n'
        '1. Install a UCI engine:  Engine -> Manage -> Install.\n'
        '   (A few engines are installed already.)\n'
        '2. Choose your opponent:  Engine -> Set Engine Opponent.\n'
        '3. Move a piece to start the game, or press Engine -> Go\n'
        '   to play as Black.\n\n'
        'Setup menus are disabled while a game is running; press\n'
        'Game -> New to end it and set up again.\n'
        'Games auto-save to pecg_auto_save_games.pgn.\n\n'
        'To replay and analyse a game:  Mode -> Review.\n\n'
        'Each Help topic is short. The full manual is the README on the\n'
        'project page; Help -> About shows its address.'),
    'help_shortcuts': (
        'Mouse and Keyboard',
        'PLAY\n'
        '  Move a piece       click it, then its square; or drag it\n'
        '  Adviser            right-click Adviser -> Start / Stop\n'
        '  Search info        right-click Opponent Search Info\n'
        '  Book moves         right-click BOOK 1 or BOOK 2\n\n'
        'REVIEW\n'
        '  Left / Right       previous / next move\n'
        '  Home / End         first / last position\n'
        '  Alt+A              Analysis on / off\n'
        '  Alt+T              Threat on / off\n'
        '  Up / Down          previous / next game (in the Game list)\n'
        '  Click a move       jump to that position\n'
        '  Click a heading    sort the Game list by that column\n\n'
        'BOTH MODES\n'
        '  Drag a title bar   move that panel\n'
        '  Drag a divider     resize panels or the board'),
    'help_eng_install': (
        'Install / Manage Engines',
        'Available before a game starts. Only UCI engines are supported.\n\n'
        'Install:\n'
        '  1. Engine -> Manage -> Install, press Add.\n'
        '  2. Press Browse and pick the engine file.\n'
        '  3. Press Get Id Name (or type a name), then OK.\n'
        '  On Linux first allow the file to run:  chmod +x engine\n\n'
        'Options:  Engine -> Manage -> Edit -> pick the engine -> Modify\n'
        '          (Hash, Threads and its other options).\n'
        'Remove:   Engine -> Manage -> Delete.\n\n'
        'After installing, choose what the engine is used for: see\n'
        'Help -> Engine -> Engine for Each Job.'),
    'help_eng_roles': (
        'Engine for Each Job',
        'There are four jobs, each with its own engine. Choose them in\n'
        'the Engine menu (Play mode, before a game starts):\n\n'
        '  Set Engine Opponent   the engine you play against\n'
        '  Set Engine Adviser    suggests a move during a game\n'
        '  Set Engine Analysis   the Analysis button in Review\n'
        '  Set Engine Threat     the Threat button in Review\n\n'
        'In the manager that opens:\n'
        '  Use Selected    make the selected engine do this job\n'
        '  Configure       give it other options for this job only,\n'
        '                  for example more Hash for analysis\n'
        '  Delete Config   remove those options again\n'
        'An engine with its own options for the job is marked\n'
        '(configured).'),
    'help_eng_opponent': (
        'Set Engine Opponent',
        'Engine -> Set Engine Opponent (before a game starts).\n\n'
        'This is the engine you play against. Select one of the\n'
        'installed engines and press Use Selected.\n\n'
        'Its clock:   Settings -> Time -> Engine.\n'
        'Its book:    Settings -> Set Book.\n'
        'Its depth:   Engine -> Set Depth.'),
    'help_eng_adviser': (
        'Engine Adviser',
        'Select it with  Engine -> Set Engine Adviser. How long it\n'
        'thinks (Movetime) is set in the same window.\n\n'
        'During a game (Play mode) right-click the Adviser label in the\n'
        'Engine panel and press Start to get a suggested move and score\n'
        'for the current position.'),
    'help_eng_analysis': (
        'Review Analysis Engine',
        'Select it with  Engine -> Set Engine Analysis.\n\n'
        'In Review mode press the Analysis button to evaluate the current\n'
        'position. Hash, Threads and the number of lines (MultiPV) are\n'
        'set in the Analysis panel. The search stops after the analysis\n'
        'time in Settings -> General (default 60s).'),
    'help_eng_threat': (
        'Review Threat Engine',
        'Select it with  Engine -> Set Engine Threat.\n\n'
        'In Review mode press the Threat button to see what the opponent\n'
        'would play if the side to move passed (null move). Unavailable\n'
        'while in check. Hash and Threads are set in the Threat panel.\n'
        'Time limit: Settings -> General (default 30s).'),
    'help_eng_depth': (
        'Search Depth',
        'Engine -> Set Depth caps the search depth of the playing and\n'
        'adviser engines. Pick "No limit" to remove the cap.\n'
        'Review analysis/threat are limited by time, not depth.'),
    'help_game_play': (
        'Play a Game',
        'Click the piece and its destination square (or drag it).\n'
        'Your first move starts the game and the clocks.\n\n'
        'Engine -> Move Now      the engine moves at once\n'
        'Game -> New             start a new game\n'
        'Game -> Resign, User Wins, User Draws   end the game\n\n'
        'The two dots beside the board show whose turn it is: the green\n'
        'one is the side to move. The Players panel shows the time left\n'
        'and the time spent on the current move.'),
    'help_game_black': (
        'Play as Black',
        'Press Engine -> Go before making a move: the engine takes\n'
        'White and moves first, and the board flips so Black is at\n'
        'the bottom. Game -> New returns you to White.'),
    'help_game_fen': (
        'Paste a FEN',
        'Game -> Paste FEN sets up a position from the clipboard (only\n'
        'before a game starts). If the side to move is not yours,\n'
        'press Engine -> Go.'),
    'help_game_assist': (
        'Adviser and Book Moves',
        'These help you during a game. Right-click the label:\n\n'
        'Adviser (Engine panel) -> Start: a suggested move and score\n'
        'from the adviser engine. Stop ends it.\n\n'
        'BOOK 1 / BOOK 2 (Opening books panel) -> Show: the opening\n'
        'book moves of the position, from computer games and from human\n'
        'games. Hide removes them.\n\n'
        'Opponent Search Info (Engine panel) -> Show / Hide: what the\n'
        'opponent engine thinks.'),
    'help_game_save': (
        'Save Games and Repertoire',
        'Every game auto-saves to pecg_auto_save_games.pgn.\n\n'
        'During a game Game -> Save also offers Save to My Games and\n'
        'Save to White / Black Repertoire.\n\n'
        'Open any of these files in Review mode to replay the games.'),
    'help_game_time': (
        'Time Control',
        'Settings -> Time -> User sets your clock; Settings -> Time ->\n'
        'Engine sets the opponent clock. Adjudication on flag-fall is\n'
        'toggled in Settings -> General.'),
    'help_settings': (
        'Settings',
        'The Settings menu is in Play mode, before a game starts.\n\n'
        'General:\n'
        '  Save time left in game notation   adds [%clk] comments\n'
        '  Adjudicate game on time forfeit   a flag-fall ends the game\n'
        '  Review analysis time (sec)        default 60\n'
        '  Review threat time (sec)          default 30\n'
        'Time -> User / Engine    the clock of each side\n'
        'Set Book                 the opponent book: use it or not, up\n'
        '                         to which ply, best or random move\n'
        'User Name                your name in the games\n'
        'PGN -> Delete Player     delete the games of a player from a\n'
        '                         PGN file\n\n'
        'Everything is saved and restored at the next start.'),
    'help_files': (
        'Files the App Writes',
        'All in the folder the app is started from:\n\n'
        'pecg_auto_save_games.pgn   every game played\n'
        'pecg_analyzed_games.pgn    games annotated by Auto-Analyze\n'
        'pecg_engines.json          installed engines and options\n'
        'pecg_settings.json         settings, engine jobs, layouts\n'
        'pecg_user.json             user names\n'
        'pecg_log.txt               log, new on every start; look here\n'
        '                           first when something goes wrong'),
    'help_review_open': (
        'Open a Game to Review',
        'Mode -> Review, then Game -> Select Game: choose a PGN file (or\n'
        'pick one from Recent), select a game and press OK or\n'
        'double-click it. The file is opened again the next time.\n\n'
        'The Game list panel shows the games of that file: click one to\n'
        'put it on the board, or use the Up / Down keys in the list.\n'
        'Click a column heading to sort. Analysis and Threat, if they\n'
        'are on, follow the board to the new game.'),
    'help_review_nav': (
        'Navigate Moves',
        'Use the arrow buttons under the board (first, previous, next,\n'
        'last; the fifth button flips the board),\n'
        'the Left / Right arrow keys (Home / End for first / last), or\n'
        'click a move in the move list to jump to that position.'),
    'help_review_engine': (
        'Analysis and Threat (Review)',
        'Analysis button (Alt+A): evaluate the position with the\n'
        'analysis engine.\n'
        'Threat button (Alt+T): show the opponent threat (null move).\n'
        'Both stop after their time limits in Settings -> General\n'
        '(analysis 60s, threat 30s) and restart automatically when you\n'
        'change move.\n\n'
        'Each box shows the search figures (depth, time, nodes, nodes\n'
        'per second), then the score and the line of moves. The score\n'
        'is for the side to move; #3 means that side mates in 3, -#3\n'
        'that it is mated in 3. For Threat the side to move is the\n'
        'opponent. The line is as long as the panel is wide: widen the\n'
        'panel to see more.\n\n'
        'Hash, Threads and MultiPV (number of lines) are set in the\n'
        'panel and saved; a running search restarts with the new value.'),
    'help_review_auto': (
        'Auto-Analyze Game',
        'Game -> Auto-Analyze Game annotates every move of the loaded\n'
        'game with the engine and time per move that you choose.\n\n'
        'Each move gets an evaluation comment, from the side that\n'
        'played it (positive is good for that side); bad moves are\n'
        'marked ?! ? ??.\n\n'
        'When the engine move is at least 25cp better (and its score\n'
        'stays within +/-300cp) the better line is replayed engine vs\n'
        'engine for up to 5 plies and added as a "Better is" variation\n'
        'scored at the end of the line.\n\n'
        'Results are appended to pecg_analyzed_games.pgn and the\n'
        'annotated game replaces the current review game. Use Game ->\n'
        'Cancel Analysis to stop early.'),
    'help_board_flip': (
        'Flip Board',
        'Board -> Flip swaps the side shown at the bottom. It works at\n'
        'any time: before, during and after a game, and in Review mode.\n'
        'The game itself is not affected.'),
    'help_board_size': (
        'Board Size',
        'Board -> Size picks a board size: Small (360), Medium (480),\n'
        'Large (600), X-Large (720), XX-Large (840) or Huge (960)\n'
        'pixels. On first start the largest board that fits the screen\n'
        'is chosen automatically, and the size is saved for the next\n'
        'session. The windows are also resizable: maximize or\n'
        'drag-resize them and the board switches to the largest of\n'
        'these sizes that fits, while the side panels absorb the\n'
        'leftover space. Like Flip, resizing works at any time.'),
    'help_board_layout': (
        'Panels and Layout',
        'The Play and Review windows are made of panels around the\n'
        'board.\n\n'
        'Move a panel: drag its title bar to the left of the board, to\n'
        'the right or below it (a green bar shows where it will land),\n'
        'or use View -> Move Panel. Under the board, drop it on the top\n'
        'or bottom edge of another panel to stack them, or on its middle\n'
        'to put them side by side.\n'
        'Resize: drag the divider between two panels, or between the\n'
        'board and the panels.\n'
        'View also has ready-made arrangements and Reset Layout.\n\n'
        'Each mode keeps its own arrangement; it is saved and restored\n'
        'at the next start.'),
    'help_board_color': (
        'Board Colors and Themes',
        'Board -> Color changes the square colors and Board -> Theme\n'
        'changes the overall GUI theme (before a game starts).'),
}

# The full manual: the project README (Help -> About shows this address).
ONLINE_HELP_URL = 'https://github.com/fsmosca/Python-Easy-Chess-GUI#readme'


# Help submenu fragments, one per subject; each mode's Help menu is made
# of the ones that apply to it. Note: a literal '&' marks a keyboard
# accelerator in menu labels, so plain words are used instead.
HELP_ENGINE_MENU = ['Engine', ['Install / Manage::help_eng_install',
                               'Engine for Each Job::help_eng_roles',
                               'Set Opponent::help_eng_opponent',
                               'Adviser::help_eng_adviser',
                               'Analysis::help_eng_analysis',
                               'Threat::help_eng_threat',
                               'Search Depth::help_eng_depth']]
HELP_GAME_MENU = ['Play', ['Play a Game::help_game_play',
                           'Play as Black::help_game_black',
                           'Paste FEN::help_game_fen',
                           'Adviser and Book Moves::help_game_assist',
                           'Save and Repertoire::help_game_save',
                           'Time Control::help_game_time']]
HELP_REVIEW_MENU = ['Review', ['Open a Game::help_review_open',
                               'Navigate Moves::help_review_nav',
                               'Analysis and Threat::help_review_engine',
                               'Auto-Analyze Game::help_review_auto']]
HELP_BOARD_MENU = ['Board and Layout', [
    'Flip::help_board_flip',
    'Size::help_board_size',
    'Panels and Layout::help_board_layout',
    'Colors and Themes::help_board_color']]


def make_help_menu(*sections):
    """Return a fresh Help menu definition for a mode.

    ``sections`` are submenu fragments of the form ``['Label', [items]]``.
    They are flattened into the parent so the label string and its item list
    become siblings (the format FreeSimpleGUI expects: a cascade is a string
    immediately followed by a list). A deep copy is returned so FreeSimpleGUI
    cannot mutate the shared fragment lists across the three menu definitions.
    """
    items = ['Getting Started::help_start',
             'Mouse and Keyboard::help_shortcuts', '---']
    for section in sections:
        items.extend(section)  # 'Label', [subitems] as two sibling elements
    items.extend(['---', 'Settings::help_settings',
                  'Files the App Writes::help_files'])
    # 'Online Help' is disabled (leading '!') so it shows but is not clickable.
    items.extend(['---', '!Online Help::help_online', 'About::help_about'])
    return ['&Help', copy.deepcopy(items)]


# Images/60
blank = os.path.join(IMAGE_PATH, 'blank.png')
bishopB = os.path.join(IMAGE_PATH, 'bB.png')
bishopW = os.path.join(IMAGE_PATH, 'wB.png')
pawnB = os.path.join(IMAGE_PATH, 'bP.png')
pawnW = os.path.join(IMAGE_PATH, 'wP.png')
knightB = os.path.join(IMAGE_PATH, 'bN.png')
knightW = os.path.join(IMAGE_PATH, 'wN.png')
rookB = os.path.join(IMAGE_PATH, 'bR.png')
rookW = os.path.join(IMAGE_PATH, 'wR.png')
queenB = os.path.join(IMAGE_PATH, 'bQ.png')
queenW = os.path.join(IMAGE_PATH, 'wQ.png')
kingB = os.path.join(IMAGE_PATH, 'bK.png')
kingW = os.path.join(IMAGE_PATH, 'wK.png')


images = {
    BISHOPB: bishopB, BISHOPW: bishopW, PAWNB: pawnB, PAWNW: pawnW,
    KNIGHTB: knightB, KNIGHTW: knightW, ROOKB: rookB, ROOKW: rookW,
    KINGB: kingB, KINGW: kingW, QUEENB: queenB, QUEENW: queenW, BLANK: blank
}


# Promote piece from psg (pysimplegui) to pyc (python-chess)
promote_psg_to_pyc = {
    KNIGHTB: chess.KNIGHT, BISHOPB: chess.BISHOP,
    ROOKB: chess.ROOK, QUEENB: chess.QUEEN,
    KNIGHTW: chess.KNIGHT, BISHOPW: chess.BISHOP,
    ROOKW: chess.ROOK, QUEENW: chess.QUEEN
}


INIT_PGN_TAG = {
    'Event': 'Human vs computer',
    'White': 'Human',
    'Black': 'Computer'
}


# (1) Mode: Play. The GUI opens directly in Play mode with a single menubar.
# Items that change the game/engine setup are usable only before a game
# starts (idle), while game actions need a started game. A leading '!'
# renders an item or submenu label disabled (grayed and unclickable).
def build_play_menu(in_game=False):
    """Return the Play-mode menubar definition for the given state.

    :param in_game: True once a game has started (first user move made or
        Engine->Go pressed) until it ends (game over or Game->New).
    """
    def g(enabled, label):
        return label if enabled else '!' + label

    idle = not in_game

    return [
        ['&Mode', [g(idle, 'Review')]],
        ['&Game', ['&New::new_game_k',
                   '---',
                   g(idle, 'Paste FEN'),
                   '---',
                   g(in_game, 'Resign::resign_game_k'),
                   g(in_game, 'User Wins::user_wins_k'),
                   g(in_game, 'User Draws::user_draws_k'),
                   '---',
                   g(in_game, 'Save'), ['Save to My Games::save_game_k',
                                        'Save to White Repertoire',
                                        'Save to Black Repertoire']]],
        ['&Engine', [g(idle, 'Go'), g(in_game, 'Move Now'),
                     '---',
                     g(idle, 'Set Engine Opponent'),
                     g(idle, 'Set Engine Adviser'),
                     g(idle, 'Set Engine Analysis'),
                     g(idle, 'Set Engine Threat'),
                     '---',
                     g(idle, 'Set Depth'),
                     g(idle, 'Manage'), ['Install', 'Edit', 'Delete']]],
        ['Boar&d', ['Flip',
                    'Size', ['{}::board_size_k'.format(label)
                             for label in BOARD_SIZE_LABELS],
                    g(idle, 'Color'), ['Brown::board_color_k',
                                       'Blue::board_color_k',
                                       'Green::board_color_k',
                                       'Gray::board_color_k'],
                    g(idle, 'Theme'), list(GUI_THEME)]],
        build_view_menu('play'),
        ['&Settings', [g(idle, 'General::settings_game_k'),
                       g(idle, 'Time'), [g(idle, 'User::tc_k'),
                                         g(idle, 'Engine::tc_k')],
                       g(idle, 'Set Book::book_set_k'),
                       g(idle, 'User Name::user_name_k'),
                       '---',
                       g(idle, 'PGN'), ['Delete Player::delete_player_k']]],
        make_help_menu(HELP_GAME_MENU, HELP_ENGINE_MENU,
                       HELP_REVIEW_MENU, HELP_BOARD_MENU),
    ]


# (2) Mode: Review. Mode->Play and Game->Auto-Analyze Game are disabled
# (leading '!') while an auto-analysis is running, since switching modes or
# starting a second analysis would race the background thread.
def build_review_menu(analyzing=False):
    """Return the Review-mode menubar definition for the given state.

    :param analyzing: True while an auto-analysis thread is running.
    """
    def g(enabled, label):
        return label if enabled else '!' + label

    idle = not analyzing

    return [
        ['&Mode', [g(idle, 'Play')]],
        ['&Game', ['Select Game::review_select_game_k',
                   g(idle, 'Auto-Analyze Game::review_auto_analyze_k'),
                   'Cancel Analysis::review_cancel_analysis_k']],
        ['Boar&d', ['Flip',
                    'Size', ['{}::board_size_k'.format(label)
                             for label in BOARD_SIZE_LABELS]]],
        build_view_menu('review'),
        make_help_menu(HELP_REVIEW_MENU, HELP_ENGINE_MENU, HELP_BOARD_MENU),
    ]


class Timer:
    def __init__(self, tc_type: str = 'fischer', base: int = 300000, inc: int = 10000, period_moves: int = 40) -> None:
        """Manages time control.

        Args:
          tc_type: time control type ['fischer, delay, classical']
          base: base time in ms
          inc: increment time in ms can be negative and 0
          period_moves: number of moves in a period
        """
        self.tc_type = tc_type  # ['fischer', 'delay', 'timepermove']
        self.base = base
        self.inc = inc
        self.period_moves = period_moves
        self.elapse = 0
        self.init_base_time = self.base
        # time.perf_counter() at the start of the turn being timed, or None
        # while this side's clock is not running.
        self._started_at = None

    def start(self) -> None:
        """Start timing the current turn; no effect if already running."""
        if self._started_at is None:
            self._started_at = time.perf_counter()

    def tick(self) -> int:
        """Set ``elapse`` to the real time (ms) since start() and return it.

        The clock follows real time, not the number of GUI loop passes, so
        it keeps running while a popup or another dialog has the focus.
        """
        if self._started_at is not None:
            self.elapse = int(
                (time.perf_counter() - self._started_at) * 1000)
        return self.elapse

    def update_base(self) -> None:
        """Updates base time after every move and stops the clock."""
        self.tick()
        self._started_at = None

        if self.tc_type == 'delay':
            self.base += min(0, self.inc - self.elapse)
        elif self.tc_type == 'fischer':
            self.base += self.inc - self.elapse
        elif self.tc_type == 'timepermove':
            self.base = self.init_base_time
        else:
            self.base -= self.elapse

        self.base = max(0, self.base)
        self.elapse = 0


class GuiBook:
    def __init__(self, book_file: str, board, is_random: bool = True) -> None:
        """Handles gui polyglot book for engine opponent.

        Args:
          book_file: polgylot book filename
          board: given board position
          is_random: randomly select move from book
        """
        self.book_file = book_file
        self.board = board
        self.is_random = is_random
        self.__book_move = None

    def get_book_move(self) -> None:
        """Gets book move either random or best move."""
        reader = chess.polyglot.open_reader(self.book_file)
        try:
            if self.is_random:
                entry = reader.weighted_choice(self.board)
            else:
                entry = reader.find(self.board)
            self.__book_move = entry.move
        except IndexError:
            logging.warning('No more book move.')
        except Exception:
            logging.exception('Failed to get book move.')
        finally:
            reader.close()

        return self.__book_move

    def get_all_moves(self):
        """
        Read polyglot book and get all legal moves from a given positions.

        :return: move string
        """
        is_found = False
        total_score = 0
        book_data = {}
        cnt = 0

        if os.path.isfile(self.book_file):
            moves = '{:4s}   {:<5s}   {}\n'.format('move', 'score', 'weight')
            with chess.polyglot.open_reader(self.book_file) as reader:
                for entry in reader.find_all(self.board):
                    is_found = True
                    san_move = self.board.san(entry.move)
                    score = entry.weight
                    total_score += score
                    bd = {cnt: {'move': san_move, 'score': score}}
                    book_data.update(bd)
                    cnt += 1
        else:
            moves = '{:4s}  {:<}\n'.format('move', 'score')

        # Get weight for each move
        if is_found:
            for _, v in book_data.items():
                move = v['move']
                score = v['score']
                weight = score/total_score
                moves += '{:4s}   {:<5d}   {:<2.1f}%\n'.format(move, score, 100*weight)

        return moves, is_found


class RunEngine(threading.Thread):
    pv_length = 9
    move_delay_sec = 3.0

    def __init__(self, eng_queue, engine_config_file, engine_path_and_file,
                 engine_id_name, max_depth=MAX_DEPTH,
                 base_ms=300000, inc_ms=1000, tc_type='fischer',
                 period_moves=0, is_stream_search_info=True,
                 existing_engine=None, multipv=1, option_overrides=None,
                 info_as_dict=False):
        """
        Run engine as opponent or as adviser.

        :param eng_queue:
        :param engine_config_file: pecg_engines.json
        :param engine_path_and_file:
        :param engine_id_name:
        :param max_depth:
        :param existing_engine: An existing chess.engine.SimpleEngine instance
            to reuse instead of spawning a new process.
        :param info_as_dict: post each line of streamed search info as a
            dict (see _run) instead of a formatted string, so the consumer
            formats the score and the whole variation itself.
        """
        threading.Thread.__init__(self)
        self._kill = threading.Event()
        self._analysis_ref = None  # Reference to running analysis context
        self._analysis_lock = threading.Lock()
        self.engine_config_file = engine_config_file
        self.engine_path_and_file = engine_path_and_file
        self.engine_id_name = engine_id_name
        self.own_book = False
        self.bm = None
        self.pv = None
        self.score = None
        self.depth = None
        self.time = None
        self.nps = 0
        self.max_depth = max_depth
        self.eng_queue = eng_queue
        self.engine = existing_engine
        self.board = None
        self.analysis = is_stream_search_info
        self.is_nomove_number_in_variation = True
        self.base_ms = base_ms
        self.inc_ms = inc_ms
        self.tc_type = tc_type
        self.period_moves = period_moves
        self.is_ownbook = False
        self.is_move_delay = True
        # Per-role UCI option overrides applied on top of the engine config.
        self.option_overrides = option_overrides or {}
        self.info_as_dict = info_as_dict
        try:
            self.multipv = max(1, int(multipv))
        except (TypeError, ValueError):
            self.multipv = 1

    def stop(self):
        """Interrupt engine search.

        Sets the kill flag and, if an analysis is in progress, sends
        the UCI ``stop`` command to the engine so that the iterator
        unblocks immediately instead of waiting for the next info line.
        """
        self._kill.set()
        with self._analysis_lock:
            if self._analysis_ref is not None:
                try:
                    self._analysis_ref.stop()
                except Exception:
                    logging.debug('Analysis ref stop failed (already finished).')

    def get_board(self, board):
        """Get the current board position."""
        self.board = board

    def configure_engine(self):
        """Configures the engine internal settings.
         
        Read the engine config file pecg_engines.json and set the engine to
        use the user_value of the value key. Our option name has 2 values,
        default_value and user_value.

        Example for hash option
        'name': Hash
        'default': default_value
        'value': user_value

        If default_value and user_value are not the same, we will set the
        engine to use the user_value by the command,
        setoption name Hash value user_value

        However if default_value and user_value are the same, we will not send
        commands to set the option value because the value is default already.
        """
        with open(self.engine_config_file, 'r') as json_file:
            data = json.load(json_file)
            managed_uci_options = {name.lower() for name in MANAGED_UCI_OPTIONS}
            for p in data:
                if p['name'] == self.engine_id_name:
                    for n in p['options']:
                        option_name = n['name'].lower()

                        if option_name == 'ownbook':
                            self.is_ownbook = True

                        # Analysis-managed options are applied at runtime.
                        if self.analysis and option_name in managed_uci_options:
                            continue

                        # Ignore button type for a moment.
                        if n['type'] == 'button':
                            continue

                        if n['type'] == 'spin':
                            user_value = int(n['value'])
                            default_value = int(n['default'])
                        else:
                            user_value = n['value']
                            default_value = n['default']

                        if user_value != default_value:
                            try:
                                self.engine.configure({n['name']: user_value})
                                logging.info('Set ' + n['name'] + ' to ' + str(user_value))
                            except Exception:
                                logging.exception('Failed to configure engine.')

    def configure_runtime_analysis_options(self):
        """Configure transient analysis-specific engine options."""
        if not self.analysis:
            return

        try:
            option_names = {name.lower(): name for name in self.engine.options}
        except Exception:
            logging.exception('Failed to read engine options.')
            return

        if 'uci_analysemode' in option_names:
            try:
                self.engine.configure({option_names['uci_analysemode']: True})
            except Exception:
                logging.exception('Failed to enable analyse mode.')

        # NOTE: MultiPV must NOT be set with engine.configure(). python-chess
        # treats it as an automatically-managed option (chess.engine.
        # MANAGED_OPTIONS) and raises EngineError "cannot set MultiPV which is
        # automatically managed". It is applied instead by passing
        # multipv=self.multipv to engine.analysis() in run().

    def apply_option_overrides(self):
        """Apply per-role UCI option overrides on top of the base config."""
        if not self.option_overrides:
            return
        try:
            option_names = {name.lower(): name for name in self.engine.options}
        except Exception:
            logging.exception('Failed to read engine options for overrides.')
            return
        managed = {m.lower() for m in chess.engine.MANAGED_OPTIONS}
        for name, value in self.option_overrides.items():
            lname = name.lower()
            if lname in managed or lname not in option_names:
                continue
            real = option_names[lname]
            try:
                opt = self.engine.options[real]
                if opt.type == 'spin':
                    value = int(value)
                elif opt.type == 'check':
                    value = value if isinstance(value, bool) else \
                        str(value).strip().lower() in ('true', '1', 'yes')
                self.engine.configure({real: value})
                logging.info('Override %s = %s', real, value)
            except Exception:
                logging.exception('Failed to apply override %s.', name)

    def run(self):
        """Thread entry: run the search and log an engine failure.

        An engine that dies or stops answering during its search raises
        here. The reason goes to the log file, so the user can see why the
        engine failed.
        """
        try:
            self._run()
        except Exception:
            logging.exception('Engine %s (%s) failed during its search.',
                              self.engine_id_name, self.engine_path_and_file)

    def _run(self):
        """Run engine to get search info and bestmove.
         
        If there is error we still send bestmove None.
        """
        # Reuse existing engine if provided
        if self.engine is None:
            folder = Path(self.engine_path_and_file)
            folder = folder.parents[0]

            try:
                if sys_os == 'Windows':
                    self.engine = chess.engine.SimpleEngine.popen_uci(
                        self.engine_path_and_file, cwd=folder,
                        creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    self.engine = chess.engine.SimpleEngine.popen_uci(
                        self.engine_path_and_file, cwd=folder)
            except chess.engine.EngineTerminatedError:
                logging.warning('Failed to start {}.'.format(self.engine_path_and_file))
                self.eng_queue.put('bestmove {}'.format(self.bm))
                return
            except Exception:
                logging.exception('Failed to start {}.'.format(
                    self.engine_path_and_file))
                self.eng_queue.put('bestmove {}'.format(self.bm))
                return

            # Set engine option values
            try:
                self.configure_engine()
            except Exception:
                logging.exception('Failed to configure engine.')

        try:
            self.configure_runtime_analysis_options()
        except Exception:
            logging.exception('Failed to configure runtime analysis options.')

        try:
            self.apply_option_overrides()
        except Exception:
            logging.exception('Failed to apply option overrides.')

        # Set search limits.
        # For infinite analysis pass limit=None so that python-chess sends
        # "go infinite" to the engine (Limit() is truthy and would produce
        # a bare "go" without the infinite token).
        if self.tc_type == 'infinite':
            limit = (chess.engine.Limit(depth=self.max_depth)
                     if self.max_depth != MAX_DEPTH else None)
        elif self.tc_type == 'delay':
            limit = chess.engine.Limit(
                depth=self.max_depth if self.max_depth != MAX_DEPTH else None,
                white_clock=self.base_ms/1000,
                black_clock=self.base_ms/1000,
                white_inc=self.inc_ms/1000,
                black_inc=self.inc_ms/1000)
        elif self.tc_type == 'timepermove':
            limit = chess.engine.Limit(time=self.base_ms/1000,
                                       depth=self.max_depth if
                                       self.max_depth != MAX_DEPTH else None)
        else:
            limit = chess.engine.Limit(
                depth=self.max_depth if self.max_depth != MAX_DEPTH else None,
                white_clock=self.base_ms/1000,
                black_clock=self.base_ms/1000,
                white_inc=self.inc_ms/1000,
                black_inc=self.inc_ms/1000)
        start_time = time.perf_counter()
        if self.analysis:
            is_time_check = False

            with self.engine.analysis(self.board, limit, multipv=self.multipv) as analysis:
                with self._analysis_lock:
                    self._analysis_ref = analysis
                # Check kill flag after storing the reference in case
                # stop() was called between thread start and here.
                if not self._kill.is_set():
                    for info in analysis:

                        if self._kill.is_set():
                            break

                        try:
                            line_number = int(info.get('multipv', 1))
                            depth = int(info['depth']) if 'depth' in info else self.depth
                            score = self.score
                            if 'score' in info:
                                score = int(
                                    info['score'].relative.score(mate_score=32000)
                                ) / 100
                            elapsed = info['time'] if 'time' in info else \
                                time.perf_counter() - start_time
                            pv = None

                            if 'pv' in info and not ('upperbound' in info or
                                                     'lowerbound' in info):
                                self.pv = info['pv'][0:self.pv_length]

                                if self.is_nomove_number_in_variation:
                                    pv = self.short_variation_san()
                                else:
                                    pv = self.board.variation_san(self.pv)

                                if line_number == 1:
                                    self.bm = info['pv'][0]

                            if line_number == 1 and depth is not None:
                                self.depth = depth
                            if line_number == 1 and score is not None:
                                self.score = score
                            if line_number == 1:
                                self.time = elapsed
                                if pv is not None:
                                    self.pv = pv

                            if self.info_as_dict:
                                # The variation in full and the score as
                                # the engine gave it, with the board they
                                # belong to.
                                if pv is not None and 'score' in info:
                                    self.eng_queue.put({
                                        'board': self.board,
                                        'multipv': line_number,
                                        'score': info['score'],
                                        'pv': list(info['pv']),
                                        'depth': depth,
                                        'seldepth': info.get('seldepth'),
                                        'time': elapsed,
                                        'nodes': info.get('nodes'),
                                        'nps': info.get('nps')})
                            elif score is not None and pv is not None and depth is not None:
                                if self.multipv > 1:
                                    info_to_send = \
                                        '{} | {:+5.2f} | {} | {:0.1f}s | {} multipv_info'.format(
                                            line_number, score, depth, elapsed, pv)
                                else:
                                    info_to_send = \
                                        '{:+5.2f} | {} | {:0.1f}s | {} info_all'.format(
                                            score, depth, elapsed, pv)
                                self.eng_queue.put('{}'.format(info_to_send))

                            # Send stop if movetime is exceeded
                            if not is_time_check \
                                    and self.tc_type not in ('fischer', 'delay', 'infinite') \
                                    and time.perf_counter() - start_time >= \
                                    self.base_ms/1000:
                                logging.info('Max time limit is reached.')
                                is_time_check = True
                                break

                            # Send stop if max depth is exceeded
                            if 'depth' in info:
                                if int(info['depth']) >= self.max_depth \
                                        and self.max_depth != MAX_DEPTH:
                                    logging.info('Max depth limit is reached.')
                                    break
                        except Exception:
                            logging.exception('Failed to parse search info.')
                with self._analysis_lock:
                    self._analysis_ref = None
        else:
            result = self.engine.play(self.board, limit, info=chess.engine.INFO_ALL)
            logging.info('result: {}'.format(result))
            try:
                self.depth = result.info['depth']
            except KeyError:
                self.depth = 1
                logging.exception('depth is missing.')
            try:
                self.score = int(result.info['score'].relative.score(
                    mate_score=32000)) / 100
            except KeyError:
                self.score = 0
                logging.exception('score is missing.')
            try:
                self.time = result.info['time'] if 'time' in result.info \
                    else time.perf_counter() - start_time
            except KeyError:
                self.time = 0
                logging.exception('time is missing.')
            try:
                if 'pv' in result.info:
                    self.pv = result.info['pv'][0:self.pv_length]

                if self.is_nomove_number_in_variation:
                    spv = self.short_variation_san()
                    self.pv = spv
                else:
                    self.pv = self.board.variation_san(self.pv)
            except Exception:
                self.pv = None
                logging.exception('pv is missing.')

            if self.pv is not None:
                info_to_send = '{:+5.2f} | {} | {:0.1f}s | {} info_all'.format(
                    self.score, self.depth, self.time, self.pv)
                self.eng_queue.put('{}'.format(info_to_send))
            self.bm = result.move

        # Apply engine move delay if movetime is small
        if self.is_move_delay:
            while True:
                if (self._kill.is_set()
                        or time.perf_counter() - start_time
                        >= self.move_delay_sec):
                    break
                logging.info('Delay sending of best move {}'.format(self.bm))
                time.sleep(1.0)

        # If bm is None, we will use engine.play()
        # Skip this fallback when the search was explicitly interrupted
        # to avoid blocking the thread with an unconstrained engine call.
        # Also skip when limit is None (infinite analysis) since
        # engine.play() requires a concrete Limit object.
        if self.bm is None and not self._kill.is_set() and limit is not None:
            logging.info('bm is none, we will try engine,play().')
            try:
                result = self.engine.play(self.board, limit)
                self.bm = result.move
            except Exception:
                logging.exception('Failed to get engine bestmove.')
        self.eng_queue.put(f'bestmove {self.bm}')
        logging.info(f'bestmove {self.bm}')

    def quit_engine(self):
        """Quit engine.

        Safe to call multiple times; subsequent calls are no-ops.
        """
        if self.engine is None:
            return
        logging.info('quit engine')
        try:
            self.engine.quit()
        except Exception:
            logging.exception('Failed to quit engine.')
        self.engine = None

    def get_engine(self):
        """Return the engine instance without quitting it.

        This allows the engine process to be reused across moves.
        """
        return self.engine

    def short_variation_san(self):
        """Returns variation in san but without move numbers."""
        if self.pv is None:
            return None

        short_san_pv = []
        tmp_board = self.board.copy()
        for pc_move in self.pv:
            san_move = tmp_board.san(pc_move)
            short_san_pv.append(san_move)
            tmp_board.push(pc_move)

        return ' '.join(short_san_pv)


class AutoAnalyzeGame(threading.Thread):
    """Background thread that annotates a game with engine analysis.

    Walks the mainline of the supplied game, evaluating each position with
    the engine. Each played move gets a comment with its evaluation
    (from the side that played it). Bad moves get ?!/?/?? NAGs. When the engine's move beats
    the game move by at least AUTO_ANALYSIS_ALT_MIN_CP and its own score is
    within AUTO_ANALYSIS_BETTER_MAX_ABS_CP of equal, the better line is not
    taken from the search PV (which can be a single move) but replayed engine
    vs engine (at MultiPV 1) for up to self.replay_plies plies and added as a
    sub-variation whose comment carries the score after the line's last move.
    When that final line score beats the game move by at least
    AUTO_ANALYSIS_BETTER_MIN_CP the variation earns the "Better is"
    pre-comment; a smaller gap is written as a bare line. Praise NAGs !/!! and
    Alt: lines need a MultiPV >= 2 search, controlled by self.multipv.
    """

    def __init__(self, game, engine_config_file, engine_path_and_file,
                 engine_id_name, time_sec, output_queue, cancel_event,
                 max_depth=MAX_DEPTH, option_overrides=None,
                 output_file=AUTO_ANALYSIS_OUTPUT_FILE,
                 multipv=AUTO_ANALYSIS_MULTIPV,
                 replay_plies=AUTO_ANALYSIS_REPLAY_PLIES):
        threading.Thread.__init__(self)
        self.game = game
        self.engine_config_file = engine_config_file
        self.engine_path_and_file = engine_path_and_file
        self.engine_id_name = engine_id_name
        self.time_sec = time_sec
        self.output_queue = output_queue
        self.cancel_event = cancel_event
        self.max_depth = max_depth
        self.option_overrides = option_overrides or {}
        self.output_file = output_file
        try:
            self.multipv = max(1, min(AUTO_ANALYSIS_MULTIPV_MAX, int(multipv)))
        except (TypeError, ValueError):
            self.multipv = AUTO_ANALYSIS_MULTIPV
        try:
            self.replay_plies = max(AUTO_ANALYSIS_REPLAY_PLIES_MIN,
                                    min(AUTO_ANALYSIS_REPLAY_PLIES_MAX,
                                        int(replay_plies)))
        except (TypeError, ValueError):
            self.replay_plies = AUTO_ANALYSIS_REPLAY_PLIES
        self.engine = None
        self.daemon = True

    def _format_score(self, score, mover):
        """Return a human-readable score string from the point of view of
        ``mover``: the side to move in the position being annotated, the
        one whose move the score is written on.

        Pawns are positive when that side is better. A mate reads "Mate
        in n" when that side forces it and "Mated in n" when it is the
        one being mated.
        """
        own = score.pov(mover)
        if own.is_mate():
            mate = own.mate()
            return 'Mate in {}'.format(mate) if mate > 0 \
                else 'Mated in {}'.format(abs(mate))
        return '{:+.2f}'.format(own.score() / 100.0)

    def _replay_variation(self, board, first_move, limit):
        """Rebuild an engine line by playing the engine against itself.

        A search PV is sometimes truncated to a single move, so instead of
        trusting it the line is replayed move by move (engine vs engine)
        for up to self.replay_plies plies, starting from board with
        first_move. Each replay search uses MultiPV 1 (best line only),
        independent of the per-move MultiPV used for the main analysis.
        Returns (moves, score) where score is the engine evaluation of the
        position after the line's last move (a PovScore of the side to move
        there; None if the engine reported none). A line that reaches a
        finished game stops there and keeps the last search score - for a
        mate that reads 'Mate in N', which is the clearer label anyway.
        """
        var_board = board.copy()
        var_board.push(first_move)
        moves = [first_move]
        score = None
        while not self.cancel_event.is_set():
            if var_board.is_game_over():
                break
            info = self.engine.analyse(var_board, limit, multipv=1)
            if isinstance(info, list):
                info = info[0]
            if info.get('score') is not None:
                score = info['score']
            if len(moves) >= self.replay_plies:
                break
            pv = info.get('pv') or []
            if not pv or pv[0] not in var_board.legal_moves:
                break
            var_board.push(pv[0])
            moves.append(pv[0])
        return moves, score

    def _build_engine_variation(self, node, moves, board, score,
                                label_better=True):
        """Add a replayed engine line as a variation on node.

        With label_better, reads e.g. "({Better is} 9...Qe6 {+1.53} 10. Re1)":
        a "Better is" pre-comment on the first variation move, followed by the
        engine's evaluation of the position the replayed line ended on. Without
        it the line is written bare - "(9...Qe6 {+1.53} 10. Re1)" - for a
        smaller edge over the game move. That evaluation is from the side
        to move on ``board`` (the one the line is for), like the comment
        of the game move it is compared with.
        """
        if not moves or moves[0] not in board.legal_moves:
            return
        score_text = self._format_score(score, board.turn) \
            if score is not None else ''
        starting_comment = 'Better is' if label_better else ''
        var_board = board.copy()
        var_node = node.add_variation(
            moves[0], starting_comment=starting_comment, comment=score_text)
        var_board.push(moves[0])
        for move in moves[1:]:
            if move not in var_board.legal_moves:
                break
            var_node = var_node.add_variation(move)
            var_board.push(move)

    def _build_move_comment(self, game_move_score, delta_cp, is_only_move,
                            allows_mate):
        """Return the annotation comment for a played move.

        Base is the score text from the mover's POV: pawns positive when
        the mover is better, 'Mate in n' when the game move wins with
        mate, 'Mated in n' when the mover is the one getting mated. The
        caller passes game_move_score anchored to the mover (its turn)
        for this reason. A move that walks into a forced mate
        while a better move existed is marked 'allows mate'; a move that
        earned a praise NAG is marked as the only good move (same criterion
        as the NAG, so text and glyph never disagree). The better move and
        its price are not spelled out here - the replayed variation carries
        them. Kept brace-free: PGN comments cannot contain '{' or '}'.
        """
        text = self._format_score(game_move_score, game_move_score.turn)
        if delta_cp is not None and delta_cp >= 30 and allows_mate:
            text += ', allows mate'
        elif is_only_move:
            text += ', only good move'
        return text

    def _classify_good_nag(self, engine_cp, second_cp, best_score,
                           second_score):
        """Return a praise NAG when the played best move stands out.

        Both centipawn values are from the mover's POV, taken from the same
        pre-move MultiPV search. Positions with a single reply return one
        line (second_cp is None), so forced moves never earn praise; and no
        praise is given when even the second-best line keeps a clear
        advantage (finding a move among many good ones is routine).
        """
        if second_cp is None or second_cp > 100:
            return None
        best_is_mate = (best_score is not None
                        and best_score.relative.is_mate()
                        and best_score.relative.mate() > 0)
        second_is_mate = (second_score is not None
                          and second_score.relative.is_mate()
                          and second_score.relative.mate() > 0)
        gap = engine_cp - second_cp
        if gap >= 400 or (best_is_mate and not second_is_mate):
            return 3   # !! the move wins where everything else fails
        if gap >= 150:
            return 1   # ! the only move that keeps the position
        return None

    def _configure_engine(self):
        """Apply UCI options from the engine config and per-role overrides."""
        with open(self.engine_config_file, 'r') as json_file:
            data = json.load(json_file)
            for p in data:
                if p['name'] != self.engine_id_name:
                    continue
                for n in p['options']:
                    if n['type'] == 'button':
                        continue
                    if n['type'] == 'spin':
                        user_value = int(n['value'])
                        default_value = int(n['default'])
                    else:
                        user_value = n['value']
                        default_value = n['default']
                    if user_value != default_value:
                        try:
                            self.engine.configure({n['name']: user_value})
                        except Exception:
                            logging.exception('Failed to configure engine option.')

        managed = {m.lower() for m in chess.engine.MANAGED_OPTIONS}
        option_names = {name.lower(): name for name in self.engine.options}
        for name, value in self.option_overrides.items():
            lname = name.lower()
            if lname in managed or lname not in option_names:
                continue
            real = option_names[lname]
            try:
                opt = self.engine.options[real]
                if opt.type == 'spin':
                    value = int(value)
                elif opt.type == 'check':
                    value = value if isinstance(value, bool) else \
                        str(value).strip().lower() in ('true', '1', 'yes')
                self.engine.configure({real: value})
            except Exception:
                logging.exception('Failed to apply override %s.', name)

    def _configure_runtime_analysis_options(self):
        """Enable analysis-specific UCI options (e.g. UCI_AnalyseMode)."""
        try:
            option_names = {name.lower(): name for name in self.engine.options}
        except Exception:
            logging.exception('Failed to read engine options.')
            return
        if 'uci_analysemode' in option_names:
            try:
                self.engine.configure({option_names['uci_analysemode']: True})
            except Exception:
                logging.exception('Failed to enable analyse mode.')

    def _centipawns(self, score):
        """Return the evaluation in centipawns from the side-to-move POV."""
        return score.relative.score(mate_score=32000)

    def _classify_nag(self, engine_cp, game_move_cp):
        """Return a NAG integer if the game move is much worse than best.

        Both scores are from the POV of the player who made the game move.
        """
        if game_move_cp <= -500 and engine_cp >= -200:
            return 4   # ?? blunder
        if game_move_cp <= -300 and engine_cp > -300:
            return 2   # ? mistake
        if game_move_cp <= -100 and engine_cp > -100:
            return 6   # ?! dubious
        return None

    def _clear_existing_annotations(self):
        """Strip comments, NAGs and non-mainline variations from the game.

        Re-analysis starts from a clean slate instead of piling new scores
        and engine lines on top of old annotations.
        """
        node = self.game
        while node.variations:
            child = node.variations[0]
            # Keep only the mainline child; drop sibling variations.
            for var in list(node.variations[1:]):
                try:
                    node.remove_variation(var)
                except Exception:
                    logging.exception('Failed to remove existing variation.')
            # Wipe annotations on the mainline child.
            child.comment = ''
            child.starting_comment = ''
            child.nags = set()
            node = child

    def run(self):
        """Analyze the game and emit progress/done messages."""
        try:
            folder = Path(self.engine_path_and_file).parents[0]
            if sys_os == 'Windows':
                self.engine = chess.engine.SimpleEngine.popen_uci(
                    self.engine_path_and_file, cwd=folder,
                    creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                self.engine = chess.engine.SimpleEngine.popen_uci(
                    self.engine_path_and_file, cwd=folder)
            self._configure_engine()
            self._configure_runtime_analysis_options()
            self._clear_existing_annotations()

            # Count mainline moves for progress reporting.
            total = 0
            node = self.game
            while node.variations:
                total += 1
                node = node.variations[0]

            current = 0
            node = self.game
            board = self.game.board()
            while node.variations:
                if self.cancel_event.is_set():
                    self.output_queue.put({'type': 'cancelled'})
                    return

                current += 1
                child = node.variations[0]
                limit = chess.engine.Limit(
                    time=self.time_sec,
                    depth=self.max_depth if self.max_depth != MAX_DEPTH else None)
                infos = self.engine.analyse(board, limit, multipv=self.multipv)
                if not isinstance(infos, list):
                    infos = [infos]

                info = infos[0]
                score = info.get('score')
                pv = info.get('pv', [])
                best_move = pv[0] if pv else None
                engine_cp = self._centipawns(score) if score is not None else None
                is_best = best_move is not None and best_move == child.move

                second_info = infos[1] if len(infos) > 1 else None
                second_score = second_info.get('score') if second_info else None
                second_cp = self._centipawns(second_score) \
                    if second_score is not None else None

                # Evaluation of the move actually played, always anchored to
                # the mover's POV so the comment's mate wording reads from
                # the side that played the move ('Mate in n' when the game
                # move wins with mate, 'Mated in n' when it runs into one).
                # If the move appears in one of the MultiPV lines its
                # pre-move score is reused (already mover POV, no extra
                # search); only a move outside the top lines needs a search
                # of the position after it, whose opponent-POV score is
                # re-anchored back to the mover.
                game_move_score = None
                game_move_cp = None
                if score is not None:
                    played_info = next(
                        (i for i in infos
                         if i.get('pv') and i['pv'][0] == child.move), None)
                    if played_info is not None:
                        game_move_score = played_info.get('score')
                        if game_move_score is not None:
                            game_move_cp = self._centipawns(game_move_score)
                    else:
                        after_board = board.copy()
                        after_board.push(child.move)
                        after_infos = self.engine.analyse(
                            after_board, limit, multipv=1)
                        after_info = after_infos[0] if isinstance(
                            after_infos, list) else after_infos
                        after_score = after_info.get('score')
                        if after_score is not None:
                            game_move_score = chess.engine.PovScore(
                                after_score.pov(board.turn), board.turn)
                            game_move_cp = self._centipawns(game_move_score)

                # How much the played move lost vs the engine's best
                # (mover POV).
                delta_cp = None
                if engine_cp is not None and game_move_cp is not None:
                    delta_cp = engine_cp - game_move_cp

                # Rebuild the engine's better line by replaying it engine
                # vs engine. The root gap (engine best vs game move) at least
                # ALT_MIN_CP, plus a not-yet-decided position, is the cheap
                # gate for replaying at all. The "Better is" label is then
                # decided by the replayed line's final score - the eval shown
                # on the variation - vs the game move (both mover POV): a gap
                # of at least BETTER_MIN_CP earns the pre-comment, a smaller
                # gap is written as a bare line.
                var_moves = None
                var_score = None
                label_better = False
                if (not is_best and best_move is not None
                        and delta_cp is not None
                        and delta_cp >= AUTO_ANALYSIS_ALT_MIN_CP
                        and engine_cp is not None
                        and abs(engine_cp) <= AUTO_ANALYSIS_BETTER_MAX_ABS_CP):
                    var_moves, var_score = self._replay_variation(
                        board, best_move, limit)
                    if var_score is None:
                        var_score = score
                    var_cp = var_score.pov(board.turn).score(mate_score=32000)
                    label_better = (var_cp - game_move_cp
                                    >= AUTO_ANALYSIS_BETTER_MIN_CP)

                if game_move_score is not None:
                    nag = None
                    if engine_cp is not None and game_move_cp is not None:
                        if is_best:
                            nag = self._classify_good_nag(
                                engine_cp, second_cp, score, second_score)
                        else:
                            nag = self._classify_nag(engine_cp, game_move_cp)
                        if nag is not None:
                            child.nags.add(nag)

                    allows_mate = (game_move_cp is not None
                                   and game_move_cp <= -31000)
                    child.comment = self._build_move_comment(
                        game_move_score, None if is_best else delta_cp,
                        nag in (1, 3), allows_mate)

                if var_moves:
                    self._build_engine_variation(
                        node, var_moves, board, var_score, label_better)

                self.output_queue.put({
                    'type': 'progress',
                    'current': current,
                    'total': total,
                })

                board.push(child.move)
                node = child

            ms_per_move = int(round(self.time_sec * 1000))
            self.game.headers['Annotator'] = '{} ({}ms/move)'.format(
                self.engine_id_name, ms_per_move)
            with open(self.output_file, mode='a+', encoding='utf-8') as f:
                f.write('\n{}\n\n'.format(self.game))

            self.output_queue.put({'type': 'done', 'game': self.game})
        except Exception:
            logging.exception('Auto-analysis failed.')
            self.output_queue.put({
                'type': 'error',
                'message': 'Auto-analysis failed. Check the log for details.'})
        finally:
            if self.engine is not None:
                try:
                    self.engine.quit()
                except Exception:
                    logging.exception('Failed to quit auto-analysis engine.')


class PanelLayout:
    """Places a window's panels around the board, with draggable dividers.

    The board box and every panel are ordinary FreeSimpleGUI columns, all
    built in one layout row so their Tk frames share one parent. After the
    window is finalized this class takes their placement over with Tk
    PanedWindow widgets: a horizontal one holding [left zone | board |
    right zone], a vertical one per side zone stacking that zone's panels,
    and a bottom zone under the board. The bottom zone is made of rows,
    one under the other, each holding one or more panels side by side
    (``bottom_rows`` is the number of panels in each row).

    Panels are resized by dragging a divider and moved by dragging their
    title bar onto another zone (or by calling arrange()), all in the live
    window without rebuilding it.

    The layout owns the sizes: the board box does not follow the size of
    the board canvas. ``on_resize(room)`` is called when the room for the
    board may have changed, so the owner can choose a board size with
    board_space() and set_board_box(): ``room`` is None when the window
    was resized, or the (width, height) a divider next to the board left
    for it when the user let go of that divider (with ``grow_only`` True
    if that should only ever make the board larger).
    ``on_change()`` is called after the user moved a panel or a divider,
    so the owner can save state().

    Heights with panels under the board: the board box is as tall as the
    board and the bottom zone takes the rest of the window. Dragging the
    divider between them gives the bottom zone the height it is dragged
    to; see _bottom_dragged().

    The board box may hold something of a fixed height under the board
    (the navigation bar of the Review window). ``board_extra_px`` is that
    height: the box is always that much taller than the board, and the
    bottom zone comes under it.
    """

    ZONES = ('left', 'right', 'bottom')
    SASH_PX = 6
    DEFAULT_ZONE_PX = 380      # width of a side zone until it is resized
    BOTTOM_MIN_PX = 60         # least height of the zone under the board
    DRAG_START_PX = 8          # pointer travel before a title-bar drag starts

    def __init__(self, window, board_key, panel_keys, on_resize, on_change,
                 stretch_panels=(), divider_color='#c8ccd2',
                 marker_color='#2e9e3f', min_zone_px=300, board_extra_px=0):
        self.window = window
        self.root = window.TKroot
        self.board_box = window[board_key].Widget
        self.row = self.board_box.master      # Tk frame of the layout row
        self.panel_keys = list(panel_keys)
        self.on_resize = on_resize
        self.on_change = on_change
        self.stretch_panels = set(stretch_panels)
        self.min_zone_px = min_zone_px
        self.extra_px = board_extra_px        # in the box, under the board
        self.arrangement = {zone: [] for zone in self.ZONES}
        self.bottom_rows = []                 # panels per row under the board
        self._row_paned = []                  # a paned window per such row
        self._arranged = False
        self._resize_after_id = None
        self._drag = None                     # state of a title-bar drag
        # Set by dragging the divider under the board: the height the
        # user gave the bottom zone (None: what its panels need) and,
        # where the window could not follow, the height that left for the
        # board box (None: just what it holds). Both only apply while
        # the window is maximized, or not, as it was at the time.
        self.bottom_px = None
        self.box_px = None
        self.bottom_maximized = False
        self._board_size = (0, 0)             # as given to set_board_box()
        self._bottom_press = None             # heights when a drag began

        options = dict(sashwidth=self.SASH_PX, sashpad=0, sashrelief='flat',
                       bd=0, opaqueresize=True, background=divider_color)
        self._paned_options = options
        self.main = tk.PanedWindow(self.row, orient='horizontal', **options)
        self.centre = tk.PanedWindow(self.row, orient='vertical', **options)
        # The divider under the board resizes the window rather than the
        # board, so while it is dragged only a line follows the pointer.
        try:
            self.centre.configure(opaqueresize=False,
                                  proxybackground=marker_color,
                                  proxyborderwidth=0)
        except tk.TclError:
            pass    # older Tk without a styled drag line: resize live
        self.zone = {
            'left': tk.PanedWindow(self.row, orient='vertical', **options),
            'right': tk.PanedWindow(self.row, orient='vertical', **options),
            # The rows under the board, each a paned window of its own.
            'bottom': tk.PanedWindow(self.row, orient='vertical',
                                     **options),
        }
        # Shows where a dragged panel would land.
        self.drop_marker = tk.Frame(self.row, background=marker_color)

        # The board box keeps the size it is given instead of shrinking
        # or growing with the canvas inside it.
        self.board_box.pack_propagate(False)
        self.main.bind('<Configure>', self._main_resized, add='+')
        self.main.bind('<ButtonRelease-1>',
                       lambda e: self._divider_released(True), add='+')
        self.centre.bind('<ButtonPress-1>', self._bottom_pressed, add='+')
        self.centre.bind('<ButtonRelease-1>',
                         lambda e: self.root.after(1, self._bottom_dragged),
                         add='+')
        for paned in self.zone.values():
            paned.bind('<ButtonRelease-1>',
                       lambda e: self._divider_released(False), add='+')

        # A panel is moved by dragging its title bar.
        for key in self.panel_keys:
            title = window[key + '_title'].Widget
            title.configure(cursor='fleur')
            title.bind('<ButtonPress-1>',
                       lambda e, k=key: self._drag_press(e, k), add='+')
            title.bind('<B1-Motion>', self._drag_motion, add='+')
            title.bind('<ButtonRelease-1>', self._drag_release, add='+')

        # Let the row holding everything follow the window size.
        self.row.pack_configure(fill='both', expand=True)

    # ----- arrangement -----------------------------------------------------
    def clean(self, arrangement):
        """Return arrangement with every panel exactly once: unknown names
        are dropped and missing panels are added to the right zone, above
        the panels there that come after them in the default order (so a
        panel that is new in this version shows up in its usual place in
        a layout saved by an older one)."""
        result = {zone: [] for zone in self.ZONES}
        seen = set()
        if isinstance(arrangement, dict):
            for zone in self.ZONES:
                keys = arrangement.get(zone, [])
                for key in keys if isinstance(keys, list) else []:
                    if key in self.panel_keys and key not in seen:
                        result[zone].append(key)
                        seen.add(key)
        order = self.panel_keys.index
        for key in self.panel_keys:
            if key not in seen:
                right = result['right']
                later = [i for i, k in enumerate(right)
                         if order(k) > order(key)]
                right.insert(later[0] if later else len(right), key)
        return result

    @staticmethod
    def clean_rows(arrangement, count):
        """Return the number of panels in each row under the board for
        ``count`` panels there: arrangement['bottom_rows'] if it fits,
        otherwise one panel per row."""
        rows = arrangement.get('bottom_rows') \
            if isinstance(arrangement, dict) else None
        if isinstance(rows, list) and sum(
                n for n in rows if isinstance(n, int)
                and not isinstance(n, bool) and n > 0) == count \
                and all(isinstance(n, int) and not isinstance(n, bool)
                        and n > 0 for n in rows):
            return list(rows)
        return [1] * count

    @staticmethod
    def _split_rows(keys, rows):
        """The panels under the board as a list of rows."""
        result, start = [], 0
        for count in rows:
            result.append(list(keys[start:start + count]))
            start += count
        return result

    def bottom_row_lists(self):
        """The panels under the board, row by row from the top."""
        return self._split_rows(self.arrangement['bottom'], self.bottom_rows)

    def _bottom_row_paned(self, index):
        """The paned window of a row under the board (made when needed)."""
        while len(self._row_paned) <= index:
            paned = tk.PanedWindow(self.row, orient='horizontal',
                                   **self._paned_options)
            paned.bind('<ButtonRelease-1>',
                       lambda e: self._divider_released(False), add='+')
            self._row_paned.append(paned)
        return self._row_paned[index]

    def sizes(self):
        """Current sizes in px: {'zones': {zone: width, or height for the
        bottom zone}, 'panels': {key: height, or width in the bottom zone},
        'rows': [height of each row under the board]}.
        """
        zones, panels = {}, {}
        for zone in self.ZONES:
            if not self.arrangement[zone]:
                continue
            across = zone == 'bottom'
            paned = self.zone[zone]
            zones[zone] = paned.winfo_height() if across \
                else paned.winfo_width()
            for key in self.arrangement[zone]:
                widget = self.window[key].Widget
                panels[key] = widget.winfo_width() if across \
                    else widget.winfo_height()
        rows = [self._row_paned[i].winfo_height()
                for i in range(len(self.bottom_rows))]
        return {'zones': zones, 'panels': panels, 'rows': rows}

    def is_maximized(self):
        """True if the window is maximized ('zoomed' on Windows and some
        window managers, the '-zoomed' attribute elsewhere on Linux)."""
        try:
            if self.root.state() == 'zoomed':
                return True
        except tk.TclError:
            pass
        try:
            return bool(self.root.wm_attributes('-zoomed'))
        except tk.TclError:
            return False

    def can_size_window(self):
        """True if the window is one whose size we may set."""
        try:
            return self.root.state() == 'normal' and not self.is_maximized()
        except tk.TclError:
            return False

    def state(self):
        """Everything needed to restore the layout later (JSON-friendly)."""
        result = {'arrangement': {z: list(k) for z, k in
                                  self.arrangement.items()}}
        result['arrangement']['bottom_rows'] = list(self.bottom_rows)
        result.update(self.sizes())
        result['bottom_px'] = self.bottom_px
        result['board_box_px'] = self.box_px
        result['bottom_maximized'] = self.bottom_maximized
        try:
            result['maximized'] = self.is_maximized()
            if not result['maximized']:
                result['window'] = [self.root.winfo_width(),
                                    self.root.winfo_height()]
        except tk.TclError:
            pass
        return result

    def arrange(self, arrangement, sizes=None, natural=False):
        """Place the panels: {'left': [keys], 'right': [...], 'bottom': [...]}.

        The panels under the board come one per row, unless the
        arrangement also has 'bottom_rows': the number of panels in each
        row, e.g. [1, 2] for one panel above two that are side by side.
        Zones without panels are left out, so the board takes their place.
        ``sizes`` (as returned by sizes()) restores saved sizes. Without
        it a zone that stays keeps its size and a panel that stays in its
        zone keeps its own, while a new zone gets the default width and a
        moved panel its natural size - or, with ``natural``, everything
        starts from the default sizes. Unless sizes are being restored,
        the window is then resized to fit the new arrangement.
        """
        new = self.clean(arrangement)
        new_rows = self.clean_rows(arrangement, len(new['bottom']))
        new_row_lists = self._split_rows(new['bottom'], new_rows)
        old = self.arrangement
        old_row_lists = self.bottom_row_lists()
        self.root.update_idletasks()
        chrome = old_main_h = None
        if self._arranged:
            # Window space that is not ours: margins, menu, status bar.
            chrome = (self.root.winfo_width() - self.main.winfo_width(),
                      self.root.winfo_height() - self.main.winfo_height())
            old_main_h = self.main.winfo_height()
        kept = self.sizes() if self._arranged and not natural \
            else {'zones': {}, 'panels': {}, 'rows': []}
        old_zone_of = {k: z for z in self.ZONES for k in old[z]}
        if sizes is None:
            zone_px = dict(kept['zones'])
            panel_px = {k: v for k, v in kept['panels'].items()
                        if k in new[old_zone_of[k]]}
            # Under the board a row that stays as it was keeps its height
            # and the widths of its panels; other rows start afresh.
            for row in old_row_lists:
                if row not in new_row_lists:
                    for key in row:
                        panel_px.pop(key, None)
            kept_row_px = {tuple(row): px for row, px in
                           zip(old_row_lists, kept['rows'])}
            row_px = [kept_row_px.get(tuple(row)) for row in new_row_lists]
            # The board box goes back to the height of what it holds,
            # and a bottom zone that is new forgets the height given to
            # the old one.
            self.box_px = None
            if self._board_size[1]:
                self.board_box.config(
                    height=self._board_size[1] + self.extra_px)
            if natural or not (old['bottom'] and new['bottom']) \
                    or old_row_lists != new_row_lists:
                self.bottom_px = None
        else:
            zone_px = dict(sizes.get('zones') or {})
            panel_px = dict(sizes.get('panels') or {})
            saved_rows = sizes.get('rows')
            if not isinstance(saved_rows, list):
                saved_rows = []
            row_px = [saved_rows[i] if i < len(saved_rows) else None
                      for i in range(len(new_row_lists))]

            def height(name):
                value = sizes.get(name)
                return value if isinstance(value, int) \
                    and not isinstance(value, bool) and value > 0 else None
            self.bottom_px = height('bottom_px')
            self.box_px = height('board_box_px')
            self.bottom_maximized = sizes.get('bottom_maximized') is True

        for paned in [self.main, self.centre] + list(self.zone.values()) \
                + self._row_paned:
            for child in paned.panes():
                paned.forget(child)
        self.main.pack_forget()
        self.arrangement = new
        self.bottom_rows = new_rows

        def size_of(value):
            return value if isinstance(value, int) \
                and not isinstance(value, bool) and value > 0 else None

        for zone in ('left', 'right'):
            # The spare height of a zone goes to its stretch panels, or
            # to its last panel when it has none. Height that belongs to
            # no panel could not be used: a divider only takes from the
            # panels below it, so they would be squeezed above empty room.
            stretchy = [k for k in new[zone] if k in self.stretch_panels] \
                or new[zone][-1:]
            for key in new[zone]:
                panel = self.window[key].Widget
                panel.pack_forget()
                options = dict(minsize=40,
                               stretch='always' if key in stretchy
                               else 'never')
                if size_of(panel_px.get(key)):
                    options['height'] = panel_px[key]
                self.zone[zone].add(panel, **options)
        # Under the board: one paned window per row, its panels side by
        # side, and the rows stacked in the bottom zone.
        for i, row in enumerate(new_row_lists):
            paned = self._bottom_row_paned(i)
            for key in row:
                panel = self.window[key].Widget
                panel.pack_forget()
                options = dict(minsize=40, stretch='always')
                if size_of(panel_px.get(key)):
                    options['width'] = panel_px[key]
                paned.add(panel, **options)
            row_px[i] = size_of(row_px[i]) or max(
                self.window[k].Widget.winfo_reqheight() for k in row)
            self.zone['bottom'].add(paned, minsize=40, stretch='always',
                                    height=row_px[i])

        # With panels under the board, the board box is exactly as tall as
        # the board and the bottom zone takes the rest of the height.
        self.board_box.pack_forget()
        # (Its small minimum lets the divider under it be dragged up
        # freely; the board is made to fit again when it is let go.)
        self.centre.add(self.board_box, minsize=self.BOTTOM_MIN_PX,
                        stretch='never' if new['bottom'] else 'always')
        bottom_px = 0
        if new['bottom']:
            # Rows that stay keep their height; new ones get what their
            # panels need.
            bottom_px = self.bottom_floor_px()
            if sizes is None:
                bottom_px = max(bottom_px, sum(row_px) + self.SASH_PX
                                * (len(row_px) - 1))
            elif isinstance(zone_px.get('bottom'), int):
                bottom_px = max(bottom_px, zone_px['bottom'])
            self.centre.add(self.zone['bottom'], stretch='always',
                            minsize=self.BOTTOM_MIN_PX, height=bottom_px)

        side_px = {}
        for zone in ('left', 'right'):
            if zone == 'right':
                self.main.add(self.centre, stretch='never',
                              minsize=8 * BOARD_SQUARE_MIN_PX
                              + TURN_MARKER_PX)
            if new[zone]:
                side_px[zone] = zone_px.get(zone)
                if not isinstance(side_px[zone], int) or side_px[zone] <= 0:
                    side_px[zone] = self.DEFAULT_ZONE_PX
                self.main.add(self.zone[zone], stretch='always',
                              minsize=self.min_zone_px, width=side_px[zone])
        self.main.pack(fill='both', expand=True)

        # The paned windows were created after the panels, so they would
        # cover them: raise everything they manage back above them.
        self.centre.lift()
        self.board_box.lift()
        for zone in self.ZONES:
            if new[zone]:
                self.zone[zone].lift()
                if zone == 'bottom':
                    for paned in self._row_paned[:len(new_rows)]:
                        paned.lift()
                for key in new[zone]:
                    self.window[key].Widget.lift()
        self.root.update_idletasks()

        if chrome is not None and sizes is None:
            self._fit_window(chrome, side_px, bottom_px,
                             None if natural else old_main_h)
        if not self._arranged:
            # Until now the window had the size its content asked for.
            # Keep that size, but from here on the paned windows ask for
            # nothing: otherwise a window made smaller than the panels'
            # natural size would cut off the status bar and the margins
            # instead of squeezing the panels.
            try:
                self.root.geometry('{}x{}'.format(
                    min(self.root.winfo_reqwidth(),
                        self.root.winfo_screenwidth() - 40),
                    min(self.root.winfo_reqheight(),
                        self.root.winfo_screenheight() - 100)))
                self.main.configure(width=1, height=1)
            except tk.TclError:
                pass
        self._arranged = True

    def _fit_window(self, chrome, side_px, bottom_px, keep_height):
        """Size the window around the board box and the zones as they
        were just arranged. A paned window does not ask for room itself,
        so the size is worked out here. ``keep_height`` is a height the
        panel area should not go below (None: just what is needed)."""
        try:
            if not self.can_size_window():
                return
            width = int(self.board_box.cget('width'))
            for px in side_px.values():
                width += px + self.SASH_PX
            height = int(self.board_box.cget('height'))
            if bottom_px:
                height += bottom_px + self.SASH_PX
            for zone in side_px:
                keys = self.arrangement[zone]
                height = max(height, sum(
                    self.window[k].Widget.winfo_reqheight() for k in keys)
                    + self.SASH_PX * (len(keys) - 1))
            if keep_height:
                height = max(height, keep_height)
            width = min(width + chrome[0], self.root.winfo_screenwidth() - 40)
            height = min(height + chrome[1],
                         self.root.winfo_screenheight() - 100)
            self.root.geometry('{}x{}'.format(width, height))
        except (tk.TclError, ValueError):
            pass

    # ----- the board box ---------------------------------------------------
    def board_space(self):
        """Return the (width, height) the board box could have at most:
        what is left of the window when the side zones are at their
        minimum width and the bottom zone at its least height. (The
        bottom zone gets whatever height the board then leaves.)"""
        self.root.update_idletasks()
        width = self.main.winfo_width()
        for zone in ('left', 'right'):
            if self.arrangement[zone]:
                width -= self.min_zone_px + self.SASH_PX
        height = self.main.winfo_height() - self.extra_px
        if self.arrangement['bottom']:
            height -= self.bottom_floor_px() + self.SASH_PX
        return width, height

    def bottom_floor_px(self):
        """Height the bottom zone keeps before the board gives way: the
        height the user dragged it to, or else what its panels need."""
        if self.bottom_px is None \
                or self.bottom_maximized != self.is_maximized():
            return self.bottom_natural_px()
        return max(self.BOTTOM_MIN_PX, self.bottom_px)

    def bottom_natural_px(self):
        """Height the panels under the board need for their content."""
        rows = self.bottom_row_lists()
        return sum(max(self.window[k].Widget.winfo_reqheight() for k in row)
                   for row in rows) + self.SASH_PX * max(0, len(rows) - 1)

    def board_box_size(self):
        """Current (width, height) of the board box."""
        return self.board_box.winfo_width(), self.board_box.winfo_height()

    def set_board_box(self, width, height):
        """Make the board box fit a board of this size (and what is
        fixed under it); the zones take the rest. (Above a bottom zone
        the box can be taller than that: see _bottom_dragged.)"""
        self._board_size = (width, height)
        box_height = height + self.extra_px
        if self.box_px is not None and self.arrangement['bottom'] \
                and self.bottom_maximized == self.is_maximized():
            room = self.main.winfo_height() - self.SASH_PX \
                - self.bottom_floor_px()
            box_height = max(box_height, min(self.box_px, room))
        self.board_box.config(width=width, height=box_height)
        try:
            self.main.paneconfigure(self.centre, width=width)
            if self.arrangement['bottom']:
                self.centre.paneconfigure(self.board_box, height=box_height)
        except tk.TclError:
            pass    # not arranged yet

    def resize_window_for_board_box(self, width, height):
        """Resize the window so the box of a board of this size fits,
        keeping the width of the side zones as it is. Call before
        set_board_box().

        A paned window does not ask for more room when one of its panes
        grows, so the window size is set explicitly. A maximized window is
        left alone, and the window never grows past the screen.
        """
        # A board size chosen outright: no spare height is kept under it.
        self.box_px = None
        try:
            if not self.can_size_window():
                return
            self.root.update_idletasks()
            grow_w = width - self.centre.winfo_width()
            need_h = height + self.extra_px
            if self.arrangement['bottom']:
                need_h += self.zone['bottom'].winfo_height() + self.SASH_PX
            grow_h = max(0, need_h - self.main.winfo_height())
            if not grow_w and not grow_h:
                return
            new_w = min(self.root.winfo_width() + grow_w,
                        self.root.winfo_screenwidth() - 40)
            new_h = min(self.root.winfo_height() + grow_h,
                        self.root.winfo_screenheight() - 100)
            self.root.geometry('{}x{}'.format(new_w, new_h))
        except tk.TclError:
            pass

    # ----- window and divider events ---------------------------------------
    def _main_resized(self, event):
        """The window changed size: report it once the resizing settles."""
        if event.widget is not self.main:
            return
        if self._resize_after_id is not None:
            try:
                self.root.after_cancel(self._resize_after_id)
            except tk.TclError:
                pass
        self._resize_after_id = self.root.after(80, self._report, None)

    def _divider_released(self, beside_board):
        """The user let go of a divider (beside the board, or in a zone)."""
        if beside_board:
            self.root.after(1, self._side_dragged)
        else:
            self.root.after(1, self.on_change)

    def _side_dragged(self):
        """The divider between the board and a side zone was moved:
        report the room that leaves for the board."""
        try:
            width, height = self.board_box_size()
            height -= self.extra_px
            if self.arrangement['bottom']:
                # Here the box is only as tall as the board, which may
                # also use the height the panels under it can spare.
                height = max(height, self.board_space()[1])
        except tk.TclError:
            return
        self._report((width, height))

    def _bottom_pressed(self, event):
        """A drag of the divider under the board may begin: note the
        heights of the bottom zone and the board box as they are."""
        if self.arrangement['bottom']:
            self._bottom_press = (self.zone['bottom'].winfo_height(),
                                  self.board_box.winfo_height())

    def _bottom_dragged(self):
        """The user let go of the divider under the board.

        The panels under the board get the height they were dragged to.
        The board keeps its size: the window becomes taller or shorter
        instead. Where the window cannot follow (it is maximized, or as
        tall as the screen) the divider stays where it was dropped: a
        board that no longer fits above it becomes smaller, and one that
        got room for a larger size becomes larger.
        """
        press, self._bottom_press = self._bottom_press, None
        try:
            if press is None or not self.arrangement['bottom']:
                return
            self.root.update_idletasks()
            wanted = self.zone['bottom'].winfo_height()
            if abs(wanted - press[0]) < 2:
                return                          # a click, not a drag
            board_width, board_height = self._board_size
            box_height = board_height + self.extra_px
            main_height = new_main_height = self.main.winfo_height()
            if self.can_size_window():
                root_height = self.root.winfo_height()
                new_root_height = min(
                    root_height + box_height + self.SASH_PX + wanted
                    - main_height, self.root.winfo_screenheight() - 100)
                if new_root_height != root_height:
                    self.root.geometry('{}x{}'.format(
                        self.root.winfo_width(), new_root_height))
                    new_main_height += new_root_height - root_height
            room = new_main_height - self.SASH_PX - wanted
            self.bottom_px = wanted
            self.bottom_maximized = self.is_maximized()
            if room == box_height:
                self.box_px = None
                self.set_board_box(board_width, board_height)
            else:
                # The window could not follow: the owner chooses the
                # board for the room that is left, and saves.
                self.box_px = room
                self._report((self.board_space()[0], room - self.extra_px),
                             True)
        except tk.TclError:
            return
        if new_main_height != main_height:
            self.refit_later()      # once the window has its new height
        elif room == box_height:
            self.on_change()

    def _report(self, room, grow_only=False):
        if room is None:
            self._resize_after_id = None
        try:
            if not self.main.winfo_exists() or self.main.winfo_width() <= 1:
                return
        except tk.TclError:
            return
        self.on_resize(room, grow_only)

    # ----- moving a panel by its title bar ---------------------------------
    def _rel(self, widget):
        """(x, y, width, height) of a widget relative to the layout row."""
        return (widget.winfo_rootx() - self.row.winfo_rootx(),
                widget.winfo_rooty() - self.row.winfo_rooty(),
                widget.winfo_width(), widget.winfo_height())

    def drop_target(self, key, x_root, y_root):
        """Where panel ``key`` would land if dropped at this screen point.

        Returns (zone, index, marker) - marker being the (x, y, w, h)
        rectangle, relative to the layout row, that shows the spot - or
        None when the point is not over a place to drop. Under the board
        the index is (row, column, True for a new row of its own).
        """
        px = x_root - self.row.winfo_rootx()
        py = y_root - self.row.winfo_rooty()
        bx, by, bw, bh = self._rel(self.board_box)
        board_h = min(bh, bw - TURN_MARKER_PX)     # the board itself
        box_h = min(bh, board_h + self.extra_px)   # and what is under it
        thick = 6
        if px < bx:
            zone = 'left'
        elif px > bx + bw:
            zone = 'right'
        elif py > by + board_h * 0.7:
            zone = 'bottom'
        elif px < bx + bw * 0.25:
            zone = 'left'
        elif px > bx + bw * 0.75:
            zone = 'right'
        else:
            return None
        if zone == 'bottom':
            return self._bottom_drop_target(key, px, py,
                                            (bx, by + box_h, bw), thick)

        others = [k for k in self.arrangement[zone] if k != key]
        if not others:
            # An empty zone: mark the edge of the board it would open on.
            if zone == 'left':
                marker = (bx, by, thick, board_h)
            else:
                marker = (bx + bw - thick, by, thick, board_h)
            return zone, 0, marker

        boxes = [self._rel(self.window[k].Widget) for k in others]
        index = len(others)
        for i, (x, y, w, h) in enumerate(boxes):
            if py < y + h / 2:
                index = i
                break
        x, y, w, h = boxes[min(index, len(boxes) - 1)]
        after_last = index == len(boxes)
        marker = (x, y + h - thick if after_last else y, w, thick)
        return zone, index, marker

    def _bottom_drop_target(self, key, px, py, box, thick):
        """drop_target() for a point under the board. ``box`` is (x, y of
        the bottom edge, width) of the board box.

        The top or bottom quarter of a row means a new row above or below
        it (a bar across); the middle means into that row, beside its
        panels (an upright bar).
        """
        bx, box_bottom, bw = box
        rows = [[k for k in row if k != key]
                for row in self.bottom_row_lists()]
        rows = [row for row in rows if row]
        if not rows:
            return 'bottom', (0, 0, True), (bx, box_bottom - thick, bw, thick)
        spans = []
        for row in rows:
            boxes = [self._rel(self.window[k].Widget) for k in row]
            spans.append((min(b[1] for b in boxes),
                          max(b[1] + b[3] for b in boxes), boxes))
        r = len(rows) - 1
        for i, (top, bottom, _) in enumerate(spans):
            if py < bottom:
                r = i
                break
        top, bottom, boxes = spans[r]
        edge = (bottom - top) * 0.25
        if py < top + edge:
            return 'bottom', (r, 0, True), (bx, top, bw, thick)
        if py > bottom - edge:
            return 'bottom', (r + 1, 0, True), \
                (bx, bottom - thick, bw, thick)
        column = len(boxes)
        for i, (x, y, w, h) in enumerate(boxes):
            if px < x + w / 2:
                column = i
                break
        x, y, w, h = boxes[min(column, len(boxes) - 1)]
        after_last = column == len(boxes)
        return 'bottom', (r, column, False), \
            (x + w - thick if after_last else x, y, thick, h)

    def _drag_press(self, event, key):
        self._drag = {'key': key, 'x': event.x_root, 'y': event.y_root,
                      'active': False, 'target': None}

    def _drag_motion(self, event):
        drag = self._drag
        if drag is None:
            return
        if not drag['active']:
            if abs(event.x_root - drag['x']) < self.DRAG_START_PX and \
                    abs(event.y_root - drag['y']) < self.DRAG_START_PX:
                return
            drag['active'] = True
        drag['target'] = self.drop_target(drag['key'], event.x_root,
                                          event.y_root)
        if drag['target'] is None:
            self.drop_marker.place_forget()
        else:
            x, y, w, h = drag['target'][2]
            self.drop_marker.place(x=x, y=y, width=w, height=h)
            self.drop_marker.lift()

    def _drag_release(self, event):
        drag, self._drag = self._drag, None
        self.drop_marker.place_forget()
        if drag is None or not drag['active'] or drag['target'] is None:
            return
        zone, index, _ = drag['target']
        self.move_panel(drag['key'], zone, index)

    def move_panel(self, key, zone, index=None):
        """Move panel ``key`` to ``zone`` (at ``index``, default last).

        Under the board ``index`` is (row, column, new_row) as given by
        drop_target(); by default the panel gets a new row at the end.
        """
        if key not in self.panel_keys or zone not in self.ZONES:
            return
        new = {z: [k for k in keys if k != key]
               for z, keys in self.arrangement.items()}
        rows = [[k for k in row if k != key]
                for row in self.bottom_row_lists()]
        rows = [row for row in rows if row]
        if zone == 'bottom':
            if index is None:
                index = (len(rows), 0, True)
            row, column, new_row = index
            if new_row or row >= len(rows):
                rows.insert(min(row, len(rows)), [key])
            else:
                rows[row].insert(min(column, len(rows[row])), key)
            new['bottom'] = [k for r in rows for k in r]
        else:
            if index is None or index > len(new[zone]):
                index = len(new[zone])
            new[zone].insert(index, key)
        new_rows = [len(row) for row in rows]
        if new == self.arrangement and new_rows == self.bottom_rows:
            return
        new['bottom_rows'] = new_rows
        self.arrange(new)
        self.refit_later()

    def refit_later(self):
        """Ask the owner to fit the board again once the window has taken
        the size just requested for it."""
        if self._resize_after_id is not None:
            try:
                self.root.after_cancel(self._resize_after_id)
            except tk.TclError:
                pass
        self._resize_after_id = self.root.after(150, self._report, None)


class EasyChessGui:
    queue = queue.Queue()

    def __init__(self, theme, engine_config_file, user_config_file,
                 gui_book_file, computer_book_file, human_book_file,
                 is_use_gui_book, is_random_book, max_book_ply,
                 max_depth=MAX_DEPTH):
        self.theme = theme
        self.user_config_file = user_config_file
        self.engine_config_file = engine_config_file
        self.gui_book_file = gui_book_file
        self.computer_book_file = computer_book_file
        self.human_book_file = human_book_file
        self.max_depth = max_depth
        self.is_use_gui_book = is_use_gui_book
        self.is_random_book = is_random_book
        self.max_book_ply = max_book_ply
        self.opp_path_and_file = None
        self.opp_file = None
        self.opp_id_name = None
        self.adviser_file = None
        self.adviser_path_and_file = None
        self.adviser_id_name = None
        self.adviser_hash = 128
        self.adviser_threads = 1
        self.adviser_movetime_sec = 10
        self.pecg_auto_save_game = 'pecg_auto_save_games.pgn'
        self.settings_file = 'pecg_settings.json'
        self.my_games = 'pecg_my_games.pgn'
        self.repertoire_file = {
            'white': 'pecg_white_repertoire.pgn',
            'black': 'pecg_black_repertoire.pgn'
        }
        # The color the human plays. It defaults to white for every new game;
        # pressing Engine->Go before the first move switches it to black.
        self.is_user_white = True
        # Board orientation only (which color is drawn at the bottom).
        # Board->Flip toggles it at any time without affecting the game.
        self.is_white_at_bottom = True
        # Active menubar definition; swapped between the idle and in-game
        # states by set_menu_state() and reused on window rebuilds.
        self.current_menu_def = build_play_menu(in_game=False)
        self.init_game()
        self.fen = None
        self.psg_board = None
        self.menu_elem = None
        self.review_menu_elem = None

        # Board scale: square size in px within BOARD_SQUARE_MIN/MAX_PX.
        # Loaded from settings, or auto-fitted to the screen on first start.
        self.square_px = BASE_SQUARE_PX
        # The board size the user wants; square_px can be smaller for a
        # while when the window has no room for it. This one is saved.
        self.preferred_square_px = BASE_SQUARE_PX
        self._board_size_from_settings = False
        # square_px -> {piece: image file for that board size}.
        self._piece_image_cache = {}

        # Board canvas state (one sg.Graph per window, key '_board_graph_k')
        self._board_square_fig = {}   # (row,col) -> rect figure id
        self._board_piece_fig = {}    # (row,col) -> piece image figure id
        self._board_label_fig = {}    # (row,col) -> [coordinate label ids]
        self._turn_marker_fig = []    # the two turn dots beside the board
        # Side to move shown by the turn marker: True white, False black.
        self.side_to_move = True
        # The PanelLayout of each window that is open ('play', 'review').
        self.panel_layouts = {mode: None for mode in PANEL_LAYOUTS}
        # Mouse input state on the board canvas
        self._drag_window = None      # sg.Window that owns the bound canvas
        self._drag_source = None      # (row,col) of the mouse press
        self._drag_piece = None       # piece code being dragged
        self._drag_started = False    # True once the piece has been lifted
        self._drag_fig = None         # figure id of the floating piece
        self.engine_id_name_list = []
        self.engine_file_list = []
        self.username = 'Human'

        self.human_base_time_ms = 5 * 60 * 1000  # 5 minutes
        self.human_inc_time_ms = 10 * 1000  # 10 seconds
        self.human_period_moves = 0
        self.human_tc_type = 'fischer'

        self.engine_base_time_ms = 3 * 60 * 1000  # 5 minutes
        self.engine_inc_time_ms = 2 * 1000  # 10 seconds
        self.engine_period_moves = 0
        self.engine_tc_type = 'fischer'

        # Default board color is brown
        self.sq_light_color = '#F0D9B5'
        self.sq_dark_color = '#B58863'

        # Move highlight, for brown board
        self.move_sq_light_color = '#E8E18E'
        self.move_sq_dark_color = '#B8AF4E'

        self.gui_theme = 'Reddit'

        self.is_save_time_left = False
        self.is_save_user_comment = True
        self.is_time_forfeit_enabled = True
        # Time caps (seconds) for Review-mode analysis and threat searches;
        # user-configurable via Settings/Game and persisted in the settings file.
        self.review_analysis_time_sec = REVIEW_ANALYSIS_TIME_SEC
        self.review_threat_time_sec = REVIEW_THREAT_TIME_SEC
        # Lines of analysis (MultiPV) asked for in Review mode; set in the
        # Analysis panel and persisted.
        self.review_analysis_multipv = REVIEW_ANALYSIS_MULTIPV_LINES
        # The most lines the analysis engine can give (set when the Review
        # window opens: show_review_engine_settings).
        self.review_multipv_limit = REVIEW_ANALYSIS_MULTIPV_MAX
        # Auto-analysis defaults to the analysis engine, but the user can
        # pick any installed engine and a per-move time in milliseconds.
        self.auto_analysis_engine_id_name = None
        self.auto_analysis_time_ms = AUTO_ANALYSIS_TIME_MS
        # Auto-analysis always searches one line (MultiPV 1); not user-facing.
        self.auto_analysis_replay_plies = AUTO_ANALYSIS_REPLAY_PLIES
        # Per-(role, engine) UCI option overrides:
        # {role: {engine_id_name: {option_name: value}}}, deltas vs base.
        self.role_engine_options = {}
        # Saved panel arrangement and sizes of each window, as returned
        # by PanelLayout.state(); None means the default.
        self.panel_layout_states = {mode: None for mode in PANEL_LAYOUTS}
        self.analysis_file = None
        self.analysis_path_and_file = None
        self.analysis_id_name = None
        self.threat_file = None
        self.threat_path_and_file = None
        self.threat_id_name = None
        # Recently opened review PGN files, most recent first (persisted).
        self.recent_pgn_files = []
        self.review_queue = queue.Queue()
        self.threat_queue = queue.Queue()
        self.auto_analysis_queue = queue.Queue()
        self.auto_analysis_thread = None
        self.auto_analysis_cancel = threading.Event()
        self.reset_review_state()

    def reset_review_state(self):
        """Reset review mode state."""
        self.review_pgn_file = None
        self.review_games = []
        self.review_game = None
        self.review_game_index = None
        # The Game list panel: its rows as shown, the game (index into
        # review_games) of each row, and (column, reversed) it is sorted
        # by - None for the order of the file.
        self.review_list_rows = []
        self.review_list_map = []
        self.review_list_sort = None
        # The boards the running analysis and threat searches were given.
        self.review_analysis_board = None
        self.review_threat_board = None
        self.review_move_index = 0
        self.review_move_labels = []
        self.review_boards = []
        self.review_nodes = []
        self.review_window = None
        self.review_analysis_lines = {}
        self.review_analysis_enabled = False
        self.review_analysis_status = 'Analysis stopped'
        self.review_analysis_search = None
        self.review_analysis_engine = None
        self._stale_analysis_searches = []
        self.review_analysis_stale = False
        self.review_threat_enabled = False
        self.review_threat_status = 'Threat stopped'
        self.review_threat_line = None
        self.review_threat_search = None
        self.review_threat_engine = None
        self._stale_threat_searches = []
        self.review_threat_stale = False
        self.review_nav_last_time = 0
        if self.auto_analysis_thread is not None:
            self.auto_analysis_cancel.set()
            self.auto_analysis_thread = None
        self.auto_analysis_cancel = threading.Event()

    def reset_review_run_state(self):
        """Reset run state of review mode when exiting, keeping loaded game/pgn."""
        self.review_window = None
        self.review_analysis_lines = {}
        self.review_analysis_enabled = False
        self.review_analysis_status = 'Analysis stopped'
        self.review_analysis_search = None
        self.review_analysis_engine = None
        self._stale_analysis_searches = []
        self.review_analysis_stale = False
        self.review_threat_enabled = False
        self.review_threat_status = 'Threat stopped'
        self.review_threat_line = None
        self.review_threat_search = None
        self.review_threat_engine = None
        self._stale_threat_searches = []
        self.review_threat_stale = False
        self.review_nav_last_time = 0
        if self.auto_analysis_thread is not None:
            self.auto_analysis_cancel.set()
            self.auto_analysis_thread = None
        self.auto_analysis_cancel = threading.Event()

    def on_move_clicked(self, idx):
        """Callback when a move in the Multiline PGN view is clicked."""
        if self.review_window is None:
            return
        self.review_move_index = idx
        self.update_review_window(self.review_window)
        self.follow_review_position(self.review_window)

    def follow_review_position(self, window):
        """The position on the Review board changed (another move, or
        another game): make analysis and threat follow it if they are on.

        Their searches are only told to stop here, without blocking. The
        Review loop restarts them on the new position once navigation has
        settled (REVIEW_NAV_DEBOUNCE_SEC).
        """
        self.restart_review_analysis_later(window)
        self.restart_review_threat_later(window)

    def restart_review_analysis_later(self, window):
        """Analysis has to start again: the position changed, or one of
        its settings (Hash, Threads, MultiPV).

        If it is on, its output is marked stale, so poll discards the
        lines of the old search and the Review loop knows to restart it
        after the debounce. If it is off it just shows 'stopped'.
        """
        if not self.review_analysis_enabled:
            self.refresh_review_analysis(window)
            return
        if self.review_analysis_search is not None:
            self.review_analysis_search.stop()
        self.review_analysis_stale = True
        self.review_analysis_lines = {}
        self.review_analysis_status = 'Waiting...'
        self.update_review_analysis_panel(window)
        self.review_nav_last_time = time.time()

    def restart_review_threat_later(self, window):
        """Threat has to start again (see restart_review_analysis_later)."""
        if not self.review_threat_enabled:
            self.refresh_review_threat(window)
            return
        if self.review_threat_search is not None:
            self.review_threat_search.stop()
        self.review_threat_stale = True
        self.review_threat_line = None
        self.review_threat_status = 'Waiting...'
        self.update_review_threat_panel(window)
        self.review_nav_last_time = time.time()

    def highlight_current_move(self, widget):
        """Highlights the active move in the Multiline text and scrolls it into view."""
        widget.tag_remove("current_move", "1.0", "end")
        widget.tag_remove("current_var_move", "1.0", "end")
        widget.tag_remove("current_var_block", "1.0", "end")

        current_node = self.review_nodes[self.review_move_index]

        # 1. Determine if the current move is in a variation
        in_var = False
        curr = current_node
        while curr.parent is not None:
            if curr.parent.variations and curr != curr.parent.variations[0]:
                in_var = True
                break
            curr = curr.parent

        # 2. Highlight active move
        tag_name = f"move_{self.review_move_index}"
        ranges = widget.tag_ranges(tag_name)
        if ranges:
            if in_var:
                widget.tag_add("current_var_move", ranges[0], ranges[1])
            else:
                widget.tag_add("current_move", ranges[0], ranges[1])
            widget.see(ranges[0])

        # 3. Highlight parenthetical variation block if in variation
        if in_var:
            var_root_idx = None
            curr = current_node
            while curr.parent is not None:
                if curr.parent.variations and curr in curr.parent.variations[1:]:
                    if curr in self.review_nodes:
                        var_root_idx = self.review_nodes.index(curr)
                        break
                curr = curr.parent

            if var_root_idx is not None:
                var_tag = f"var_block_{var_root_idx}"
                var_ranges = widget.tag_ranges(var_tag)
                if var_ranges:
                    widget.tag_add("current_var_block", var_ranges[0], var_ranges[1])

    def render_pgn_tree(self, node, board, widget, indent=0, is_var=False):
        """Recursively render game node and variations into the Tkinter Text widget."""

        def render_only_move(n, b, ind):
            NAG_SYMBOLS = {
                1: "!",
                2: "?",
                3: "!!",
                4: "??",
                5: "!?",
                6: "?!",
            }
            if n.move is None:
                return b, None

            # 1. Print starting comment, if any
            if n.starting_comment:
                comment_text = f"{{{n.starting_comment}}} "
                widget.insert("insert", comment_text, "comment")

            turn = b.turn
            fullmove = b.fullmove_number
            san = b.san(n.move)

            nag_suffix = ""
            for nag in n.nags:
                if nag in NAG_SYMBOLS:
                    nag_suffix += NAG_SYMBOLS[nag]

            idx = len(self.review_nodes)
            self.review_nodes.append(n)
            next_b = b.copy()
            next_b.push(n.move)
            self.review_boards.append(next_b)

            prefix = ""
            if turn == chess.WHITE:
                prefix = f"{fullmove}. "
            else:
                if self.first_move_in_line:
                    prefix = f"{fullmove}... "

            move_text = f"{prefix}{san}{nag_suffix} "
            tag_name = f"move_{idx}"
            widget.insert("insert", move_text, (tag_name, "move_link"))
            widget.tag_bind(tag_name, "<Button-1>", lambda event, i=idx: self.on_move_clicked(i))

            self.first_move_in_line = False

            # 2. Print comment, if any
            if n.comment:
                comment_text = f"{{{n.comment}}} "
                widget.insert("insert", comment_text, "comment")

            return next_b, idx

        def render_continuations(n, b, ind):
            if not n.variations:
                return

            mainline_child = n.variations[0]
            # 1. Render mainline child's move
            next_b, idx = render_only_move(mainline_child, b, ind)

            # 2. Render sibling variations (alternatives to mainline child)
            if len(n.variations) > 1:
                for var_node in n.variations[1:]:
                    var_idx = len(self.review_nodes)
                    start_mark = widget.index("insert")

                    widget.insert("insert", "\n" + "    " * (ind + 1) + "( ")
                    self.first_move_in_line = True
                    render_node(var_node, b, ind + 1, True)
                    widget.insert("insert", " ) ")
                    self.first_move_in_line = True

                    end_mark = widget.index("insert")
                    var_tag = f"var_block_{var_idx}"
                    widget.tag_add(var_tag, start_mark, end_mark)

                # After the last variation, continue the mainline on a fresh
                # line at the parent's indentation level.
                if mainline_child.variations:
                    widget.insert("insert", "\n" + "    " * ind)

            # 3. Render mainline child's continuation
            render_continuations(mainline_child, next_b, ind)

        def render_node(n, b, ind, is_v):
            next_b, idx = render_only_move(n, b, ind)
            render_continuations(n, next_b, ind)

        render_node(node, board, indent, is_var)

    def render_review_movelist(self, window):
        """Build and render the entire PGN move list with variations into the Multiline widget."""
        if self.review_game is None or 'review_move_list_k' not in window.AllKeysDict:
            return

        widget = window['review_move_list_k'].Widget
        widget.configure(state='normal')
        widget.delete('1.0', tk.END)

        # Re-initialize index mapping lists
        self.review_nodes = [self.review_game]
        self.review_boards = [self.review_game.board()]

        # Configure styles
        default_fg = widget.cget("foreground")
        widget.tag_configure("move_link", foreground=default_fg, font=widget.cget("font"))
        widget.tag_configure("comment", foreground="green")
        widget.tag_configure("current_move", background="yellow", foreground="black")
        widget.tag_configure("current_var_move", background="#adff2f", foreground="black")
        widget.tag_configure("current_var_block", background="#e2f0d9")

        widget.tag_raise("current_move", "move_link")
        widget.tag_raise("current_var_move", "move_link")
        widget.tag_raise("current_move", "current_var_block")
        widget.tag_raise("current_var_move", "current_var_block")

        widget.tag_bind("move_link", "<Enter>", lambda event: widget.configure(cursor="hand2"))
        widget.tag_bind("move_link", "<Leave>", lambda event: widget.configure(cursor=""))

        # Insert Start Position
        widget.insert("insert", "Start Position", ("move_0", "move_link"))
        widget.tag_bind("move_0", "<Button-1>", lambda event, i=0: self.on_move_clicked(i))
        widget.insert("insert", "\n\n")

        self.first_move_in_line = True
        game = self.review_game
        if game.variations:
            # Render from the root so that alternative first moves (e.g. an
            # engine-best line for move 1) appear inline after the mainline
            # first move instead of at the end of the move list.
            self.render_pgn_tree(game, game.board(), widget, 0, False)

        widget.configure(state='disabled')
        self.highlight_current_move(widget)

    def update_game(self, mc: int, user_move: str, time_left: int, user_comment: str):
        """Saves moves in the game.

        Args:
          mc: move count
          user_move: user's move
          time_left: time left
          user_comment: Can be a 'book' from the engine
        """
        # Save user comment
        if self.is_save_user_comment:
            # If comment is empty
            if not (user_comment and user_comment.strip()):
                if mc == 1:
                    self.node = self.game.add_variation(user_move)
                else:
                    self.node = self.node.add_variation(user_move)

                # Save clock (time left after a move) as move comment
                if self.is_save_time_left:
                    rem_time = self.get_time_h_mm_ss(time_left, False)
                    self.node.comment = '[%clk {}]'.format(rem_time)
            else:
                if mc == 1:
                    self.node = self.game.add_variation(user_move)
                else:
                    self.node = self.node.add_variation(user_move)

                # Save clock, add clock as comment after a move
                if self.is_save_time_left:
                    rem_time = self.get_time_h_mm_ss(time_left, False)
                    self.node.comment = '[%clk {}] {}'.format(rem_time, user_comment)
                else:
                    self.node.comment = user_comment
        # Do not save user comment
        else:
            if mc == 1:
                self.node = self.game.add_variation(user_move)
            else:
                self.node = self.node.add_variation(user_move)

            # Save clock, add clock as comment after a move
            if self.is_save_time_left:
                rem_time = self.get_time_h_mm_ss(time_left, False)
                self.node.comment = '[%clk {}]'.format(rem_time)

    def begin_dialog(self, window):
        """Keep window visible but non-interactive while a dialog is open.

        The '-disabled' wm attribute (Windows-only) blocks all input to the
        window, including the menubar and board canvas binds. Unlike a tk
        grab (sg.Window modal=True), it survives nested popups closing —
        FreeSimpleGUI never restores a parent's grab. On other platforms
        the attribute is unsupported and the dialog's own modal grab is
        the best-effort fallback.
        """
        try:
            window.TKroot.attributes('-disabled', True)
        except Exception:
            pass

    def end_dialog(self, window):
        """Restore interactivity after begin_dialog()."""
        try:
            window.TKroot.attributes('-disabled', False)
        except Exception:
            pass

    def create_new_window(self, window):
        """Hide current window and creates a new window."""
        loc = window.CurrentLocation()
        window.Hide()

        layout = self.build_main_layout(self.is_white_at_bottom)

        w = sg.Window(
            '{} {}'.format(APP_NAME, APP_VERSION),
            layout,
            default_button_element_size=(12, 1),
            auto_size_buttons=False,
            location=(loc[0], loc[1]),
            finalize=True,
            resizable=True,
            icon=ico_path[platform]['pecg']
        )

        # Initialize White and black boxes
        self.update_labels_and_game_tags(w, human=self.username)

        # Panels, board input and menubar font of the new window.
        self.finish_play_window(w)

        window.Close()
        return w

    def delete_player(self, name, pgn, que):
        """Delete the games of player ``name`` from pgn (worker thread).

        Posts progress lines to que and finally 'Done', or 'Failed' when
        anything goes wrong (the reason is logged), so the dialog waiting on
        que always gets an answer.
        """
        try:
            self._delete_player(name, pgn, que)
            que.put('Done')
        except Exception:
            logging.exception('Failed to delete player %s from %s', name, pgn)
            que.put('Failed')

    def _delete_player(self, name, pgn, que):
        """
        Delete games of player name in pgn.

        :param name:
        :param pgn:
        :param que:
        :return:
        """
        logging.info('Enters delete_player()')

        pgn_path = Path(pgn)
        folder_path = pgn_path.parents[0]

        file = PurePath(pgn)
        pgn_file = file.name

        # Create backup of orig, byte for byte (no decoding involved).
        backup = pgn_file + '.backup'
        backup_path = Path(folder_path, backup)
        backup_path.write_bytes(pgn_path.read_bytes())
        logging.info(f'backup copy {backup_path} is successfully created.')

        # Rewrite the file in the encoding it already uses.
        encoding = pgn_file_encoding(pgn_path)

        # Define output file
        output = 'out_' + pgn_file
        output_path = Path(folder_path, output)
        logging.info(f'output {output_path} is successfully created.')

        logging.info(f'Deleting player {name}.')
        gcnt = 0

        # read pgn and save each game if player name to be deleted is not in
        # the game, either white or black. The output is written from
        # scratch so a leftover from a failed attempt is never appended to.
        with open(output_path, 'w', encoding=encoding) as f:
            with open(pgn_path, encoding=encoding) as h:
                game = chess.pgn.read_game(h)
                while game:
                    gcnt += 1
                    que.put('Delete, {}, processing game {}'.format(
                        name, gcnt))
                    wp = game.headers['White']
                    bp = game.headers['Black']

                    # If this game has no player with name to be deleted
                    if wp != name and bp != name:
                        f.write('{}\n\n'.format(game))
                    game = chess.pgn.read_game(h)

        if output_path.exists():
            logging.info(f'Deleting player {name} is successful.')

            # Delete the orig file and rename the current output to orig file
            pgn_path.unlink()
            logging.info('Delete orig pgn file')
            output_path.rename(pgn_path)
            logging.info('Rename output to orig pgn file')

    def get_players(self, pgn, q):
        """Post [player names, number of games] of a PGN file to q.

        Posts None when the file cannot be read (the reason is logged), so
        the dialog waiting on q always gets an answer.
        """
        logging.info('Enters get_players()')
        try:
            players = []
            games = 0
            with open(pgn, encoding=pgn_file_encoding(pgn)) as h:
                while True:
                    headers = chess.pgn.read_headers(h)
                    if headers is None:
                        break

                    wp = headers['White']
                    bp = headers['Black']

                    players.append(wp)
                    players.append(bp)
                    games += 1

            q.put([list(set(players)), games])
        except Exception:
            logging.exception('Failed to read players from %s', pgn)
            q.put(None)

    def get_engine_id_name(self, path_and_file, q):
        """Post ['Done', id name] of a uci engine to q (worker thread).

        The name is None when the engine cannot be started, whatever the
        reason, so the dialog waiting on q always gets an answer.
        """
        id_name = None

        try:
            # .parent never raises, unlike .parents[0] on a drive root.
            folder = Path(path_and_file).parent
            if sys_os == 'Windows':
                engine = chess.engine.SimpleEngine.popen_uci(
                    path_and_file, cwd=folder,
                    creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                engine = chess.engine.SimpleEngine.popen_uci(
                    path_and_file, cwd=folder)
            id_name = engine.id['name']
            engine.quit()
        except Exception:
            logging.exception('Failed to get id name.')

        q.put(['Done', id_name])

    def get_engine_hash(self, eng_id_name):
        """ Returns hash value from engine config file """
        eng_hash = None
        with open(self.engine_config_file, 'r') as json_file:
            data = json.load(json_file)
            for p in data:
                if p['name'] == eng_id_name:
                    # There engines without options
                    try:
                        for n in p['options']:
                            if n['name'].lower() == 'hash':
                                return n['value']
                    except KeyError:
                        logging.info(f'This engine {eng_id_name} has no option.')
                        break
                    except Exception:
                        logging.exception('Failed to get engine hash.')

        return eng_hash

    def get_engine_threads(self, eng_id_name):
        """
        Returns number of threads of eng_id_name from pecg_engines.json.

        :param eng_id_name: the engine id name
        :return: number of threads
        """
        eng_threads = None
        with open(self.engine_config_file, 'r') as json_file:
            data = json.load(json_file)
            for p in data:
                if p['name'] == eng_id_name:
                    try:
                        for n in p['options']:
                            if n['name'].lower() == 'threads':
                                return n['value']
                    except KeyError:
                        logging.info(f'This engine {eng_id_name} has no options.')
                        break
                    except Exception:
                        logging.exception('Failed to get engine threads.')

        return eng_threads

    def get_engine_file(self, eng_id_name):
        """
        Returns eng_id_name's filename and path from pecg_engines.json file.

        :param eng_id_name: engine id name
        :return: engine file and its path
        """
        eng_file, eng_path_and_file = None, None
        with open(self.engine_config_file, 'r') as json_file:
            data = json.load(json_file)
            for p in data:
                if p['name'] == eng_id_name:
                    eng_file = p['command']
                    eng_path_and_file = Path(p['workingDirectory'],
                                             eng_file).as_posix()
                    break

        return eng_file, eng_path_and_file

    def get_engine_id_name_list(self):
        """
        Read engine config file.

        :return: list of engine id names
        """
        eng_id_name_list = []
        with open(self.engine_config_file, 'r') as json_file:
            data = json.load(json_file)
            for p in data:
                if p['protocol'] == 'uci':
                    eng_id_name_list.append(p['name'])

        eng_id_name_list = sorted(eng_id_name_list)

        return eng_id_name_list

    def get_usernames(self):
        """Return the de-duplicated list of saved player names."""
        try:
            with open(self.user_config_file, 'r') as json_file:
                data = json.load(json_file)
        except Exception:
            logging.exception('Failed to read usernames.')
            return [self.username]
        names = []
        for p in data:
            n = p.get('username')
            if n and n not in names:
                names.append(n)
        return names

    def set_current_user(self, name):
        """Make ``name`` the active player and persist it.

        The name is stored last in pecg_user.json (the entry that
        check_user_config_file loads on startup), with duplicates removed, so
        the choice survives a restart and the saved list never repeats a name.
        Returns False if the name is empty.
        """
        name = (name or '').strip()
        if not name:
            return False
        names = [n for n in self.get_usernames() if n != name]
        names.append(name)
        try:
            with open(self.user_config_file, 'w') as h:
                json.dump([{'username': n} for n in names], h, indent=4)
        except Exception:
            logging.exception('Failed to save usernames.')
        self.username = name
        return True

    def delete_username(self, name):
        """Remove a saved player name from pecg_user.json and persist.

        If the list becomes empty it falls back to ['Human']. If the removed
        name was the active player (or the active is no longer present) the
        active switches to the last remaining name, kept last so it reloads on
        restart.
        """
        names = [n for n in self.get_usernames() if n != name]
        if not names:
            names = ['Human']
        if self.username == name or self.username not in names:
            self.username = names[-1]
        # Keep the active player last (check_user_config_file loads the last).
        names = [n for n in names if n != self.username] + [self.username]
        try:
            with open(self.user_config_file, 'w') as h:
                json.dump([{'username': n} for n in names], h, indent=4)
        except Exception:
            logging.exception('Failed to delete username.')

    def check_user_config_file(self):
        """
        Check presence of pecg_user.json file, if nothing we will create
        one with ['username': 'Human']

        :return:
        """
        user_config_file_path = Path(self.user_config_file)
        if user_config_file_path.exists():
            with open(self.user_config_file, 'r') as json_file:
                data = json.load(json_file)
                for p in data:
                    username = p['username']
            self.username = username
        else:
            # Write a new user config file
            data = []
            data.append({'username': 'Human'})

            # Save data to pecg_user.json
            with open(self.user_config_file, 'w') as h:
                json.dump(data, h, indent=4)

    def _read_review_time(self, value, fallback):
        """Parse and clamp a Review-mode time (sec), falling back if invalid."""
        try:
            value = int(value)
        except (TypeError, ValueError):
            logging.info('Invalid review time %r; keeping %s s.', value, fallback)
            return fallback
        return min(REVIEW_ANALYSIS_TIME_MAX,
                   max(REVIEW_ANALYSIS_TIME_MIN, value))

    def read_whole_number(self, text, label, title,
                          min_value=None, max_value=None):
        """Parse and range-check a whole number typed into a dialog field.

        Returns the number, or None after telling the user when ``text`` is
        not a whole number or lies outside ``min_value``..``max_value``
        (either may be None for no limit). The caller keeps its dialog open
        on None.
        """
        try:
            value = int(str(text).strip())
        except (TypeError, ValueError):
            value = None

        if value is not None \
                and (min_value is None or value >= min_value) \
                and (max_value is None or value <= max_value):
            return value

        if min_value is not None and max_value is not None:
            limits = ' from {} to {}'.format(min_value, max_value)
        elif min_value is not None:
            limits = ' not less than {}'.format(min_value)
        elif max_value is not None:
            limits = ' not more than {}'.format(max_value)
        else:
            limits = ''
        sg.popup('{}: please enter a whole number{}.'.format(label, limits),
                 title=title, icon=ico_path[platform]['pecg'])
        return None

    def time_control_rows(self, base_ms, inc_ms):
        """Layout rows to pick a base time and an increment (no typing)."""
        minutes, seconds = divmod(max(0, int(base_ms)) // 1000, 60)
        inc_sec = max(0, int(inc_ms)) // 1000
        return [
            [sg.T('Base time', size=(10, 1)),
             sg.Combo(choices_with(range(TC_BASE_MAX_MIN + 1), minutes),
                      default_value=minutes, readonly=True, size=(5, 1),
                      key='base_min_k'),
             sg.T('min'),
             sg.Combo(list(range(60)), default_value=seconds, readonly=True,
                      size=(4, 1), key='base_sec_k'),
             sg.T('sec')],
            [sg.T('Increment', size=(10, 1)),
             sg.Combo(choices_with(range(TC_INC_MAX_SEC + 1), inc_sec),
                      default_value=inc_sec, readonly=True, size=(5, 1),
                      key='inc_sec_k'),
             sg.T('sec')],
        ]

    def read_time_control(self, values, title):
        """Return (base_ms, inc_ms) picked in a time control dialog.

        Returns None after telling the user when the base time is 0:00, the
        one combination the pickers allow that cannot be used.
        """
        base_sec = 60 * int(values['base_min_k']) + int(values['base_sec_k'])
        if base_sec <= 0:
            sg.popup('Base time must be more than 0.', title=title,
                     icon=ico_path[platform]['pecg'])
            return None
        return 1000 * base_sec, 1000 * int(values['inc_sec_k'])

    def check_spin_options(self, values, opt_meta, title):
        """Validate the numeric (spin) fields of an engine options editor.

        Each must be a whole number within the option's own min..max.
        Returns False after telling the user about the first bad field.
        """
        for m in opt_meta:
            if m['type'] != 'spin' or m['key'] not in values:
                continue
            if self.read_whole_number(values[m['key']], m['name'], title,
                                      m.get('min'), m.get('max')) is None:
                return False
        return True

    def load_settings(self):
        """Load persisted Settings/Game values from the settings file.

        A missing file or missing keys leave the __init__ defaults in place.
        """
        settings_path = Path(self.settings_file)
        if not settings_path.exists():
            return
        try:
            with open(self.settings_file, 'r') as json_file:
                data = json.load(json_file)
        except Exception:
            logging.exception('Failed to read settings file.')
            return

        if 'is_save_time_left' in data:
            self.is_save_time_left = bool(data['is_save_time_left'])
        if 'is_time_forfeit_enabled' in data:
            self.is_time_forfeit_enabled = bool(data['is_time_forfeit_enabled'])
        for key in ('review_analysis_time_sec', 'review_threat_time_sec'):
            if key in data:
                setattr(self, key,
                        self._read_review_time(data[key], getattr(self, key)))
        if 'review_analysis_multipv' in data:
            try:
                self.review_analysis_multipv = max(
                    1, min(REVIEW_ANALYSIS_MULTIPV_MAX,
                           int(data['review_analysis_multipv'])))
            except (TypeError, ValueError):
                pass
        if 'adviser_movetime_sec' in data:
            self.adviser_movetime_sec = self._read_review_time(
                data['adviser_movetime_sec'], self.adviser_movetime_sec)
        if 'auto_analysis_engine_id_name' in data:
            self.auto_analysis_engine_id_name = data['auto_analysis_engine_id_name']
        if 'auto_analysis_replay_plies' in data:
            try:
                self.auto_analysis_replay_plies = max(
                    AUTO_ANALYSIS_REPLAY_PLIES_MIN,
                    min(AUTO_ANALYSIS_REPLAY_PLIES_MAX,
                        int(data['auto_analysis_replay_plies'])))
            except (TypeError, ValueError):
                pass
        if 'board_square_px' in data:
            try:
                self.square_px = fit_square_px(int(data['board_square_px']))
                self._board_size_from_settings = True
            except (TypeError, ValueError):
                pass
        if 'auto_analysis_time_ms' in data:
            try:
                self.auto_analysis_time_ms = min(
                    AUTO_ANALYSIS_TIME_MS_MAX,
                    max(AUTO_ANALYSIS_TIME_MS_MIN,
                        int(data['auto_analysis_time_ms'])))
            except (TypeError, ValueError):
                pass
        elif 'auto_analysis_time_sec' in data:
            # Settings written before v2.19.0 stored seconds; convert once
            # to milliseconds (the file is rewritten on the next save).
            try:
                self.auto_analysis_time_ms = min(
                    AUTO_ANALYSIS_TIME_MS_MAX,
                    max(AUTO_ANALYSIS_TIME_MS_MIN,
                        int(data['auto_analysis_time_sec']) * 1000))
            except (TypeError, ValueError):
                pass
        # Per-role engine option overrides (the active role ids are applied
        # later by restore_engine_roles, once the engine list exists).
        for mode, spec in PANEL_LAYOUTS.items():
            if isinstance(data.get(spec['setting']), dict):
                self.panel_layout_states[mode] = data[spec['setting']]
        if isinstance(data.get('role_engine_options'), dict):
            self.role_engine_options = data['role_engine_options']
        if isinstance(data.get('recent_pgn_files'), list):
            self.recent_pgn_files = [
                p for p in data['recent_pgn_files'] if isinstance(p, str)
            ][:MAX_RECENT_PGN_FILES]
        if 'review_pgn_file' in data:
            self.review_pgn_file = data['review_pgn_file']
            if self.review_pgn_file and os.path.isfile(self.review_pgn_file):
                try:
                    self.review_games, _ = self.load_pgn_games(self.review_pgn_file)
                except Exception:
                    logging.exception('Failed to auto-load PGN games from saved path.')

    def save_settings(self):
        """Persist Settings/Game values to the settings file."""
        data = {
            'is_save_time_left': self.is_save_time_left,
            'is_time_forfeit_enabled': self.is_time_forfeit_enabled,
            'review_analysis_time_sec': self.review_analysis_time_sec,
            'review_threat_time_sec': self.review_threat_time_sec,
            'review_analysis_multipv': self.review_analysis_multipv,
            'opp_id_name': self.opp_id_name,
            'adviser_id_name': self.adviser_id_name,
            'analysis_id_name': self.analysis_id_name,
            'threat_id_name': self.threat_id_name,
            'adviser_movetime_sec': self.adviser_movetime_sec,
            'auto_analysis_engine_id_name': self.auto_analysis_engine_id_name,
            'auto_analysis_replay_plies': self.auto_analysis_replay_plies,
            'auto_analysis_time_ms': self.auto_analysis_time_ms,
            'board_square_px': self.preferred_square_px,
            'role_engine_options': self.role_engine_options,
            'recent_pgn_files': self.recent_pgn_files,
            'review_pgn_file': self.review_pgn_file,
        }
        for mode, spec in PANEL_LAYOUTS.items():
            data[spec['setting']] = self.panel_layout_states[mode]
        try:
            with open(self.settings_file, 'w') as json_file:
                json.dump(data, json_file, indent=4)
        except Exception:
            logging.exception('Failed to save settings file.')

    # ----- Engine role helpers -----
    def get_engine_options(self, eng_id_name):
        """Return the option list for an engine from pecg_engines.json."""
        try:
            with open(self.engine_config_file, 'r') as json_file:
                data = json.load(json_file)
            for p in data:
                if p['name'] == eng_id_name:
                    return p.get('options', [])
        except Exception:
            logging.exception('Failed to read engine options.')
        return []

    def get_role_options(self, role, eng_id_name):
        """Return saved option overrides {name: value} for (role, engine)."""
        if not eng_id_name:
            return {}
        return dict(self.role_engine_options.get(role, {}).get(eng_id_name, {}))

    def set_role_options(self, role, eng_id_name, deltas):
        """Store (or clear) option overrides for (role, engine) and persist."""
        role_map = self.role_engine_options.setdefault(role, {})
        if deltas:
            role_map[eng_id_name] = deltas
        else:
            role_map.pop(eng_id_name, None)
        self.save_settings()

    def delete_role_options(self, role, eng_id_name):
        """Remove saved option overrides for (role, engine) and persist."""
        self.role_engine_options.get(role, {}).pop(eng_id_name, None)
        self.save_settings()

    def set_active_role(self, role, eng_id_name):
        """Make eng_id_name the active engine for role and persist."""
        id_attr, file_attr, path_attr, _, _ = ROLE_META[role]
        try:
            eng_file, eng_path = self.get_engine_file(eng_id_name)
        except Exception:
            logging.exception('Failed to resolve engine file for %s.', eng_id_name)
            return
        setattr(self, id_attr, eng_id_name)
        setattr(self, file_attr, eng_file)
        setattr(self, path_attr, eng_path)
        self.save_settings()

    def restore_engine_roles(self):
        """Apply persisted active engine per role (after the engine list exists).

        Saved ids that are no longer installed are ignored (role keeps its
        default). Must run after set_default_* in main_loop.
        """
        settings_path = Path(self.settings_file)
        if not settings_path.exists():
            return
        try:
            with open(self.settings_file, 'r') as json_file:
                data = json.load(json_file)
        except Exception:
            logging.exception('Failed to read settings for engine roles.')
            return
        for role, (id_attr, _, _, _, _) in ROLE_META.items():
            name = data.get(id_attr)
            if name and name in self.engine_id_name_list:
                self.set_active_role(role, name)

    def rename_engine_references(self, old_name, new_name):
        """Follow an engine rename everywhere the engine is stored by name.

        The roles that use the engine, the saved Auto-Analyze engine and the
        per-role option overrides all move to the new name, and the settings
        are saved, so a rename never leaves them pointing at a name that no
        longer exists.
        """
        for id_attr, _, _, _, _ in ROLE_META.values():
            if getattr(self, id_attr) == old_name:
                setattr(self, id_attr, new_name)
        if self.auto_analysis_engine_id_name == old_name:
            self.auto_analysis_engine_id_name = new_name
        for role_map in self.role_engine_options.values():
            if isinstance(role_map, dict) and old_name in role_map:
                role_map[new_name] = role_map.pop(old_name)
        self.save_settings()

    def build_engine_options_layout(self, option_list, current_values=None):
        """Build editor rows for an engine's UCI options.

        Returns (option_layout, option_layout2, opt_meta) where opt_meta is a
        list of {'name','key','type','base'}. ``current_values`` (name->value)
        overrides the displayed value per option. The 2-column split for many
        options is preserved.
        """
        current_values = current_values or {}
        option_layout, option_layout2 = [], []
        opt_meta = []
        num_opt = len(option_list)
        opt_cnt = 0
        for o in option_list:
            type_ = o.get('type')
            name = o.get('name')
            if name is None or type_ == 'button':
                continue
            opt_cnt += 1
            base = o.get('value')
            value = current_values.get(name, base)
            key_name = '{}_{}_k'.format(type_, name.lower())

            if type_ == 'spin':
                ttip = 'min {} max {}'.format(o.get('min'), o.get('max'))
                row = [sg.Text(name, size=(16, 1)),
                       sg.Input(value, size=(8, 1), key=key_name, tooltip=ttip)]
            elif type_ == 'check':
                row = [sg.Text(name, size=(16, 1)),
                       sg.Checkbox('', key=key_name, default=bool(value))]
            elif type_ == 'combo':
                row = [sg.Text(name, size=(16, 1)),
                       sg.Combo(o.get('choices', []), default_value=value,
                                size=(12, 1), key=key_name)]
            elif type_ == 'string':
                if 'syzygypath' in name.lower():
                    row = [sg.Text(name, size=(16, 1)),
                           sg.Input(value, size=(12, 1), key=key_name),
                           sg.FolderBrowse()]
                elif 'weightsfile' in name.lower():
                    row = [sg.Text(name, size=(16, 1)),
                           sg.Input(value, size=(12, 1), key=key_name),
                           sg.FileBrowse()]
                else:
                    row = [sg.Text(name, size=(16, 1)),
                           sg.Input(value, size=(16, 1), key=key_name)]
            else:
                continue

            opt_meta.append({'name': name, 'key': key_name,
                             'type': type_, 'base': base,
                             'min': o.get('min'), 'max': o.get('max')})
            if num_opt > 10 and opt_cnt > num_opt // 2:
                option_layout2.append(row)
            else:
                option_layout.append(row)
        return option_layout, option_layout2, opt_meta

    def read_option_values(self, values, opt_meta):
        """Read edited option values from a window values dict -> {name: value}."""
        result = {}
        for m in opt_meta:
            if m['key'] in values:
                result[m['name']] = values[m['key']]
        return result

    def _build_options_window_layout(self, option_layout, option_layout2):
        """Wrap option rows in a screen-capped scrollable column + OK/Cancel."""
        if len(option_layout2) > 1:
            body = [[sg.Column(option_layout, vertical_alignment='top'),
                     sg.Column(option_layout2, vertical_alignment='top')]]
        else:
            body = [[sg.Column(option_layout, vertical_alignment='top')]]
        rows = max(len(option_layout), len(option_layout2))
        try:
            _, screen_h = sg.Window.get_screen_size()
        except Exception:
            screen_h = 800
        view_h = min(rows * 28 + 10, max(300, screen_h - 200))
        view_w = 760 if len(option_layout2) > 1 else 430
        return [[sg.Column(body, scrollable=True, vertical_scroll_only=True,
                           size=(view_w, view_h))],
                [sg.OK(), sg.Cancel()]]

    def configure_role_engine(self, role, eng_id_name):
        """Open the options editor for (role, engine); save deltas vs base."""
        option_list = self.get_engine_options(eng_id_name)
        if not option_list:
            sg.popup('No options available for {}.'.format(eng_id_name),
                     title='Configure', icon=ico_path[platform]['pecg'])
            return
        saved = self.get_role_options(role, eng_id_name)
        col1, col2, opt_meta = self.build_engine_options_layout(
            option_list, current_values=saved)
        layout = self._build_options_window_layout(col1, col2)
        role_label = ROLE_META[role][4] if role in ROLE_META else 'Auto-Analysis'
        title = '{} options - {}'.format(role_label, eng_id_name)
        w = sg.Window(title, layout, icon=ico_path[platform]['pecg'],
                      resizable=True, finalize=True, modal=True)
        while True:
            e, v = w.Read()
            if e in (None, 'Cancel'):
                break
            if e == 'OK':
                # Keep the window open on a bad number.
                if not self.check_spin_options(v, opt_meta, title):
                    continue
                entered = self.read_option_values(v, opt_meta)
                base = {m['name']: m['base'] for m in opt_meta}
                deltas = {n: val for n, val in entered.items()
                          if str(val) != str(base.get(n))}
                self.set_role_options(role, eng_id_name, deltas)
                break
        w.Close()

    def manage_role_engine(self, window, role):
        """Manager dialog for an engine role: select active, configure, delete."""
        id_attr, _, _, icon_key, title = ROLE_META[role]
        role_icon = ico_path[platform].get(icon_key, ico_path[platform]['pecg'])

        def display_list():
            configured = self.role_engine_options.get(role, {})
            return ['{}{}'.format(n, '  (configured)' if n in configured else '')
                    for n in self.engine_id_name_list]

        def to_id(display):
            return display.split('  (configured)')[0] if display else None

        active = getattr(self, id_attr)
        preselect = [d for d in display_list() if to_id(d) == active]
        # Adviser also has an app-level movetime (how long it thinks).
        extra = []
        if role == 'adviser':
            extra = [[sg.Text('Movetime (sec)', size=(14, 1)),
                      sg.Combo(choices_with(TIME_CHOICES_SEC,
                                            self.adviser_movetime_sec),
                               default_value=self.adviser_movetime_sec,
                               readonly=True,
                               size=(8, 1), key='role_movetime_k')]]
        layout = [
            [sg.Text('Active {}:'.format(title), size=(14, 1)),
             sg.Text(active if active else 'None', key='role_active_k',
                     font=('Helvetica', 10, 'bold'), size=(30, 1))],
            [sg.HorizontalSeparator()],
            [sg.Text('Installed engines  (select one, then use a button below)')],
            [sg.Listbox(values=display_list(), size=(46, 10), key='role_list_k',
                        default_values=preselect)],
        ] + extra + [
            [sg.Button('Use Selected', key='role_use_k'),
             sg.Button('Configure', key='role_cfg_k'),
             sg.Button('Delete Config', key='role_del_k'),
             sg.Button('Close')],
        ]
        self.begin_dialog(window)
        w = sg.Window('{} Manager'.format(title), layout,
                      icon=role_icon, finalize=True, modal=True)
        try:
            w['role_list_k'].Widget.bind(
                '<Double-Button-1>',
                lambda e: w.write_event_value('role_use_k', True))
            w['role_list_k'].Widget.bind(
                '<Return>', lambda e: w.write_event_value('role_use_k', True))
        except Exception:
            logging.exception('Failed to bind role list keys.')

        def refresh():
            w['role_list_k'].Update(values=display_list())
            w['role_active_k'].Update(getattr(self, id_attr) or 'None')

        def store_movetime(values):
            if role == 'adviser' and values and 'role_movetime_k' in values:
                self.adviser_movetime_sec = int(values['role_movetime_k'])
                self.save_settings()

        while True:
            e, v = w.Read()
            if e in (None, 'Close'):
                store_movetime(v)
                break
            sel = to_id(v['role_list_k'][0]) if v.get('role_list_k') else None
            if e == 'role_use_k':
                if not sel:
                    sg.popup('Please select an engine.', title=title,
                             icon=role_icon)
                    continue
                store_movetime(v)
                self.set_active_role(role, sel)
                refresh()
            elif e == 'role_cfg_k':
                if not sel:
                    sg.popup('Please select an engine to configure.',
                             title=title, icon=role_icon)
                    continue
                self.configure_role_engine(role, sel)
                try:
                    w.make_modal()
                except Exception:
                    pass
                refresh()
            elif e == 'role_del_k':
                if sel:
                    self.delete_role_options(role, sel)
                    refresh()
        w.Close()
        self.end_dialog(window)
        self.update_labels_and_game_tags(window, human=self.username)

    def update_engine_to_config_file(self, eng_path_file, new_name, old_name, user_opt):
        """
        Update engine config file based on params.

        :param eng_path_file: full path of engine
        :param new_name: new engine id name
        :param new_name: old engine id name
        :param user_opt: a list of dict, i.e d = ['a':a, 'b':b, ...]
        :return:
        """
        folder = Path(eng_path_file)
        folder = folder.parents[0]
        folder = Path(folder)
        folder = folder.as_posix()

        file = PurePath(eng_path_file)
        file = file.name

        with open(self.engine_config_file, 'r') as json_file:
            data = json.load(json_file)

        for p in data:
            command = p['command']
            work_dir = p['workingDirectory']

            if file == command and folder == work_dir and old_name == p['name']:
                p['name'] = new_name
                for k, v in p.items():
                    if k == 'options':
                        for d in v:
                            # d = {'name': 'Ponder', 'default': False,
                            # 'value': False, 'type': 'check'}

                            default_type = type(d['default'])
                            opt_name = d['name']
                            opt_value = d['value']
                            for u in user_opt:
                                # u = {'name': 'CDrill 1400'}
                                for k1, v1 in u.items():
                                    if k1 == opt_name:
                                        v1 = int(v1) if default_type == int else v1
                                        if v1 != opt_value:
                                            d['value'] = v1
                break

        # Save data to pecg_engines.json
        with open(self.engine_config_file, 'w') as h:
            json.dump(data, h, indent=4)

    def is_name_exists(self, name):
        """

        :param name: The name to check in pecg.engines.json file.
        :return:
        """
        with open(self.engine_config_file, 'r') as json_file:
            data = json.load(json_file)

        for p in data:
            jname = p['name']
            if jname == name:
                return True

        return False

    def add_engine_to_config_file(self, engine_path_and_file, pname, que):
        """
        Add pname config in pecg_engines.json file.

        :param engine_path_and_file:
        :param pname: id name of uci engine
        :return:
        """
        # .parent never raises (unlike .parents[0] on an empty or root path),
        # so an unusable path reaches popen_uci below and reports 'Failure'.
        folder = Path(engine_path_and_file).parent
        file = PurePath(engine_path_and_file)
        file = file.name

        option = []

        with open(self.engine_config_file, 'r') as json_file:
            data = json.load(json_file)

        try:
            if sys_os == 'Windows':
                engine = chess.engine.SimpleEngine.popen_uci(
                    engine_path_and_file, cwd=folder,
                    creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                engine = chess.engine.SimpleEngine.popen_uci(
                    engine_path_and_file, cwd=folder)
        except Exception:
            logging.exception(f'Failed to add {pname} in config file.')
            que.put('Failure')
            return

        try:
            opt_dict = engine.options.items()
        except Exception:
            logging.exception('Failed to get engine options.')
            que.put('Failure')
            return

        engine.quit()

        for opt in opt_dict:
            o = opt[1]

            if o.type == 'spin':
                # Adjust hash and threads values
                if o.name.lower() == 'threads':
                    value = 1
                    logging.info(f'config {o.name} is set to {value}')
                elif o.name.lower() == 'hash':
                    value = 32
                    logging.info(f'config {o.name} is set to {value}')
                else:
                    value = o.default

                option.append({'name': o.name,
                               'default': o.default,
                               'value': value,
                               'type': o.type,
                               'min': o.min,
                               'max': o.max})
            elif o.type == 'combo':
                option.append({'name': o.name,
                               'default': o.default,
                               'value': o.default,
                               'type': o.type,
                               'choices': o.var})
            else:
                option.append({'name': o.name,
                               'default': o.default,
                               'value': o.default,
                               'type': o.type})

        # Save engine filename, working dir, name and options
        wdir = Path(folder).as_posix()
        protocol = 'uci'  # Only uci engine is supported so far
        self.engine_id_name_list.append(pname)
        data.append({'command': file, 'workingDirectory': wdir,
                     'name': pname, 'protocol': protocol,
                     'options': option})

        # Save data to pecg_engines.json
        with open(self.engine_config_file, 'w') as h:
            json.dump(data, h, indent=4)

        que.put('Success')

    def check_engine_config_file(self):
        """
        Check presence of engine config file pecg_engines.json. If not
        found we will create it, with entries from engines in Engines folder.

        :return:
        """
        ec = Path(self.engine_config_file)
        if ec.exists():
            return

        data = []
        cwd = Path.cwd()

        self.engine_file_list = self.get_engines()

        for fn in self.engine_file_list:
            # Run engine and get id name and options
            option = []

            # cwd=current working dir, engines=folder, fn=exe file
            epath = Path(cwd, 'Engines', fn)
            engine_path_and_file = str(epath)
            folder = epath.parents[0]

            try:
                if sys_os == 'Windows':
                    engine = chess.engine.SimpleEngine.popen_uci(
                        engine_path_and_file, cwd=folder,
                        creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    engine = chess.engine.SimpleEngine.popen_uci(
                        engine_path_and_file, cwd=folder)
            except Exception:
                logging.exception(f'Failed to start engine {fn}!')
                continue

            engine_id_name = engine.id['name']
            opt_dict = engine.options.items()
            engine.quit()

            for opt in opt_dict:
                o = opt[1]

                if o.type == 'spin':
                    # Adjust hash and threads values
                    if o.name.lower() == 'threads':
                        value = 1
                    elif o.name.lower() == 'hash':
                        value = 32
                    else:
                        value = o.default

                    option.append({'name': o.name,
                                   'default': o.default,
                                   'value': value,
                                   'type': o.type,
                                   'min': o.min,
                                   'max': o.max})
                elif o.type == 'combo':
                    option.append({'name': o.name,
                                   'default': o.default,
                                   'value': o.default,
                                   'type': o.type,
                                   'choices': o.var})
                else:
                    option.append({'name': o.name,
                                   'default': o.default,
                                   'value': o.default,
                                   'type': o.type})

            # Save engine filename, working dir, name and options
            wdir = Path(cwd, 'Engines').as_posix()
            name = engine_id_name
            protocol = 'uci'
            self.engine_id_name_list.append(name)
            data.append({'command': fn, 'workingDirectory': wdir,
                         'name': name, 'protocol': protocol,
                         'options': option})

        # Save data to pecg_engines.json
        with open(self.engine_config_file, 'w') as h:
            json.dump(data, h, indent=4)

    def get_time_mm_ss_ms(self, time_ms):
        """ Returns time in min:sec:millisec given time in millisec """
        s, ms = divmod(int(time_ms), 1000)
        m, s = divmod(s, 60)

        return '{:02d}m:{:02d}s'.format(m, s)

    def get_time_h_mm_ss(self, time_ms, symbol=True):
        """
        Returns time in h:mm:ss format.

        :param time_ms:
        :param symbol:
        :return:
        """
        s, ms = divmod(int(time_ms), 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)

        if not symbol:
            return '{:01d}:{:02d}:{:02d}'.format(h, m, s)
        return '{:01d}h:{:02d}m:{:02d}s'.format(h, m, s)

    def update_text_box(self, window, msg, is_hide):
        """ Update text elements """
        best_move = None
        msg_str = str(msg)

        if 'bestmove ' not in msg_str:
            if 'info_all' in msg_str:
                info_all = ' '.join(msg_str.split()[0:-1]).strip()
                msg_line = '{}\n'.format(info_all)
                window.find_element('search_info_all_k').Update(
                        '' if is_hide else msg_line)
        else:
            # Best move can be None because engine dies
            try:
                best_move = chess.Move.from_uci(msg.split()[1])
            except Exception:
                logging.exception(f'Engine sent {best_move}')
                sg.popup(
                    f'Engine error, it sent a {best_move} bestmove.\n \
                    It is better to change engine {self.opp_id_name}.',
                    icon=ico_path[platform]['pecg'],
                    title=BOX_TITLE
                )

        return best_move

    def get_tag_date(self):
        """ Return date in pgn tag date format """
        return datetime.today().strftime('%Y.%m.%d')

    def init_game(self):
        """ Initialize game with initial pgn tag values """
        self.game = chess.pgn.Game()
        self.node = None
        self.game.headers['Event'] = INIT_PGN_TAG['Event']
        self.game.headers['Date'] = self.get_tag_date()
        self.game.headers['White'] = INIT_PGN_TAG['White']
        self.game.headers['Black'] = INIT_PGN_TAG['Black']

    def set_new_game(self):
        """ Initialize new game but save old pgn tag values"""
        old_event = self.game.headers['Event']
        old_white = self.game.headers['White']
        old_black = self.game.headers['Black']

        # Define a game object for saving game in pgn format
        self.game = chess.pgn.Game()

        self.game.headers['Event'] = old_event
        self.game.headers['Date'] = self.get_tag_date()
        self.game.headers['White'] = old_white
        self.game.headers['Black'] = old_black

    def clear_elements(self, window):
        """ Clear movelist, score, pv, time, depth and nps boxes """
        window.find_element('search_info_all_k').Update('')
        window.find_element('_movelist_').Update(disabled=False)
        window.find_element('_movelist_').Update('', disabled=True)
        window.find_element('polyglot_book1_k').Update('')
        window.find_element('polyglot_book2_k').Update('')
        window.find_element('advise_info_k').Update('')
        window.find_element('comment_k').Update('')
        window.Element('w_base_time_k').Update('')
        window.Element('b_base_time_k').Update('')
        window.Element('w_elapse_k').Update('')
        window.Element('b_elapse_k').Update('')

    def update_labels_and_game_tags(self, window, human='Human'):
        """ Update player names """
        engine_id = self.opp_id_name
        if self.is_user_white:
            window.find_element('_White_').Update(human)
            window.find_element('_Black_').Update(engine_id)
            self.game.headers['White'] = human
            self.game.headers['Black'] = engine_id
        else:
            window.find_element('_White_').Update(engine_id)
            window.find_element('_Black_').Update(human)
            self.game.headers['White'] = engine_id
            self.game.headers['Black'] = human

    def read_fen_board(self):
        """Return a board for the FEN on the clipboard, or None.

        None is returned, after telling the user why, when the clipboard
        does not hold a FEN or the position cannot occur in chess (no king,
        the side that just moved is in check, ...). self.fen is set only on
        success, so a bad paste leaves the current position untouched.
        """
        title = 'Paste FEN'
        try:
            fen = sg.clipboard_get().strip()
            board = chess.Board(fen)
        except Exception:
            logging.exception('Error in parsing FEN from clipboard.')
            sg.popup('The clipboard does not contain a FEN position.',
                     title=title, icon=ico_path[platform]['pecg'])
            return None

        # Sloppy castling or en passant fields are harmless (python-chess
        # ignores what cannot be used); everything else is unplayable.
        tolerated = (chess.STATUS_BAD_CASTLING_RIGHTS
                     | chess.STATUS_INVALID_EP_SQUARE)
        problems = [s.name.replace('_', ' ').lower() for s in chess.Status
                    if s.value and s & board.status() & ~tolerated]
        if problems:
            logging.warning('Pasted FEN %r rejected: %s', fen, problems)
            sg.popup('The FEN on the clipboard is not a legal position '
                     '({}).'.format(', '.join(problems)),
                     title=title, icon=ico_path[platform]['pecg'])
            return None

        self.fen = fen
        return board

    def fen_to_psg_board(self, window):
        """ Update psg_board based on FEN """
        self.board_to_psg_board(chess.BaseBoard(self.fen.split()[0]))
        self.redraw_board(window)

    def board_to_psg_board(self, board):
        """Set psg_board from a python-chess (base) board. No redraw."""
        psgboard = []
        old_r = None

        for s in chess.SQUARES:
            r = chess.square_rank(s)

            if old_r is None:
                piece_r = []
            elif old_r != r:
                psgboard.append(piece_r)
                piece_r = []
            elif s == 63:
                psgboard.append(piece_r)

            try:
                pc = board.piece_at(s ^ 56)
            except Exception:
                pc = None
                logging.exception('Failed to get piece.')

            if pc is not None:
                pt = pc.piece_type
                c = pc.color
                if c:
                    if pt == chess.PAWN:
                        piece_r.append(PAWNW)
                    elif pt == chess.KNIGHT:
                        piece_r.append(KNIGHTW)
                    elif pt == chess.BISHOP:
                        piece_r.append(BISHOPW)
                    elif pt == chess.ROOK:
                        piece_r.append(ROOKW)
                    elif pt == chess.QUEEN:
                        piece_r.append(QUEENW)
                    elif pt == chess.KING:
                        piece_r.append(KINGW)
                else:
                    if pt == chess.PAWN:
                        piece_r.append(PAWNB)
                    elif pt == chess.KNIGHT:
                        piece_r.append(KNIGHTB)
                    elif pt == chess.BISHOP:
                        piece_r.append(BISHOPB)
                    elif pt == chess.ROOK:
                        piece_r.append(ROOKB)
                    elif pt == chess.QUEEN:
                        piece_r.append(QUEENB)
                    elif pt == chess.KING:
                        piece_r.append(KINGB)

            # Else if pc is None or square is empty
            else:
                piece_r.append(BLANK)

            old_r = r

        self.psg_board = psgboard

    def board_graph(self, window):
        """Return the board sg.Graph element of a window, or None."""
        graph = window.AllKeysDict.get('_board_graph_k')
        if graph is None or graph.Widget is None:
            return None
        return graph

    @property
    def board_px(self):
        """Board edge length in px at the current scale."""
        return 8 * self.square_px

    def square_to_xy(self, row, col):
        """Top-left graph coords (== pixels) of a logical square for the
        current orientation."""
        if self.is_white_at_bottom:
            return col * self.square_px, row * self.square_px
        return (7 - col) * self.square_px, (7 - row) * self.square_px

    def xy_to_square(self, x, y):
        """Map graph coords to a logical (row, col), or None if off-board."""
        d_col = int(x) // self.square_px
        d_row = int(y) // self.square_px
        if not (0 <= d_col <= 7 and 0 <= d_row <= 7):
            return None
        if self.is_white_at_bottom:
            return d_row, d_col
        return 7 - d_row, 7 - d_col

    def paint_square(self, graph, row, col, highlight=False):
        """Draw one square (rect, piece, edge coordinate labels) on the
        board canvas, replacing that square's existing figures."""
        old_rect = self._board_square_fig.pop((row, col), None)
        if old_rect is not None:
            graph.delete_figure(old_rect)
        old_piece = self._board_piece_fig.pop((row, col), None)
        if old_piece is not None:
            graph.delete_figure(old_piece)
        for fig in self._board_label_fig.pop((row, col), []):
            graph.delete_figure(fig)

        is_dark = (row + col) % 2
        if highlight:
            color = self.move_sq_dark_color if is_dark \
                else self.move_sq_light_color
        else:
            color = self.sq_dark_color if is_dark else self.sq_light_color
        sq = self.square_px
        x, y = self.square_to_xy(row, col)
        self._board_square_fig[(row, col)] = graph.draw_rectangle(
            (x, y), (x + sq, y + sq),
            fill_color=color, line_color=color)

        piece = self.psg_board[row][col]
        if piece != BLANK:
            self._board_piece_fig[(row, col)] = graph.draw_image(
                location=(x, y), **self.piece_image_source(piece))

        # Board coordinates on the display edges: file letter in the
        # bottom-right corner of the bottom row, rank number in the
        # top-left corner of the left column, in the opposite square color.
        label_color = self.sq_light_color if is_dark else self.sq_dark_color
        coord_font = (FONT_NAME, max(7, round(7 * sq / BASE_SQUARE_PX)),
                      'bold')
        labels = []
        if y == self.board_px - sq:
            labels.append(graph.draw_text(
                'abcdefgh'[col], (x + sq - 3, y + sq - 2),
                color=label_color, font=coord_font,
                text_location=sg.TEXT_LOCATION_BOTTOM_RIGHT))
        if x == 0:
            labels.append(graph.draw_text(
                str(8 - row), (x + 3, y + 2),
                color=label_color, font=coord_font,
                text_location=sg.TEXT_LOCATION_TOP_LEFT))
        if labels:
            self._board_label_fig[(row, col)] = labels

    def change_square_color(self, window, row, col):
        """Highlight a square (selected piece or move from/to square)."""
        graph = self.board_graph(window)
        if graph is not None:
            self.paint_square(graph, row, col, highlight=True)

    def restore_square_color(self, window, row, col):
        """Repaint a square in its normal color (clears a highlight)."""
        graph = self.board_graph(window)
        if graph is not None:
            self.paint_square(graph, row, col, highlight=False)

    def relative_row(self, s, stm):
        """
        The board can be viewed, as white at the bottom and black at the
        top. If stm is white the row 0 is at the bottom. If stm is black
        row 0 is at the top.
        :param s: square
        :param stm: side to move
        :return: relative row
        """
        return 7 - self.get_row(s) if stm else self.get_row(s)

    def get_row(self, s):
        """
        This row is based on PySimpleGUI square mapping that is 0 at the
        top and 7 at the bottom.
        In contrast Python-chess square mapping is 0 at the bottom and 7
        at the top. chess.square_rank() is a method from Python-chess that
        returns row given square s.

        :param s: square
        :return: row
        """
        return 7 - chess.square_rank(s)

    def get_col(self, s):
        """ Returns col given square s """
        return chess.square_file(s)

    def redraw_board(self, window):
        """Redraw the whole board on the Graph canvas from psg_board.

        Orientation (is_white_at_bottom) is applied here at draw time, so
        flipping the board is just another redraw - no window rebuild.
        """
        graph = self.board_graph(window)
        if graph is None:
            return
        graph.erase()
        self._board_square_fig = {}
        self._board_piece_fig = {}
        self._board_label_fig = {}
        self._turn_marker_fig = []
        for i in range(8):
            for j in range(8):
                self.paint_square(graph, i, j)
        self.draw_turn_marker(graph)

    def draw_turn_marker(self, graph):
        """Draw the two turn dots in the strip right of the board.

        One dot sits level with each player's back rank (beside h1 and h8
        with White at the bottom; the other way round when flipped). The
        dot of the side to move is filled green, the other is a grey ring.
        """
        for fig in self._turn_marker_fig:
            graph.delete_figure(fig)
        self._turn_marker_fig = []
        if self.side_to_move is None:
            return
        sq = self.square_px
        x = self.board_px + TURN_MARKER_PX // 2
        radius = TURN_MARKER_PX // 2 - 3
        for is_white in (True, False):
            at_bottom = (is_white == self.is_white_at_bottom)
            y = 7 * sq + sq // 2 if at_bottom else sq // 2
            if is_white == self.side_to_move:
                fig = graph.draw_circle((x, y), radius,
                                        fill_color=TURN_MARKER_ON,
                                        line_color=TURN_MARKER_ON)
            else:
                fig = graph.draw_circle((x, y), radius,
                                        line_color=TURN_MARKER_OFF,
                                        line_width=2)
            self._turn_marker_fig.append(fig)

    def update_turn_marker(self, window, board):
        """Show whose turn it is in ``board`` with the turn marker."""
        self.side_to_move = board.turn
        graph = self.board_graph(window)
        if graph is not None:
            self.draw_turn_marker(graph)

    def piece_image_source(self, piece):
        """draw_image kwargs for a piece at the current board size.

        Every board size has its own folder of ready-made images,
        Images/<square size>. If a file is missing there, the original
        60px image is used (the piece then sits off-center, but the app
        keeps working).
        """
        cache = self._piece_image_cache.setdefault(self.square_px, {})
        filename = cache.get(piece)
        if filename is None:
            filename = os.path.join(IMAGE_DIR, str(self.square_px),
                                    os.path.basename(images[piece]))
            if not os.path.isfile(filename):
                logging.warning('Missing piece image %s', filename)
                filename = images[piece]
            cache[piece] = filename
        return {'filename': filename}

    def _apply_board_scale(self, window):
        """Sync the window's board canvas to the current square_px.

        Also used when returning to a window that was hidden while the
        scale changed elsewhere (Play <-> Review), whose canvas is stale.
        """
        graph = self.board_graph(window)
        if graph is None:
            return
        # Keep graph coords == pixels: the widget size and the Graph
        # element's coordinate system must be updated together, otherwise
        # _convert_canvas_xy_to_xy would scale mouse coords wrongly.
        width = self.board_px + TURN_MARKER_PX
        graph.Widget.config(width=width, height=self.board_px)
        graph.CanvasSize = (width, self.board_px)
        graph.BottomLeft = (0, self.board_px)
        graph.TopRight = (width, 0)
        self.redraw_board(window)

    def _is_window_maximized(self, window):
        """True if the window is maximized ('zoomed' on Windows/some WMs,
        the '-zoomed' attribute elsewhere on Linux)."""
        try:
            if window.TKroot.state() == 'zoomed':
                return True
        except Exception:
            pass
        try:
            return bool(window.TKroot.wm_attributes('-zoomed'))
        except Exception:
            return False

    def _set_window_maximized(self, window):
        """Maximize the window (best effort across platforms)."""
        try:
            window.TKroot.state('zoomed')
            return
        except Exception:
            pass
        try:
            window.TKroot.wm_attributes('-zoomed', 1)
        except Exception:
            logging.exception('Failed to maximize the window.')

    def handle_board_size_event(self, window, button):
        """Apply a Board -> Size menu selection ('<label>::board_size_k'),
        or pass a View menu selection on to handle_layout_event()."""
        if '::layout_k' in str(button):
            self.handle_layout_event(window, button)
            return
        label = str(button).split('::')[0]
        square_px = BOARD_SIZE_LABELS.get(label)
        if not square_px:
            return
        self.set_board_square(window, square_px)

    def auto_fit_board_size(self):
        """Pick the largest board scale that fits the screen (first start
        only; afterwards the persisted size wins)."""
        try:
            screen_w, screen_h = sg.Window.get_screen_size()
        except Exception:
            logging.exception('Failed to read the screen size.')
            return
        # Reserve room for the side panel (width) and for the title bar,
        # menubar, status bar and taskbar (height).
        avail = min(screen_w - 560, screen_h - 200)
        self.square_px = fit_square_px(avail // 8)

    def setup_board_drag_drop(self, window):
        """Bind mouse input on the board canvas.

        Emits the same events the play loop always consumed: a (row, col)
        tuple event for a click and '__drag_move__' with (from_sq, to_sq)
        for a completed drag, via window.write_event_value.
        """
        self._drag_window = window
        self._drag_source = None
        self._drag_piece = None
        self._drag_started = False
        self._drag_fig = None
        graph = self.board_graph(window)
        if graph is None:
            return
        graph.Widget.bind('<ButtonPress-1>', self._on_board_press, add='+')
        graph.Widget.bind('<B1-Motion>', self._on_board_motion, add='+')
        graph.Widget.bind('<ButtonRelease-1>', self._on_board_release, add='+')

    def _on_board_press(self, event):
        """Record the source square (and its piece) on mouse press."""
        self._drag_started = False
        self._drag_fig = None
        graph = self.board_graph(self._drag_window)
        if graph is None:
            self._drag_source = None
            self._drag_piece = None
            return
        x, y = graph._convert_canvas_xy_to_xy(event.x, event.y)
        self._drag_source = self.xy_to_square(x, y)
        if self._drag_source is not None:
            row, col = self._drag_source
            self._drag_piece = self.psg_board[row][col]
        else:
            self._drag_piece = None

    def _on_board_motion(self, event):
        """Float the dragged piece under the cursor.

        The floating piece is created lazily on the first motion, so a
        plain click shows nothing. Only the source square's piece figure
        is lifted; ``self.psg_board`` (the move data) is left untouched so
        move validation stays correct.
        """
        if self._drag_source is None or self._drag_piece in (None, BLANK):
            return
        graph = self.board_graph(self._drag_window)
        if graph is None:
            return
        x, y = graph._convert_canvas_xy_to_xy(event.x, event.y)
        half = self.square_px // 2
        if not self._drag_started:
            self._drag_started = True
            # Lift the piece off its source square (display only).
            fig = self._board_piece_fig.pop(self._drag_source, None)
            if fig is not None:
                graph.delete_figure(fig)
            self._drag_fig = graph.draw_image(
                location=(x - half, y - half),
                **self.piece_image_source(self._drag_piece))
            graph.bring_figure_to_front(self._drag_fig)
        elif self._drag_fig is not None:
            graph.relocate_figure(self._drag_fig, x - half, y - half)

    def _on_board_release(self, event):
        """Emit a click or drag-move event on mouse release.

        Release on the press square (with or without a small drag) is a
        click and emits that square's (row, col) tuple event; a drag
        released on another square emits '__drag_move__'. The play loop
        consumes both exactly as it did with the old button board.
        """
        source = self._drag_source
        started = self._drag_started
        drag_fig = self._drag_fig
        self._drag_source = None
        self._drag_piece = None
        self._drag_started = False
        self._drag_fig = None

        graph = self.board_graph(self._drag_window)
        if graph is None:
            return
        if drag_fig is not None:
            graph.delete_figure(drag_fig)
        if source is None:
            return
        if started:
            # Put the lifted piece back; a legal move repaints right after
            # via the __drag_move__ handler, an illegal or cancelled drag
            # keeps the piece on its origin square.
            self.paint_square(graph, source[0], source[1])

        x, y = graph._convert_canvas_xy_to_xy(event.x, event.y)
        target = self.xy_to_square(x, y)
        if target is None:
            return
        if target == source:
            self._drag_window.write_event_value(source, True)
        elif started:
            self._drag_window.write_event_value(
                '__drag_move__', (source, target))

    def render_square(self, image, key, location):
        """ Returns an RButton (Read Button) with image image """
        if (location[0] + location[1]) % 2:
            color = self.sq_dark_color  # Dark square
        else:
            color = self.sq_light_color
        return sg.RButton('', image_filename=image, size=(1, 1),
                          border_width=0, button_color=('white', color),
                          pad=(0, 0), key=key)

    def select_promotion_piece(self, stm):
        """
        Allow user to select a piece type to promote to.

        :param stm: side to move
        :return: promoted piece, i.e QUEENW, QUEENB ...
        """
        piece = None
        board_layout, row = [], []

        psg_promote_board = copy.deepcopy(white_init_promote_board) if stm else copy.deepcopy(black_init_promote_board)

        # Loop through board and create buttons with images.
        for i in range(1):
            for j in range(4):
                piece_image = images[psg_promote_board[i][j]]
                row.append(self.render_square(piece_image, key=(i, j),
                                              location=(i, j)))

            board_layout.append(row)

        promo_window = sg.Window('{} {}'.format(APP_NAME, APP_VERSION),
                                 board_layout,
                                 default_button_element_size=(12, 1),
                                 auto_size_buttons=False,
                                 icon=ico_path[platform]['pecg'])

        while True:
            button, value = promo_window.Read(timeout=0)
            if button is None:
                break
            if type(button) is tuple:
                move_from = button
                fr_row, fr_col = move_from
                piece = psg_promote_board[fr_row][fr_col]
                logging.info(f'promote piece: {piece}')
                break

        promo_window.Close()

        return piece

    def update_rook(self, window, move):
        """
        Update rook location for castle move.

        :param window:
        :param move: uci move format
        :return:
        """
        if move == 'e1g1':
            fr = chess.H1
            to = chess.F1
            pc = ROOKW
        elif move == 'e1c1':
            fr = chess.A1
            to = chess.D1
            pc = ROOKW
        elif move == 'e8g8':
            fr = chess.H8
            to = chess.F8
            pc = ROOKB
        elif move == 'e8c8':
            fr = chess.A8
            to = chess.D8
            pc = ROOKB

        self.psg_board[self.get_row(fr)][self.get_col(fr)] = BLANK
        self.psg_board[self.get_row(to)][self.get_col(to)] = pc
        self.redraw_board(window)

    def update_ep(self, window, move, stm):
        """
        Update board for e.p move.

        :param window:
        :param move: python-chess format
        :param stm: side to move
        :return:
        """
        to = move.to_square
        if stm:
            capture_sq = to - 8
        else:
            capture_sq = to + 8

        self.psg_board[self.get_row(capture_sq)][self.get_col(capture_sq)] = BLANK
        self.redraw_board(window)

    def get_promo_piece(self, move, stm, human):
        """
        Returns promotion piece.

        :param move: python-chess format
        :param stm: side to move
        :param human: if side to move is human this is True
        :return: promoted piece in python-chess and pythonsimplegui formats
        """
        # If this move is from a user, we will show a window with piece images
        if human:
            psg_promo = self.select_promotion_piece(stm)

            # If user pressed x we set the promo to queen
            if psg_promo is None:
                logging.info('User did not select a promotion piece, set this to queen.')
                psg_promo = QUEENW if stm else QUEENB

            pyc_promo = promote_psg_to_pyc[psg_promo]
        # Else if move is from computer
        else:
            pyc_promo = move.promotion  # This is from python-chess
            if stm:
                if pyc_promo == chess.QUEEN:
                    psg_promo = QUEENW
                elif pyc_promo == chess.ROOK:
                    psg_promo = ROOKW
                elif pyc_promo == chess.BISHOP:
                    psg_promo = BISHOPW
                elif pyc_promo == chess.KNIGHT:
                    psg_promo = KNIGHTW
            else:
                if pyc_promo == chess.QUEEN:
                    psg_promo = QUEENB
                elif pyc_promo == chess.ROOK:
                    psg_promo = ROOKB
                elif pyc_promo == chess.BISHOP:
                    psg_promo = BISHOPB
                elif pyc_promo == chess.KNIGHT:
                    psg_promo = KNIGHTB

        return pyc_promo, psg_promo

    def set_depth_limit(self, window):
        """Let the user pick the depth limit of the playing and adviser
        engines from a list."""
        # MAX_DEPTH means the search is not depth-limited (see RunEngine).
        current = DEPTH_NO_LIMIT if self.max_depth >= MAX_DEPTH \
            else self.max_depth
        depths = choices_with(range(MIN_DEPTH, DEPTH_CHOICE_MAX + 1),
                              MIN_DEPTH if current == DEPTH_NO_LIMIT
                              else current)
        layout = [
            [sg.Text('Depth', size=(8, 1)),
             sg.Combo([DEPTH_NO_LIMIT] + depths, default_value=current,
                      readonly=True, size=(10, 1), key='depth_k')],
            [sg.OK(), sg.Cancel()]
        ]

        self.begin_dialog(window)
        w = sg.Window('Engine/Set Depth', layout,
                      icon=ico_path[platform]['pecg'], modal=True)
        e, v = w.Read()
        w.Close()
        self.end_dialog(window)

        if e == 'OK':
            self.max_depth = MAX_DEPTH if v['depth_k'] == DEPTH_NO_LIMIT \
                else int(v['depth_k'])

    def show_help_topic(self, menu_event):
        """Show a brief help popup for a Help-menu selection.

        ``menu_event`` is the full menu event string, e.g.
        'Set Opponent::help_eng_opponent'. The Online Help and About items are
        routed to their handlers; every other key shows a short popup from
        HELP_TOPICS.
        """
        key = menu_event.split('::')[-1]
        if key == 'help_online':
            self.open_online_help()
            return
        if key == 'help_about':
            self.show_about()
            return
        title, body = HELP_TOPICS.get(
            key, ('Help', 'See the README on the project page for the '
                          'full manual.'))
        sg.popup_scrolled(body, title='Help - {}'.format(title),
                          size=(64, 16), icon=ico_path[platform]['pecg'])

    def show_about(self):
        """Show the About dialog."""
        msg = ('{} {}\n\n'
               'A chess GUI built with FreeSimpleGUI and python-chess.\n'
               'Install any UCI engine to play, analyse and review games.\n\n'
               'Project:  {}\n'
               'License:  LGPL-3.0 (see the bundled LICENSE file).').format(
                   APP_NAME, APP_VERSION, ONLINE_HELP_URL)
        sg.popup(msg, title='About {}'.format(APP_NAME),
                 icon=ico_path[platform]['pecg'])

    def open_online_help(self):
        """Open the detailed online help (README) in the default browser."""
        try:
            webbrowser.open(ONLINE_HELP_URL, new=2)
        except Exception:
            logging.exception('Failed to open online help.')
            sg.popup('Visit:\n{}'.format(ONLINE_HELP_URL),
                     title='Online Help', icon=ico_path[platform]['pecg'])

    def define_timer(self, window, name='human'):
        """
        Returns Timer object for either human or engine.
        """
        if name == 'human':
            timer = Timer(
                self.human_tc_type, self.human_base_time_ms,
                self.human_inc_time_ms, self.human_period_moves
            )
        else:
            timer = Timer(
                self.engine_tc_type, self.engine_base_time_ms,
                self.engine_inc_time_ms, self.engine_period_moves
            )

        elapse_str = self.get_time_h_mm_ss(timer.base)
        is_white_base = (self.is_user_white and name == 'human') or (not self.is_user_white and name != 'human')
        window.Element('w_base_time_k' if is_white_base else 'b_base_time_k').Update(elapse_str)

        return timer

    def set_menu_state(self, window, in_game):
        """Swap the menubar between the idle and in-game states."""
        self.current_menu_def = build_play_menu(in_game)
        self.menu_elem.Update(self.current_menu_def)
        self.apply_menu_font(window)

    def set_review_menu_state(self, window, analyzing):
        """Swap the Review menubar between the idle and analyzing states."""
        self.review_menu_elem.Update(build_review_menu(analyzing))
        self.apply_menu_font(window)

    def flip_play_window(self, window, board):
        """Flip the board orientation during Play.

        The board is drawn on a canvas with orientation applied at draw
        time, so flipping is just a redraw of the same window; the game,
        clocks, move list and a thinking engine are untouched.

        :return: the same window (kept for call-site symmetry).
        """
        self.is_white_at_bottom = not self.is_white_at_bottom
        self.board_to_psg_board(board)
        self.redraw_board(window)
        return window

    def play_game(self, window: sg.Window, board: chess.Board):
        """Play a game against an engine.

        The window also idles here between games: setup menu events are
        delegated to handle_setup_event() until the game starts (first user
        move or Engine->Go).

        Args:
          window: A PySimplegUI window.
          board: current board position

        Returns:
          (is_new_game, window) - the window may have been rebuilt by a
          board flip, color or theme change.
        """
        window.find_element('_movelist_').Update(disabled=False)
        window.find_element('_movelist_').Update('', disabled=True)

        is_human_stm = True if self.is_user_white else False

        move_state = 0
        move_from, move_to = None, None
        is_new_game, is_exit_app = False, False

        # Do not play immediately when stm is computer
        is_engine_ready = True if is_human_stm else False

        # The game starts at the first user move or Engine->Go; setup menus
        # stay enabled and the clocks do not tick until then.
        is_game_started = False

        # For saving game
        move_cnt = 0

        is_user_resigns = False
        is_user_wins = False
        is_user_draws = False
        is_user_time_forfeit = False
        is_search_stop_for_exit = False
        is_search_stop_for_new_game = False
        is_search_stop_for_resign = False
        is_search_stop_for_user_wins = False
        is_search_stop_for_user_draws = False

        # Engine instance that persists across moves
        persistent_engine = None
        is_hide_book1 = True
        is_hide_book2 = True
        is_hide_search_info = True

        # Init timer. The clocks only start ticking once the game starts;
        # the timers are re-created when an idle setup event may have
        # changed the time control or the user's color.
        human_timer = self.define_timer(window)
        engine_timer = self.define_timer(window, 'engine')

        # Game loop
        while not board.is_game_over(claim_draw=True):
            moved_piece = None

            # Mode: Play, Hide book 1
            if is_hide_book1:
                window.Element('polyglot_book1_k').Update('')
            else:
                # Load 2 polyglot book files.
                ref_book1 = GuiBook(self.computer_book_file, board,
                                    self.is_random_book)
                all_moves, is_found = ref_book1.get_all_moves()
                if is_found:
                    window.Element('polyglot_book1_k').Update(all_moves)
                else:
                    window.Element('polyglot_book1_k').Update('no book moves')

            # Mode: Play, Hide book 2
            if is_hide_book2:
                window.Element('polyglot_book2_k').Update('')
            else:
                ref_book2 = GuiBook(self.human_book_file, board,
                                    self.is_random_book)
                all_moves, is_found = ref_book2.get_all_moves()
                if is_found:
                    window.Element('polyglot_book2_k').Update(all_moves)
                else:
                    window.Element('polyglot_book2_k').Update('no book moves')

            # Mode: Play, Stm: computer (first move), Allow user to change settings.
            # User can start the engine by Engine->Go.
            if not is_engine_ready:
                window.find_element('_gamestatus_').Update(
                        'Mode     Play, press Engine->Go')
                while True:
                    button, value = window.Read(timeout=100)

                    # Mode: Play, Stm: computer (first move)
                    if button == 'New::new_game_k':
                        is_new_game = True
                        break

                    if isinstance(button, str) and '::help_' in button:
                        self.show_help_topic(button)
                        continue

                    if button == 'Flip':
                        window = self.flip_play_window(window, board)
                        continue

                    if isinstance(button, str) and (
                            '::board_size_k' in button
                            or '::layout_k' in button):
                        self.handle_board_size_event(window, button)
                        continue

                    if button == 'Paste FEN':
                        # A bad paste shows a message and changes nothing.
                        pasted_board = self.read_fen_board()
                        if pasted_board is None:
                            continue
                        board = pasted_board
                        self.set_new_game()

                        self.fen_to_psg_board(window)
                        self.update_turn_marker(window, board)

                        # The human plays their color, the engine the other;
                        # wait for Engine->Go when it is the engine's turn.
                        is_human_stm = (board.turn == self.is_user_white)
                        is_engine_ready = True if is_human_stm else False

                        window.find_element('_gamestatus_').Update(
                            'Mode     Play' if is_human_stm else
                            'Mode     Play, press Engine->Go')

                        self.game.headers['FEN'] = self.fen
                        break

                    if button == 'Go':
                        if self.opp_path_and_file is None:
                            sg.popup(
                                'Install engine first! in Engine/Manage/Install',
                                icon=ico_path[platform]['pecg'],
                                title='Mode Play')
                            continue
                        is_engine_ready = True
                        if not is_game_started:
                            is_game_started = True
                            human_timer = self.define_timer(window)
                            engine_timer = self.define_timer(window, 'engine')
                            self.set_menu_state(window, True)
                        break

                    if button is None:
                        logging.info('Quit app X is pressed.')
                        is_exit_app = True
                        break

                    # Mode: Play, idle setup (game not started): engine, time,
                    # book, user, settings, color and theme dialogs plus
                    # Review mode entry.
                    if (not is_game_started and isinstance(button, str)
                            and button != sg.TIMEOUT_KEY):
                        if button == 'Review':
                            self.start_review_mode(window)
                            # A flip done inside Review persists; the redraw
                            # below repaints in the current orientation.
                            self.board_to_psg_board(board)
                            self.redraw_board(window)
                            self.update_turn_marker(window, board)
                            human_timer = self.define_timer(window)
                            engine_timer = self.define_timer(window, 'engine')
                            window.find_element('_gamestatus_').Update(
                                'Mode     Play, press Engine->Go')
                            continue
                        is_handled, window = self.handle_setup_event(
                            button, window)
                        if is_handled:
                            # The window may have been rebuilt (theme/colors):
                            # restore the position display and re-map clocks.
                            self.board_to_psg_board(board)
                            self.redraw_board(window)
                            self.update_turn_marker(window, board)
                            human_timer = self.define_timer(window)
                            engine_timer = self.define_timer(window, 'engine')
                            window.find_element('_gamestatus_').Update(
                                'Mode     Play, press Engine->Go')
                            continue

                if is_exit_app or is_new_game:
                    break

            # If side to move is human
            if is_human_stm:
                move_state = 0

                while True:
                    button, value = window.Read(timeout=100)

                    # The user has just moved: leave before touching the
                    # clock, or it would start again on the engine's turn.
                    if not is_human_stm:
                        break

                    # The clock only runs once the game has started.
                    if is_game_started:
                        # The turn is timed in real time from its first
                        # pass here; start() does nothing on later passes.
                        human_timer.start()

                        # Update elapse box in m:s format
                        elapse_str = self.get_time_mm_ss_ms(human_timer.tick())
                        k = 'w_elapse_k'
                        if not self.is_user_white:
                            k = 'b_elapse_k'
                        window.Element(k).Update(elapse_str)

                        # Check if human has run out of time
                        if (self.is_time_forfeit_enabled and
                                human_timer.elapse >= human_timer.base):
                            color = 'white' if self.is_user_white else 'black'
                            sg.popup(
                                '{} loses on time!'.format(color.capitalize()),
                                title=BOX_TITLE,
                                icon=ico_path[platform]['pecg'])
                            is_user_time_forfeit = True
                            break

                    # Mode: Play, Stm: User, Run adviser engine
                    if button == 'Start::right_adviser_k':
                        if self.adviser_path_and_file is None:
                            sg.popup(
                                'Set an engine adviser first!\n'
                                'Engine -> Set Engine Adviser',
                                icon=ico_path[platform]['pecg'],
                                title='Adviser')
                            break
                        self.adviser_threads = self.get_engine_threads(
                            self.adviser_id_name)
                        self.adviser_hash = self.get_engine_hash(
                            self.adviser_id_name)
                        adviser_base_ms = self.adviser_movetime_sec * 1000
                        adviser_inc_ms = 0

                        search = RunEngine(
                            self.queue, self.engine_config_file,
                            self.adviser_path_and_file, self.adviser_id_name,
                            self.max_depth, adviser_base_ms, adviser_inc_ms,
                            tc_type='timepermove',
                            period_moves=0,
                            is_stream_search_info=True,
                            option_overrides=self.get_role_options(
                                'adviser', self.adviser_id_name)
                        )
                        search.get_board(board)
                        search.daemon = True
                        search.start()
                        adviser_line = None

                        while True:
                            button, value = window.Read(timeout=10)

                            # The user's clock keeps running (and showing)
                            # while the adviser is thinking.
                            if is_game_started and button is not None:
                                window.Element(k).Update(
                                    self.get_time_mm_ss_ms(human_timer.tick()))

                            if button == 'Stop::right_adviser_k':
                                search.stop()

                            # Exit app while adviser is thinking.
                            if button is None:
                                search.stop()
                                is_search_stop_for_exit = True
                            try:
                                msg = self.queue.get_nowait()
                                if 'info_all' in msg:
                                    # Extract PV moves: format is
                                    # "{score} | {depth} | {time}s | {moves} info_all"
                                    parts = msg.split('|')
                                    if len(parts) >= 4:
                                        pv_part = parts[-1].strip()
                                        # Remove trailing info_all tag
                                        pv_moves = pv_part.replace('info_all', '').strip()
                                    else:
                                        pv_moves = msg.replace('info_all', '').strip()
                                    # Limit to 5 moves
                                    move_list = pv_moves.split()
                                    adviser_line = ' '.join(move_list[:5])
                                    window.Element('advise_info_k').Update(adviser_line)
                            except queue.Empty:
                                continue
                            except Exception:
                                logging.exception(
                                    'Unexpected error reading adviser queue')
                                continue

                            if 'bestmove' in msg:
                                if adviser_line:
                                    adviser_line += ' ... ' + self.adviser_id_name
                                else:
                                    bestmove_parts = msg.split(maxsplit=1)
                                    if len(bestmove_parts) > 1:
                                        bestmove = bestmove_parts[1]
                                    else:
                                        bestmove = '(none)'
                                    adviser_line = \
                                        f'{bestmove} ... {self.adviser_id_name}'
                                window.Element('advise_info_k').Update(adviser_line)
                                break

                        search.join()
                        search.quit_engine()
                        break

                    # Mode: Play, Stm: user
                    if button == 'Show::right_search_info_k':
                        is_hide_search_info = False
                        break

                    # Mode: Play, Stm: user
                    if button == 'Hide::right_search_info_k':
                        is_hide_search_info = True
                        window.Element('search_info_all_k').Update('')
                        break

                    # Mode: Play, Stm: user
                    if button == 'Show::right_book1_k':
                        is_hide_book1 = False
                        break

                    # Mode: Play, Stm: user
                    if button == 'Hide::right_book1_k':
                        is_hide_book1 = True
                        break

                    # Mode: Play, Stm: user
                    if button == 'Show::right_book2_k':
                        is_hide_book2 = False
                        break

                    # Mode: Play, Stm: user
                    if button == 'Hide::right_book2_k':
                        is_hide_book2 = True
                        break

                    if button is None:
                        logging.info('Quit app X is pressed.')
                        is_exit_app = True
                        break

                    if is_search_stop_for_exit:
                        is_exit_app = True
                        logging.warning('Search is stopped for exit.')
                        break

                    # Mode: Play, Stm: User
                    if button == 'New::new_game_k' or is_search_stop_for_new_game:
                        is_new_game = True
                        self.clear_elements(window)
                        break

                    if button == 'Save to My Games::save_game_k':
                        logging.info('Saving game manually')
                        self.save_game_as(self.my_games, 'My Games')
                        break

                    # Mode: Play, Stm: user
                    if button == 'Save to White Repertoire':
                        self.save_game_as(self.repertoire_file['white'],
                                          'White Repertoire')
                        break

                    # Mode: Play, Stm: user
                    if button == 'Save to Black Repertoire':
                        self.save_game_as(self.repertoire_file['black'],
                                          'Black Repertoire')
                        break

                    # Mode: Play, stm: User
                    if button == 'Resign::resign_game_k' or is_search_stop_for_resign:
                        logging.info('User resigns')

                        # Verify resign
                        reply = sg.popup('Do you really want to resign?',
                                         button_type=sg.POPUP_BUTTONS_YES_NO,
                                         title=BOX_TITLE,
                                         icon=ico_path[platform]['pecg'])
                        if reply == 'Yes':
                            is_user_resigns = True
                            break
                        else:
                            if is_search_stop_for_resign:
                                is_search_stop_for_resign = False
                            continue

                    # Mode: Play, stm: User
                    if button == 'User Wins::user_wins_k' or is_search_stop_for_user_wins:
                        logging.info('User wins by adjudication')
                        is_user_wins = True
                        break

                    # Mode: Play, stm: User
                    if button == 'User Draws::user_draws_k' or is_search_stop_for_user_draws:
                        logging.info('User draws by adjudication')
                        is_user_draws = True
                        break

                    # Mode: Play, stm: User
                    if isinstance(button, str) and '::help_' in button:
                        self.show_help_topic(button)
                        break

                    # Mode: Play, stm: User, flip the board view anytime
                    if button == 'Flip':
                        window = self.flip_play_window(window, board)
                        break

                    if isinstance(button, str) and (
                            '::board_size_k' in button
                            or '::layout_k' in button):
                        self.handle_board_size_event(window, button)
                        break

                    # Mode: Play, stm: User. Engine->Go before the first move:
                    # the engine takes the side to move and the user plays the
                    # other color (the way to play as black).
                    if button == 'Go':
                        if is_game_started or len(self.game.variations):
                            # Only for starting the engine before the first
                            # move; disabled in the in-game menu.
                            continue
                        if self.opp_path_and_file is None:
                            sg.popup(
                                'Install engine first! in Engine/Manage/Install',
                                icon=ico_path[platform]['pecg'],
                                title='Mode Play')
                            continue
                        self.is_user_white = not board.turn
                        self.update_labels_and_game_tags(
                            window, human=self.username)
                        # Put the user's color at the bottom (they can still
                        # flip back at any time).
                        if self.is_white_at_bottom != self.is_user_white:
                            window = self.flip_play_window(window, board)
                        is_human_stm = False
                        is_engine_ready = True
                        is_game_started = True
                        # Re-map the clock labels to the swapped colors.
                        human_timer = self.define_timer(window)
                        engine_timer = self.define_timer(window, 'engine')
                        self.set_menu_state(window, True)
                        window.find_element('_gamestatus_').Update(
                                'Mode     Play, Engine is thinking ...')
                        break

                    # Mode: Play, stm: User
                    if button == 'Paste FEN':
                        # Pasting fen is only allowed before the game starts.
                        if len(self.game.variations):
                            sg.popup('Press Game->New then paste your fen.',
                                     title='Mode Play')
                            continue
                        # A bad paste shows a message and changes nothing.
                        pasted_board = self.read_fen_board()
                        if pasted_board is None:
                            continue
                        board = pasted_board
                        self.set_new_game()

                        self.fen_to_psg_board(window)
                        self.update_turn_marker(window, board)

                        # The human plays their color, the engine the other;
                        # wait for Engine->Go when it is the engine's turn.
                        is_human_stm = (board.turn == self.is_user_white)
                        is_engine_ready = True if is_human_stm else False

                        window.find_element('_gamestatus_').Update(
                                'Mode     Play, side: {}'.format(
                                        'white' if board.turn else 'black'))

                        self.game.headers['FEN'] = self.fen
                        break

                    # Mode: Play, stm: User, idle setup (game not started):
                    # engine, time, book, user, settings, color and theme
                    # dialogs plus Review mode entry.
                    if (not is_game_started and isinstance(button, str)
                            and button != sg.TIMEOUT_KEY):
                        if button == 'Review':
                            self.start_review_mode(window)
                            # A flip done inside Review persists; the redraw
                            # below repaints in the current orientation.
                            self.board_to_psg_board(board)
                            self.redraw_board(window)
                            self.update_turn_marker(window, board)
                            human_timer = self.define_timer(window)
                            engine_timer = self.define_timer(window, 'engine')
                            window.find_element('_gamestatus_').Update(
                                'Mode     Play')
                            break
                        is_handled, window = self.handle_setup_event(
                            button, window)
                        if is_handled:
                            # The window may have been rebuilt (theme/colors):
                            # restore the position display and re-map clocks.
                            self.board_to_psg_board(board)
                            self.redraw_board(window)
                            self.update_turn_marker(window, board)
                            human_timer = self.define_timer(window)
                            engine_timer = self.define_timer(window, 'engine')
                            window.find_element('_gamestatus_').Update(
                                'Mode     Play')
                            break

                    # Moves are not allowed until an engine opponent is set.
                    if (button == '__drag_move__' or type(button) is tuple) \
                            and self.opp_path_and_file is None:
                        sg.popup(
                            'Install engine first! in Engine/Manage/Install',
                            icon=ico_path[platform]['pecg'],
                            title='Mode Play')
                        continue

                    # Mode: Play, stm: User, handle drag-and-drop move
                    if button == '__drag_move__':
                        drag_from, drag_to = value['__drag_move__']
                        d_fr_row, d_fr_col = drag_from
                        d_piece = self.psg_board[d_fr_row][d_fr_col]
                        d_moved_piece = board.piece_type_at(
                            chess.square(d_fr_col, 7 - d_fr_row))

                        if d_piece != BLANK and d_moved_piece is not None:
                            # If a click-based move was in progress, restore
                            # the color of the previously selected square
                            if move_state == 1:
                                self.restore_square_color(
                                    window, move_from[0], move_from[1])

                            # Set up state as if source square was clicked
                            move_from = drag_from
                            fr_row, fr_col = d_fr_row, d_fr_col
                            piece = d_piece
                            moved_piece = d_moved_piece
                            self.change_square_color(window, fr_row, fr_col)
                            move_state = 1

                            # Re-assign button to destination so existing
                            # move_state==1 code below handles execution
                            button = drag_to
                        else:
                            logging.debug(
                                'Drag from empty or inconsistent square '
                                '(%d, %d): psg_board=%s, piece_type=%s',
                                d_fr_row, d_fr_col, d_piece, d_moved_piece)

                    # Mode: Play, stm: User, user starts moving
                    if type(button) is tuple:
                        # If fr_sq button is pressed
                        if move_state == 0:
                            move_from = button
                            fr_row, fr_col = move_from
                            piece = self.psg_board[fr_row][fr_col]  # get the move-from piece

                            # Change the color of the "fr" board square
                            self.change_square_color(window, fr_row, fr_col)

                            move_state = 1
                            moved_piece = board.piece_type_at(chess.square(fr_col, 7-fr_row))  # Pawn=1

                        # Else if to_sq button is pressed
                        elif move_state == 1:
                            is_promote = False
                            move_to = button
                            to_row, to_col = move_to

                            # If move is cancelled, pressing same button twice
                            if move_to == move_from:
                                # Restore the color of the fr square
                                self.restore_square_color(
                                    window, fr_row, fr_col)
                                move_state = 0
                                continue

                            # Create a move in python-chess format based from user input
                            user_move = None

                            # Get the fr_sq and to_sq of the move from user, based from this info
                            # we will create a move based from python-chess format.
                            # Note chess.square() and chess.Move() are from python-chess module
                            fr_row, fr_col = move_from
                            fr_sq = chess.square(fr_col, 7-fr_row)
                            to_sq = chess.square(to_col, 7-to_row)

                            # If user move is a promote. Ask for the piece
                            # only when the pawn move itself is legal (which
                            # does not depend on the piece chosen); an
                            # illegal one falls through to the check below.
                            if self.relative_row(to_sq, board.turn) == RANK_8 and \
                                    moved_piece == chess.PAWN and \
                                    board.is_legal(chess.Move(
                                        fr_sq, to_sq, promotion=chess.QUEEN)):
                                is_promote = True
                                pyc_promo, psg_promo = self.get_promo_piece(
                                        user_move, board.turn, True)
                                user_move = chess.Move(fr_sq, to_sq, promotion=pyc_promo)
                            else:
                                user_move = chess.Move(fr_sq, to_sq)

                            # Check if user move is legal
                            if user_move in list(board.legal_moves):
                                # Update rook location if this is a castle move
                                if board.is_castling(user_move):
                                    self.update_rook(window, str(user_move))

                                # Update board if e.p capture
                                elif board.is_en_passant(user_move):
                                    self.update_ep(window, user_move, board.turn)

                                # Empty the board from_square, applied to any types of move
                                self.psg_board[move_from[0]][move_from[1]] = BLANK

                                # Update board to_square if move is a promotion
                                if is_promote:
                                    self.psg_board[to_row][to_col] = psg_promo
                                # Update the to_square if not a promote move
                                else:
                                    # Place piece in the move to_square
                                    self.psg_board[to_row][to_col] = piece

                                self.redraw_board(window)

                                board.push(user_move)
                                move_cnt += 1
                                self.update_turn_marker(window, board)

                                # The user's first move starts the game:
                                # clocks begin to run and the setup menu
                                # items are disabled.
                                if not is_game_started:
                                    is_game_started = True
                                    self.set_menu_state(window, True)

                                # Update clock, reset elapse to zero
                                human_timer.update_base()

                                # Update game, move from human
                                time_left = human_timer.base
                                user_comment = value['comment_k']
                                self.update_game(move_cnt, user_move, time_left, user_comment)

                                window.find_element('_movelist_').Update(disabled=False)
                                window.find_element('_movelist_').Update('')
                                window.find_element('_movelist_').Update(
                                    self.game.variations[0], append=True, disabled=True)

                                # Clear comment and engine search box
                                window.find_element('comment_k').Update('')
                                window.Element('search_info_all_k').Update('')

                                # Change the color of the "fr" and "to" board squares
                                self.change_square_color(window, fr_row, fr_col)
                                self.change_square_color(window, to_row, to_col)

                                is_human_stm = not is_human_stm
                                # Human has done its move

                                k1 = 'w_elapse_k'
                                k2 = 'w_base_time_k'
                                if not self.is_user_white:
                                    k1 = 'b_elapse_k'
                                    k2 = 'b_base_time_k'

                                # Update elapse box
                                elapse_str = self.get_time_mm_ss_ms(
                                    human_timer.elapse)
                                window.Element(k1).Update(elapse_str)

                                # Update remaining time box
                                elapse_str = self.get_time_h_mm_ss(
                                    human_timer.base)
                                window.Element(k2).Update(elapse_str)

                                window.Element('advise_info_k').Update('')

                            # Else if move is illegal
                            else:
                                move_state = 0
                                # Restore the color of the fr square
                                self.restore_square_color(
                                    window, move_from[0], move_from[1])
                                continue

                if (is_new_game or is_exit_app or
                        is_user_resigns or is_user_wins or is_user_draws or
                        is_user_time_forfeit):
                    break

            # Else if side to move is not human
            elif not is_human_stm and is_engine_ready:
                is_promote = False
                best_move = None
                is_book_from_gui = True

                # Mode: Play, stm: Computer, If using gui book
                if self.is_use_gui_book and move_cnt <= self.max_book_ply:
                    # Verify presence of a book file
                    if os.path.isfile(self.gui_book_file):
                        gui_book = GuiBook(self.gui_book_file, board, self.is_random_book)
                        best_move = gui_book.get_book_move()
                        logging.info('Book move is {}.'.format(best_move))
                    else:
                        logging.warning('GUI book is missing.')

                # Mode: Play, stm: Computer, If there is no book move,
                # let the engine search the best move
                if best_move is None:
                    search = RunEngine(
                        self.queue, self.engine_config_file, self.opp_path_and_file,
                        self.opp_id_name, self.max_depth, engine_timer.base,
                        engine_timer.inc, tc_type=engine_timer.tc_type,
                        period_moves=board.fullmove_number,
                        existing_engine=persistent_engine,
                        option_overrides=self.get_role_options(
                            'opponent', self.opp_id_name)
                    )
                    search.get_board(board)
                    search.daemon = True
                    search.start()
                    engine_timer.start()
                    window.find_element('_gamestatus_').Update(
                            'Mode     Play, Engine is thinking ...')

                    while True:
                        button, value = window.Read(timeout=100)

                        # Window closed while the engine is thinking: stop
                        # the search and leave through the normal end of
                        # game below, which saves the game, quits the
                        # engine and exits.
                        if button == sg.WIN_CLOSED:
                            logging.warning('User closes the window while the engine is thinking.')
                            search.stop()
                            is_exit_app = True
                            break

                        # Update elapse box in m:s format
                        elapse_str = self.get_time_mm_ss_ms(engine_timer.tick())
                        k = 'b_elapse_k'
                        if not self.is_user_white:
                            k = 'w_elapse_k'
                        window.Element(k).Update(elapse_str)

                        # Hide/Unhide engine searching info while engine is thinking
                        if button == 'Show::right_search_info_k':
                            is_hide_search_info = False

                        if button == 'Hide::right_search_info_k':
                            is_hide_search_info = True
                            window.Element('search_info_all_k').Update('')

                        # Show book 1 while engine is searching
                        if button == 'Show::right_book1_k':
                            is_hide_book1 = False
                            ref_book1 = GuiBook(self.computer_book_file,
                                                board, self.is_random_book)
                            all_moves, is_found = ref_book1.get_all_moves()
                            if is_found:
                                window.Element('polyglot_book1_k').Update(all_moves)
                            else:
                                window.Element('polyglot_book1_k').Update('no book moves')

                        # Hide book 1 while engine is searching
                        if button == 'Hide::right_book1_k':
                            is_hide_book1 = True
                            window.Element('polyglot_book1_k').Update('')

                        # Show book 2 while engine is searching
                        if button == 'Show::right_book2_k':
                            is_hide_book2 = False
                            ref_book2 = GuiBook(self.human_book_file, board,
                                                self.is_random_book)
                            all_moves, is_found = ref_book2.get_all_moves()
                            if is_found:
                                window.Element('polyglot_book2_k').Update(all_moves)
                            else:
                                window.Element('polyglot_book2_k').Update('no book moves')

                        # Hide book 2 while engine is searching
                        if button == 'Hide::right_book2_k':
                            is_hide_book2 = True
                            window.Element('polyglot_book2_k').Update('')

                        # Forced engine to move now and create a new game
                        if button == 'New::new_game_k':
                            search.stop()
                            is_search_stop_for_new_game = True

                        # Forced engine to move now
                        if button == 'Move Now':
                            search.stop()

                        # Mode: Play, Computer is thinking, flip board view
                        if button == 'Flip':
                            window = self.flip_play_window(window, board)
                            continue

                        if isinstance(button, str) and (
                                '::board_size_k' in button
                                or '::layout_k' in button):
                            self.handle_board_size_event(window, button)
                            continue

                        if button == 'Resign::resign_game_k':
                            search.stop()
                            is_search_stop_for_resign = True

                        if button == 'User Wins::user_wins_k':
                            search.stop()
                            is_search_stop_for_user_wins = True

                        if button == 'User Draws::user_draws_k':
                            search.stop()
                            is_search_stop_for_user_draws = True

                        # Get the engine search info and display it in GUI text boxes
                        try:
                            msg = self.queue.get_nowait()
                        except Exception:
                            continue

                        msg_str = str(msg)
                        best_move = self.update_text_box(window, msg, is_hide_search_info)
                        if 'bestmove' in msg_str:
                            logging.info('engine msg: {}'.format(msg_str))
                            break

                    # When exiting, do not wait forever on an engine that
                    # does not answer the stop request.
                    search.join(timeout=5.0 if is_exit_app else None)
                    # Keep engine alive for reuse; retrieve instance
                    persistent_engine = search.get_engine()
                    is_book_from_gui = False

                # If engine failed to send a legal move, or the window was
                # closed before it moved (best_move is still None).
                if best_move is None:
                    break

                # Update board with computer move
                move_str = str(best_move)
                fr_col = ord(move_str[0]) - ord('a')
                fr_row = 8 - int(move_str[1])
                to_col = ord(move_str[2]) - ord('a')
                to_row = 8 - int(move_str[3])

                piece = self.psg_board[fr_row][fr_col]
                self.psg_board[fr_row][fr_col] = BLANK

                # Update rook location if this is a castle move
                if board.is_castling(best_move):
                    self.update_rook(window, move_str)

                # Update board if e.p capture
                elif board.is_en_passant(best_move):
                    self.update_ep(window, best_move, board.turn)

                # Update board if move is a promotion
                elif best_move.promotion is not None:
                    is_promote = True
                    _, psg_promo = self.get_promo_piece(best_move, board.turn, False)

                # Update board to_square if move is a promotion
                if is_promote:
                    self.psg_board[to_row][to_col] = psg_promo
                # Update the to_square if not a promote move
                else:
                    # Place piece in the move to_square
                    self.psg_board[to_row][to_col] = piece

                self.redraw_board(window)

                board.push(best_move)
                move_cnt += 1
                self.update_turn_marker(window, board)

                # Update timer
                engine_timer.update_base()

                # Update game, move from engine
                time_left = engine_timer.base
                if is_book_from_gui:
                    engine_comment = 'book'
                else:
                    engine_comment = ''
                self.update_game(move_cnt, best_move, time_left, engine_comment)

                window.find_element('_movelist_').Update(disabled=False)
                window.find_element('_movelist_').Update('')
                window.find_element('_movelist_').Update(
                    self.game.variations[0], append=True, disabled=True)

                # Change the color of the "fr" and "to" board squares
                self.change_square_color(window, fr_row, fr_col)
                self.change_square_color(window, to_row, to_col)

                is_human_stm = not is_human_stm
                # Engine has done its move

                k1 = 'b_elapse_k'
                k2 = 'b_base_time_k'
                if not self.is_user_white:
                    k1 = 'w_elapse_k'
                    k2 = 'w_base_time_k'

                # Update elapse box
                elapse_str = self.get_time_mm_ss_ms(engine_timer.elapse)
                window.Element(k1).Update(elapse_str)

                # Update remaining time box
                elapse_str = self.get_time_h_mm_ss(engine_timer.base)
                window.Element(k2).Update(elapse_str)

                window.find_element('_gamestatus_').Update('Mode     Play')

        # Auto-save game
        logging.info('Saving game automatically')

        # Quit the persistent engine now that the game is over or
        # the user is exiting play mode (e.g. new game, resign).
        if persistent_engine is not None:
            logging.info('Quitting persistent engine at end of game')
            try:
                persistent_engine.quit()
            except Exception:
                logging.exception('Failed to quit persistent engine.')
            finally:
                persistent_engine = None
        if is_user_resigns:
            self.game.headers['Result'] = '0-1' if self.is_user_white else '1-0'
            self.game.headers['Termination'] = '{} resigns'.format(
                    'white' if self.is_user_white else 'black')
        elif is_user_time_forfeit:
            self.game.headers['Result'] = '0-1' if self.is_user_white else '1-0'
            self.game.headers['Termination'] = '{} forfeits on time'.format(
                    'white' if self.is_user_white else 'black')
        elif is_user_wins:
            self.game.headers['Result'] = '1-0' if self.is_user_white else '0-1'
            self.game.headers['Termination'] = 'Adjudication'
        elif is_user_draws:
            self.game.headers['Result'] = '1/2-1/2'
            self.game.headers['Termination'] = 'Adjudication'
        else:
            self.game.headers['Result'] = board.result(claim_draw=True)

        base_h = int(self.human_base_time_ms / 1000)
        inc_h = int(self.human_inc_time_ms / 1000)
        base_e = int(self.engine_base_time_ms / 1000)
        inc_e = int(self.engine_inc_time_ms / 1000)

        if self.is_user_white:
            if self.human_tc_type == 'fischer':
                self.game.headers['WhiteTimeControl'] = str(base_h) + '+' + \
                                                        str(inc_h)
            elif self.human_tc_type == 'delay':
                self.game.headers['WhiteTimeControl'] = str(base_h) + '-' + \
                                                        str(inc_h)
            if self.engine_tc_type == 'fischer':
                self.game.headers['BlackTimeControl'] = str(base_e) + '+' + \
                                                        str(inc_e)
            elif self.engine_tc_type == 'timepermove':
                self.game.headers['BlackTimeControl'] = str(1) + '/' + str(base_e)
        else:
            if self.human_tc_type == 'fischer':
                self.game.headers['BlackTimeControl'] = str(base_h) + '+' + \
                                                        str(inc_h)
            elif self.human_tc_type == 'delay':
                self.game.headers['BlackTimeControl'] = str(base_h) + '-' + \
                                                        str(inc_h)
            if self.engine_tc_type == 'fischer':
                self.game.headers['WhiteTimeControl'] = str(base_e) + '+' + \
                                                        str(inc_e)
            elif self.engine_tc_type == 'timepermove':
                self.game.headers['WhiteTimeControl'] = str(1) + '/' + str(base_e)

        # Do not auto-save games that never started (idle quit or Game->New
        # before the first move).
        if is_game_started:
            self.save_game()

        if board.is_game_over(claim_draw=True):
            sg.popup('Game is over.', title=BOX_TITLE,
                     icon=ico_path[platform]['pecg'])

        if is_exit_app:
            window.Close()
            sys.exit(0)

        self.clear_elements(window)

        return is_new_game, window

    def save_game_as(self, pgn_file, event):
        """Append the current game to pgn_file, labelled with ``event``.

        Only the saved copy gets the label. The game being played keeps its
        own Event, so the auto-save and the games that follow are not
        relabelled.
        """
        own_event = self.game.headers['Event']
        self.game.headers['Event'] = event
        try:
            with open(pgn_file, mode='a+', encoding=PGN_ENCODING) as f:
                f.write('{}\n\n'.format(self.game))
        finally:
            self.game.headers['Event'] = own_event

    def save_game(self):
        """ Save game in append mode """
        with open(self.pecg_auto_save_game, mode='a+',
                  encoding=PGN_ENCODING) as f:
            f.write('{}\n\n'.format(self.game))

    def load_pgn_games(self, pgn, max_games=REVIEW_MAX_DISPLAY_GAMES):
        """Load review game headers up to a display limit."""
        games = []
        is_truncated = False
        with open(pgn, encoding='utf-8', errors='replace') as h:
            while len(games) < max_games:
                offset = h.tell()
                headers = chess.pgn.read_headers(h)
                if headers is None:
                    break
                games.append({'offset': offset, 'headers': headers})

            if len(games) == max_games and chess.pgn.read_headers(h) is not None:
                is_truncated = True

        return games, is_truncated

    def load_review_game(self, pgn, game_entry):
        """Load a single review game from its file offset."""
        with open(pgn, encoding='utf-8', errors='replace') as h:
            h.seek(game_entry['offset'])
            return chess.pgn.read_game(h)

    def add_recent_pgn(self, path):
        """Move a PGN path to the front of the recent-files list and persist."""
        path = os.path.normpath(path)
        files = [p for p in self.recent_pgn_files
                 if os.path.normpath(p) != path]
        self.recent_pgn_files = ([path] + files)[:MAX_RECENT_PGN_FILES]
        self.save_settings()

    def get_review_game_row(self, game, index):
        """Return one table row [no, white, black, result, date, event]."""
        headers = game.headers if hasattr(game, 'headers') else game['headers']
        return [index + 1,
                headers.get('White', '?'),
                headers.get('Black', '?'),
                headers.get('Result', '*'),
                headers.get('Date', '?'),
                headers.get('Event', '?')]

    @staticmethod
    def sort_game_rows(rows, row_map, col, reverse):
        """Return (rows, row_map) of a game table sorted by column
        ``col``: by game number in the first column, as text ignoring
        case in the others."""
        paired = sorted(
            zip(rows, row_map),
            key=lambda rm: (rm[0][col] if col == 0
                            else str(rm[0][col]).lower()),
            reverse=reverse)
        return [p[0] for p in paired], [p[1] for p in paired]

    def fill_review_game_list(self, window):
        """Show the games of the review PGN file in the Game list panel,
        in the order of the file. Follow with mark_review_game()."""
        self.review_list_sort = None
        self.review_list_rows = [self.get_review_game_row(game, index)
                                 for index, game in
                                 enumerate(self.review_games)]
        self.review_list_map = list(range(len(self.review_list_rows)))
        window['review_game_table_k'].Update(values=self.review_list_rows)

    def sort_review_game_list(self, window, col):
        """Sort the Game list panel by a column; again by the same column
        reverses the order. The game on the board stays marked."""
        if not self.review_list_rows \
                or not 0 <= col < len(REVIEW_GAME_LIST_HEADINGS):
            return
        reverse = self.review_list_sort is not None \
            and self.review_list_sort[0] == col \
            and not self.review_list_sort[1]
        self.review_list_sort = (col, reverse)
        self.review_list_rows, self.review_list_map = self.sort_game_rows(
            self.review_list_rows, self.review_list_map, col, reverse)
        window['review_game_table_k'].Update(values=self.review_list_rows)
        self.mark_review_game(window)

    def mark_review_game(self, window):
        """Select the row of the game on the board in the Game list panel
        and bring it into view. No row is selected when that game is not
        one of the list (an empty or an auto-analysed game)."""
        tree = window['review_game_table_k'].Widget
        try:
            row = str(self.review_list_map.index(self.review_game_index) + 1)
        except ValueError:
            row = None
        try:
            if row is None:
                tree.selection_set([])
            elif tuple(tree.selection()) != (row,):
                tree.selection_set(row)
                tree.see(row)
        except tk.TclError:
            logging.exception('Failed to mark the game in the game list.')

    def select_listed_review_game(self, window):
        """A row of the Game list panel was selected (by mouse or with the
        Up / Down keys): put that game on the board."""
        selection = window['review_game_table_k'].Widget.selection()
        try:
            index = self.review_list_map[int(selection[0]) - 1]
        except (IndexError, ValueError):
            return
        # Marking the current game (mark_review_game) also comes here.
        if index == self.review_game_index:
            return
        game = None
        try:
            game = self.load_review_game(self.review_pgn_file,
                                         self.review_games[index])
        except (OSError, IndexError):
            logging.exception('Failed to load game %d of %s', index + 1,
                              self.review_pgn_file)
        if game is None:
            window['_gamestatus_'].Update(
                'Failed to load game {}.'.format(index + 1))
            self.mark_review_game(window)
            return
        self.show_review_game(window, game, index)

    def show_review_game(self, window, game, game_index):
        """Put another game on the Review board. Analysis and threat stay
        on if they were, and follow the board to the new game."""
        self.prepare_review_game(game, game_index)
        self.render_review_movelist(window)
        self.update_review_window(window)
        self.mark_review_game(window)
        self.follow_review_position(window)

    def select_review_game(self, pgn_file=None, games=None):
        """Ask user to select a game from a pgn file.

        The games are shown in a table (White/Black/Result/Date/Event)
        sortable by clicking a column heading; a Recent drop-down reopens
        previously used PGN files. Double-clicking a row is the same as OK.
        """
        if games is None:
            games = []

        headings = ['#', 'White', 'Black', 'Result', 'Date', 'Event']
        col_widths = [5, 16, 16, 7, 10, 18]
        selected_games = games
        selected_pgn = pgn_file or ''
        is_truncated = False
        # rows[i] belongs to game row_map[i] in selected_games; sorting the
        # table only reorders rows/row_map, never selected_games itself.
        rows, row_map = [], []
        sort_state = {'col': None, 'reverse': False}

        def build_rows():
            rows_, map_ = [], []
            for index, game in enumerate(selected_games):
                rows_.append(self.get_review_game_row(game, index))
                map_.append(index)
            return rows_, map_

        def status_text():
            if not selected_games:
                return 'Status: Load a PGN, select a game, then press OK.'
            if is_truncated:
                return ('Status: Showing first {} games only. '
                        'Select one and press OK.'.format(len(selected_games)))
            return ('Status: Loaded {} game(s). Click a heading to sort; '
                    'double-click a game to open it.'.format(
                        len(selected_games)))

        # Auto-load games if a valid PGN file path is passed but no games
        # are loaded yet.
        if selected_pgn and not selected_games:
            if os.path.isfile(selected_pgn):
                try:
                    selected_games, is_truncated = self.load_pgn_games(selected_pgn)
                except Exception:
                    logging.exception(f'Failed to auto-load PGN games from {selected_pgn}')
        rows, row_map = build_rows()

        layout = [
            [sg.Text('PGN', size=(6, 1)),
             sg.Input(default_text=selected_pgn, key='pgn_k', expand_x=True,
                      enable_events=True),
             sg.FileBrowse()],
            [sg.Text('Recent', size=(6, 1)),
             sg.Combo(list(self.recent_pgn_files), key='recent_k',
                      readonly=True, enable_events=True, expand_x=True)],
            [sg.Text(status_text(), key='status_k', relief='sunken',
                     expand_x=True)],
            [sg.Table(values=rows, headings=headings, key='game_table_k',
                      auto_size_columns=False, col_widths=col_widths,
                      justification='left', num_rows=15,
                      enable_click_events=True,
                      select_mode=sg.TABLE_SELECT_MODE_BROWSE,
                      expand_x=True, expand_y=True, font=FONT_BASE)],
            [sg.Button('OK'), sg.Cancel()]
        ]

        w = sg.Window('Review/Select Game', layout,
                      icon=ico_path[platform]['pecg'], finalize=True,
                      resizable=True)

        # Double-click on a row confirms the selection like OK.
        try:
            w['game_table_k'].Widget.bind(
                '<Double-Button-1>',
                lambda e: w.write_event_value('table_dclick_k', True),
                add='+')
        except Exception:
            logging.exception('Failed to bind table double-click.')

        def refresh_table(select_first=True):
            w['game_table_k'].Update(values=rows)
            if rows and select_first:
                w['game_table_k'].Update(select_rows=[0])
            w['status_k'].Update(status_text())

        if rows:
            refresh_table()

        def sort_by(col):
            """Sort rows by table column, toggling the direction."""
            reverse = (not sort_state['reverse']
                       if sort_state['col'] == col else False)
            sort_state['col'] = col
            sort_state['reverse'] = reverse
            return self.sort_game_rows(rows, row_map, col, reverse)

        selected_game = None

        while True:
            e, v = w.Read(timeout=50)
            if e is None or e == 'Cancel':
                break

            # Heading click -> sort by that column.
            if (isinstance(e, tuple) and e[0] == 'game_table_k'
                    and e[1] == '+CLICKED+'):
                clicked_row, clicked_col = e[2]
                if (clicked_row == -1 and clicked_col is not None
                        and clicked_col >= 0 and rows):
                    rows, row_map = sort_by(clicked_col)
                    refresh_table()
                continue

            if e == 'recent_k':
                recent = v['recent_k']
                if recent:
                    w['pgn_k'].Update(recent)
                    e, new_pgn = 'Display Games', recent
                else:
                    continue
            else:
                new_pgn = v.get('pgn_k', '') if isinstance(v, dict) else ''

            if e == 'Display Games' or e == 'pgn_k':
                if not new_pgn:
                    if e == 'Display Games':
                        w['status_k'].Update('Status: Please choose a PGN file.')
                    continue

                # For auto-loading via typing/browsing event, only proceed
                # if it exists as a file.
                if e == 'pgn_k' and not os.path.isfile(new_pgn):
                    continue

                selected_pgn = new_pgn
                try:
                    selected_games, is_truncated = self.load_pgn_games(selected_pgn)
                except (FileNotFoundError, OSError, UnicodeError) as exc:
                    logging.exception(
                        f'Failed to load pgn games from {selected_pgn}: {exc}')
                    w['status_k'].Update(
                        'Status: Failed to read PGN file. Check the file path and encoding.')
                    selected_games = []
                    rows, row_map = [], []
                    refresh_table()
                    continue

                if not selected_games:
                    w['status_k'].Update('Status: No games found in PGN file.')
                    rows, row_map = [], []
                    w['game_table_k'].Update(values=[])
                    continue

                sort_state['col'] = None
                rows, row_map = build_rows()
                refresh_table()
                self.add_recent_pgn(selected_pgn)
                w['recent_k'].Update(values=list(self.recent_pgn_files),
                                     value=self.recent_pgn_files[0])
                continue

            if e == 'OK' or e == 'table_dclick_k':
                if e == 'table_dclick_k':
                    # Ignore double-clicks on the heading row.
                    last = getattr(w['game_table_k'],
                                   'last_clicked_position', (None, None))
                    if last[0] is None or last[0] == -1:
                        continue
                try:
                    view_row = v['game_table_k'][0]
                    selected_index = row_map[view_row]
                except (IndexError, KeyError, TypeError):
                    w['status_k'].Update('Status: Please select a game.')
                    continue

                selected_game_obj = self.load_review_game(
                    selected_pgn, selected_games[selected_index])
                if selected_game_obj is None:
                    w['status_k'].Update('Status: Failed to load selected game.')
                    continue

                selected_game = {
                    'pgn_file': selected_pgn,
                    'games': selected_games,
                    'game_index': selected_index,
                    'game': selected_game_obj
                }
                break

        w.Close()
        return selected_game

    def traverse_review_game(self, node, current_board, indent, is_var):
        """Recursively traverse game tree to build flat list of moves, boards, and nodes."""

        def traverse_only_move(n, b, ind, is_v):
            if n.move is None:
                return b

            # 1. Add starting comment to label if present
            start_comment = f"{{{n.starting_comment}}} " if n.starting_comment else ""

            turn = b.turn
            fullmove = b.fullmove_number
            san = b.san(n.move)
            prefix = f'{fullmove}. ' if turn == chess.WHITE else f'{fullmove}... '

            # 2. Add ending comment to label if present
            end_comment = f" {{{n.comment}}}" if n.comment else ""

            if is_v:
                label = '    ' * ind + f'( {start_comment}{prefix}{san}{end_comment} )'
            else:
                label = '    ' * ind + f'{start_comment}{prefix}{san}{end_comment}'

            next_b = b.copy()
            next_b.push(n.move)

            self.review_move_labels.append(label)
            self.review_boards.append(next_b)
            self.review_nodes.append(n)
            return next_b

        def traverse_continuations(n, b, ind):
            if not n.variations:
                return

            mainline_child = n.variations[0]
            next_b = traverse_only_move(mainline_child, b, ind, False)

            if len(n.variations) > 1:
                for var_node in n.variations[1:]:
                    traverse_node(var_node, b, ind + 1, True)

            traverse_continuations(mainline_child, next_b, ind)

        def traverse_node(n, b, ind, is_v):
            next_b = traverse_only_move(n, b, ind, is_v)
            traverse_continuations(n, next_b, ind)

        traverse_node(node, current_board, indent, is_var)

    def prepare_review_game(self, game, game_index=None):
        """Prepare move list and board positions for review.

        Analysis and threat are left as they are: the caller makes them
        follow the new game (show_review_game) or stops them
        (reset_review_engines_for_new_game).
        """
        self.review_game = game
        self.review_game_index = game_index
        self.review_move_index = 0
        self.review_move_labels = ['Start position']
        self.review_boards = [game.board()]
        self.review_nodes = [game]

        if game.variations:
            # Mainline starts at variations[0]
            self.traverse_review_game(game.variations[0], game.board(), 0, False)
            # Alternative starting moves (variations) start at variations[1:]
            for var_node in game.variations[1:]:
                self.traverse_review_game(var_node, game.board(), 1, True)

    def set_board_from_board_state(self, window, board):
        """Update the GUI board from a python-chess board."""
        self.fen = board.fen()
        self.fen_to_psg_board(window)

    def clear_queue(self, work_queue):
        """Remove all queued messages."""
        while True:
            try:
                work_queue.get_nowait()
            except queue.Empty:
                break
            except Exception:
                break

    # ----- Review analysis / threat output -----
    # A line of search info is the dict RunEngine posts with
    # info_as_dict: the board searched, the score, the variation in full
    # and the search figures. It is turned into text here, when shown, so
    # the variation can be as long as the box is wide.
    @staticmethod
    def format_review_score(score):
        """The score of a line as text, from the point of view of the
        side to move in the position searched (as the engine gives it):
        in pawns ('+0.26'), or the moves to mate ('#5' when that side
        mates, '-#5' when it is mated)."""
        own = score.relative
        if own.is_mate():
            sign = '' if own > chess.engine.Cp(0) else '-'
            return '{}#{}'.format(sign, abs(own.mate()))
        return '{:+.2f}'.format(own.score() / 100)

    @staticmethod
    def format_review_count(count):
        """A number of nodes in short form: 850k, 2.9M, 1.25G."""
        for size, unit, digits in ((1e9, 'G', 2), (1e6, 'M', 1),
                                   (1e3, 'k', 0)):
            if count >= size:
                return '{:.{}f}{}'.format(count / size, digits, unit)
        return str(count)

    def format_review_figures(self, info):
        """The search figures of a line of info: depth (and selective
        depth), time, nodes searched and nodes per second."""
        parts = []
        if info.get('depth') is not None:
            parts.append('depth {}'.format(info['depth']) + (
                '/{}'.format(info['seldepth']) if info.get('seldepth')
                else ''))
        if info.get('time') is not None:
            parts.append('time {:.1f}s'.format(info['time']))
        if info.get('nodes'):
            parts.append('nodes {}'.format(
                self.format_review_count(info['nodes'])))
        if info.get('nps'):
            parts.append('nps {}'.format(
                self.format_review_count(info['nps'])))
        return '  '.join(parts)

    @staticmethod
    def format_review_pv(board, pv, width):
        """The variation ``pv`` from ``board`` as moves with move numbers
        ('12. Nf3 Nc6 13. Bb5', or '12... Nc6 13. Bb5' when Black is to
        move): as many moves as fit in ``width`` characters, with ' …'
        after a variation that was cut."""
        board = board.copy(stack=False)
        text = ''
        for i, move in enumerate(pv):
            if not board.is_legal(move):
                break               # an engine may end a line with rubbish
            san = board.san(move)
            if board.turn == chess.WHITE:
                san = '{}. {}'.format(board.fullmove_number, san)
            elif i == 0:
                san = '{}... {}'.format(board.fullmove_number, san)
            longer = text + ' ' + san if text else san
            # Every move but the last leaves room for the cut mark.
            if text and len(longer) > width - (2 if i < len(pv) - 1 else 0):
                return text + ' …'
            text = longer
            board.push(move)
        return text

    def review_box_chars(self, widget, fallback=48):
        """The number of characters that fit on a line of an Analysis or
        Threat box (``fallback`` while it is not on screen yet)."""
        try:
            width = widget.winfo_width()
            if width <= 1:
                return fallback
            font = getattr(widget, 'pecg_font', None)
            if font is None:
                font = widget.pecg_font = tkfont.Font(
                    root=widget, font=widget.cget('font'))
            edge = sum(int(str(widget.cget(name))) for name in
                       ('borderwidth', 'padx', 'highlightthickness'))
            return max(12, (width - 2 * edge) // max(1, font.measure('0')))
        except (tk.TclError, ValueError):
            return fallback

    def review_info_rows(self, infos, width):
        """The lines of an Analysis or Threat box for these lines of
        search info (None where a line has none yet), ``width`` characters
        wide: the search figures, then the score and the variation of
        each line. Each row is a list of (text, tag) pieces."""
        first = next((info for info in infos if info), None)
        rows = [[(self.format_review_figures(first)[:width] if first else '',
                  'figures')]]
        for info in infos:
            if not info:
                rows.append([('', 'pv')])
                continue
            # The score takes 6 characters ('+12.34', '-#12') and 2 spaces.
            rows.append([
                ('{:>6}'.format(self.format_review_score(info['score'])),
                 'score'),
                ('  ' + self.format_review_pv(info['board'], info['pv'],
                                              width - 8), 'pv')])
        return rows

    @staticmethod
    def set_review_box(widget, rows):
        """Show ``rows`` (see review_info_rows) in an Analysis or Threat
        box. Nothing is redrawn when they are what the box shows."""
        if getattr(widget, 'pecg_rows', None) == rows:
            return
        widget.pecg_rows = rows
        top = widget.yview()[0]
        widget.configure(state='normal')
        widget.delete('1.0', tk.END)
        for i, row in enumerate(rows):
            if i:
                widget.insert(tk.END, '\n')
            for text, tag in row:
                widget.insert(tk.END, text, tag)
        widget.configure(state='disabled')
        widget.yview_moveto(top)

    def update_review_analysis_panel(self, window):
        """Refresh Review mode analysis widgets: the status and the box
        (search figures, then one line per variation asked for)."""
        window['review_analysis_status_k'].Update(self.review_analysis_status)
        widget = window['review_analysis_k'].Widget
        self.set_review_box(widget, self.review_info_rows(
            [self.review_analysis_lines.get(line) for line in
             range(1, self.review_multipv() + 1)],
            self.review_box_chars(widget)))

    # ----- Review engine settings (Hash, Threads, MultiPV) -----
    def review_engine_option(self, role, option):
        """Return (name, value, min, max) of a number option - 'Hash',
        'Threads', 'MultiPV' - of the engine of a Review role ('analysis'
        or 'threat'), or None when that engine has no such option. The
        value is the one the role uses: its own if it has one (see
        role_engine_options), otherwise the engine's."""
        eng_id_name = getattr(self, ROLE_META[role][0])
        if not eng_id_name:
            return None
        own = {name.lower(): value for name, value in
               self.get_role_options(role, eng_id_name).items()}
        for o in self.get_engine_options(eng_id_name):
            name = str(o.get('name', ''))
            if name.lower() != option.lower() or o.get('type') != 'spin':
                continue
            try:
                value = int(own.get(name.lower(), o.get('value')))
                return (name, value, int(o.get('min', 1)),
                        int(o.get('max', value)))
            except (TypeError, ValueError):
                return None
        return None

    def review_multipv(self):
        """Lines of analysis to ask for and show: what the user chose,
        but no more than the analysis engine can give."""
        return max(1, min(self.review_analysis_multipv,
                          self.review_multipv_limit))

    def show_review_engine_settings(self, window):
        """Fill the Hash, Threads and MultiPV widgets of the Analysis and
        Threat panels from the engines of those roles. A widget of an
        option the engine does not have is disabled."""
        cores = os.cpu_count() or 1
        for role in ('analysis', 'threat'):
            hash_box = window['review_{}_hash_k'.format(role)]
            option = self.review_engine_option(role, 'Hash')
            if option:
                _, value, low, high = option
                hash_box.Update(
                    value=value, disabled=False,
                    values=choices_with([mb for mb in REVIEW_HASH_CHOICES_MB
                                         if low <= mb <= high], value))
            else:
                hash_box.Update(value='', values=[], disabled=True)

            threads = window['review_{}_threads_k'.format(role)]
            option = self.review_engine_option(role, 'Threads')
            if option:
                _, value, low, high = option
                threads.Update(
                    value=value, disabled=False,
                    values=choices_with(range(max(1, low),
                                              min(high, cores) + 1), value))
            else:
                threads.Update(value=1, values=[1], disabled=True)

        option = self.review_engine_option('analysis', 'MultiPV')
        self.review_multipv_limit = \
            min(REVIEW_ANALYSIS_MULTIPV_MAX, option[3]) if option else 1
        window['review_analysis_multipv_k'].Update(
            value=self.review_multipv(),
            values=list(range(1, self.review_multipv_limit + 1)),
            disabled=self.review_multipv_limit == 1)

    def change_review_engine_setting(self, window, key, value):
        """The user changed a Hash, Threads or MultiPV widget (``key``,
        'review_<role>_<setting>_k') of the Analysis or Threat panel: keep
        the value and restart that search with it if it is on.

        Hash and Threads are kept as options of that role for its engine
        (role_engine_options), as Engine -> Manage -> Configure does. They
        are kept even when equal to the engine's own value, so an engine
        that is already running is set to it too.
        """
        try:
            _, role, setting, _ = key.split('_')
            value = int(value)
        except (TypeError, ValueError):
            return
        if setting == 'multipv':
            if value == self.review_analysis_multipv:
                return
            self.review_analysis_multipv = value
            self.save_settings()
        else:
            option = self.review_engine_option(role, setting)
            if option is None or option[1] == value:
                return
            eng_id_name = getattr(self, ROLE_META[role][0])
            options = {name: v for name, v in
                       self.get_role_options(role, eng_id_name).items()
                       if name.lower() != setting}
            options[option[0]] = value
            self.set_role_options(role, eng_id_name, options)
            logging.info('Review %s engine %s: %s set to %s.', role,
                         eng_id_name, option[0], value)
        if role == 'analysis':
            self.restart_review_analysis_later(window)
        else:
            self.restart_review_threat_later(window)

    def _keep_one_engine(self, attr_engine, engine):
        """Store ``engine`` in ``attr_engine``, keeping exactly one live engine.

        If a different engine is already held, quit the old one and keep the
        newly-recovered engine. The previous code quit the new engine instead,
        which reused an older (possibly stale) process and discarded the engine
        that had just finished the active search, causing intermittent analysis
        failures and wasting processes.
        """
        if engine is None:
            return
        current = getattr(self, attr_engine)
        if current is not None and current is not engine:
            try:
                current.quit()
            except Exception:
                logging.exception('Failed to quit redundant review engine.')
        setattr(self, attr_engine, engine)

    def _collect_stale_search(self, search, attr_engine):
        """Attempt to join a previously-stopped search thread.

        If the thread has finished, recover the engine instance for reuse.
        Returns True if the thread is done, False if still running.
        """
        if search is None:
            return True
        search.join(timeout=0)
        if not search.is_alive():
            self._keep_one_engine(attr_engine, search.get_engine())
            return True
        return False

    def stop_review_analysis(self):
        """Stop the current Review mode analysis search.

        Signals the engine thread to stop without blocking the GUI.
        The thread is parked in ``_stale_analysis_searches`` so that
        ``poll_review_analysis`` can collect it later.  This keeps the
        button click fully non-blocking — no ``join()`` on the GUI
        thread — eliminating the "long press" feel.
        """
        if self.review_analysis_search is not None:
            self.review_analysis_search.stop()
            # Park the thread for asynchronous cleanup instead of
            # blocking the GUI with join().
            self._stale_analysis_searches.append(self.review_analysis_search)
            self.review_analysis_search = None
        self.clear_queue(self.review_queue)

    def close_review_analysis(self):
        """Stop Review analysis and close its engine process."""
        self.stop_review_analysis()
        # Also clean up all stale search threads.
        for s in self._stale_analysis_searches:
            s.join(timeout=2.0)
            if not s.is_alive():
                eng = s.get_engine()
                if eng is not None and self.review_analysis_engine is None:
                    self.review_analysis_engine = eng
                elif eng is not None:
                    try:
                        eng.quit()
                    except Exception:
                        pass
        self._stale_analysis_searches = []
        if self.review_analysis_engine is not None:
            try:
                self.review_analysis_engine.quit()
            except Exception:
                logging.exception('Failed to quit review analysis engine.')
            finally:
                self.review_analysis_engine = None

    def start_review_analysis(self, window):
        """Start analysis for the current Review mode position."""
        if self.review_game is None or not self.review_boards:
            return

        if self.analysis_path_and_file is None or self.analysis_id_name is None:
            self.review_analysis_enabled = False
            self.review_analysis_status = 'No analysis engine selected'
            self.review_analysis_lines = {}
            self.update_review_analysis_panel(window)
            return

        self.stop_review_analysis()
        self.review_analysis_enabled = True
        # Fresh search: its output is current, so poll must not discard it.
        self.review_analysis_stale = False
        self.review_analysis_lines = {}
        # Give immediate feedback: a cold start (no reusable engine) must spawn
        # and hand-shake an engine process, so say so; a warm reuse is fast.
        if self.review_analysis_engine is None:
            self.review_analysis_status = \
                'Analysis: starting {}...'.format(self.analysis_id_name)
        else:
            self.review_analysis_status = \
                'Analysing with {} at position {}'.format(
                    self.analysis_id_name, self.review_move_index)
        self.update_review_analysis_panel(window)
        # Force an immediate repaint so the click is acknowledged now instead of
        # on the next Read(timeout=50) tick.
        window.refresh()

        search = RunEngine(
            self.review_queue, self.engine_config_file,
            self.analysis_path_and_file, self.analysis_id_name,
            self.max_depth, self.review_analysis_time_sec * 1000, 0,
            tc_type='timepermove',
            period_moves=0,
            is_stream_search_info=True,
            existing_engine=self.review_analysis_engine,
            multipv=self.review_multipv(),
            option_overrides=self.get_role_options(
                'analysis', self.analysis_id_name),
            info_as_dict=True
        )
        # Its info comes back with this board: what poll shows only.
        self.review_analysis_board = \
            self.review_boards[self.review_move_index].copy(stack=False)
        search.get_board(self.review_analysis_board)
        search.is_move_delay = False
        search.daemon = True
        search.start()
        self.review_analysis_search = search
        self.review_analysis_engine = None

    def refresh_review_analysis(self, window):
        """Restart analysis after the Review mode position changes."""
        if not self.review_analysis_enabled:
            self.review_analysis_lines = {}
            self.review_analysis_status = 'Analysis stopped'
            self.update_review_analysis_panel(window)
            return
        self.start_review_analysis(window)

    def reset_review_engines_for_new_game(self, window):
        """Stop and disable Review analysis/threat: used when auto-analysis
        replaces the game on the board with its annotated copy.

        Both panels are then cleanly 'stopped', so the next click on the
        Analysis/Threat button starts a new search. (Switching to another
        game keeps them on instead: see show_review_game.)
        """
        self.review_analysis_enabled = False
        self.review_threat_enabled = False
        self.review_analysis_stale = False
        self.review_threat_stale = False
        self.stop_review_analysis()
        self.stop_review_threat()
        self.review_analysis_lines = {}
        self.review_analysis_status = 'Analysis stopped'
        self.review_threat_line = None
        self.review_threat_status = 'Threat stopped'
        self.update_review_analysis_panel(window)
        self.update_review_threat_panel(window)

    def confirm_auto_analysis(self, window):
        """Ask the user to pick engine/time and confirm auto-analysis.

        Returns a dict with engine_id_name, engine_path_and_file and
        time_ms (milliseconds per move) if the user confirms, otherwise
        False.
        """
        if self.review_game is None:
            sg.popup('Load a game first.', title='Auto-Analyze',
                     icon=ico_path[platform]['pecg'])
            return False

        if not self.engine_id_name_list:
            sg.popup('No engines installed.\n\n'
                     'Add one via Engine -> Install / Manage.',
                     title='Auto-Analyze', icon=ico_path[platform]['pecg'])
            return False

        move_count = 0
        node = self.review_game
        while node.variations:
            move_count += 1
            node = node.variations[0]

        # Default to the saved auto-analysis engine, or the analysis engine.
        default_engine = self.auto_analysis_engine_id_name
        if default_engine not in self.engine_id_name_list:
            default_engine = self.analysis_id_name
        if default_engine not in self.engine_id_name_list:
            default_engine = self.engine_id_name_list[0]

        default_time = self.auto_analysis_time_ms
        if not isinstance(default_time, int) \
                or default_time < AUTO_ANALYSIS_TIME_MS_MIN:
            default_time = AUTO_ANALYSIS_TIME_MS

        default_plies = max(AUTO_ANALYSIS_REPLAY_PLIES_MIN,
                            min(AUTO_ANALYSIS_REPLAY_PLIES_MAX,
                                self.auto_analysis_replay_plies))

        layout = [
            [sg.Text('Select engine and time per move for auto-analysis:')],
            [sg.Text('Engine:', size=(16, 1)),
             sg.Listbox(values=self.engine_id_name_list, size=(40, 6),
                        key='auto_engine_k',
                        default_values=[default_engine])],
            [sg.Text('MS per move:', size=(16, 1)),
             sg.Combo(choices_with(AUTO_ANALYSIS_TIME_CHOICES_MS,
                                   default_time),
                      default_value=default_time, readonly=True,
                      size=(8, 1), key='auto_time_k')],
            [sg.Text('PV length:', size=(16, 1),
                     tooltip='Length of the engine-vs-engine "Better is"\n'
                             'variation. Each ply is one extra search, so\n'
                             'longer lines analyze more slowly.'),
             sg.Spin([n for n in range(AUTO_ANALYSIS_REPLAY_PLIES_MIN,
                                       AUTO_ANALYSIS_REPLAY_PLIES_MAX + 1)],
                     initial_value=default_plies, readonly=True,
                     size=(8, 1), key='auto_plies_k')],
            [sg.Text('Moves to analyze:', size=(16, 1)),
             sg.Text(str(move_count), size=(30, 1))],
            [sg.Text('The annotated game will be saved to:')],
            [sg.Text(AUTO_ANALYSIS_OUTPUT_FILE, size=(50, 1),
                     relief='sunken')],
            [sg.OK(), sg.Button('Configure'), sg.Cancel()],
        ]

        self.begin_dialog(window)
        w = sg.Window('Auto-Analyze Game', layout,
                      icon=ico_path[platform]['pecg'], modal=True)
        result = False
        while True:
            e, v = w.Read(timeout=10)
            if e == sg.TIMEOUT_KEY:
                continue
            if e is None or e == 'Cancel':
                break
            if e == 'Configure':
                selected = v.get('auto_engine_k', [])
                eng = selected[0] if selected else None
                if eng is None:
                    sg.popup('Please select an engine to configure.',
                             title='Auto-Analyze',
                             icon=ico_path[platform]['pecg'])
                    continue
                self.configure_role_engine('auto_analysis', eng)
                try:
                    w.make_modal()
                except Exception:
                    pass
                continue
            if e == 'OK':
                selected = v.get('auto_engine_k', [])
                engine_id_name = selected[0] if selected else None
                if engine_id_name is None:
                    sg.popup('Please select an engine.', title='Auto-Analyze',
                             icon=ico_path[platform]['pecg'])
                    continue
                time_ms = int(v['auto_time_k'])
                replay_plies = int(v['auto_plies_k'])
                try:
                    eng_file, eng_path = self.get_engine_file(engine_id_name)
                except Exception:
                    logging.exception('Failed to resolve engine file.')
                    sg.popup('Failed to locate the selected engine.',
                             title='Auto-Analyze',
                             icon=ico_path[platform]['pecg'])
                    break
                self.auto_analysis_engine_id_name = engine_id_name
                self.auto_analysis_time_ms = time_ms
                self.auto_analysis_replay_plies = replay_plies
                self.save_settings()
                result = {
                    'engine_id_name': engine_id_name,
                    'engine_path_and_file': eng_path,
                    'time_ms': time_ms,
                    'replay_plies': replay_plies,
                }
                break
        w.Close()
        self.end_dialog(window)
        return result

    def start_auto_analysis(self, window):
        """Start the background auto-analysis thread for the loaded game."""
        if self.review_game is None:
            return
        if self.auto_analysis_thread is not None and \
                self.auto_analysis_thread.is_alive():
            sg.popup('An analysis is already running.',
                     title='Auto-Analyze', icon=ico_path[platform]['pecg'])
            return
        config = self.confirm_auto_analysis(window)
        if config is False:
            return

        self.auto_analysis_cancel = threading.Event()
        self.auto_analysis_queue = queue.Queue()
        self.auto_analysis_thread = AutoAnalyzeGame(
            copy.deepcopy(self.review_game),
            self.engine_config_file,
            config['engine_path_and_file'],
            config['engine_id_name'],
            # The dialog collects milliseconds; the engine Limit wants
            # a seconds float.
            config['time_ms'] / 1000.0,
            self.auto_analysis_queue,
            self.auto_analysis_cancel,
            self.max_depth,
            option_overrides=self.get_role_options(
                'auto_analysis', config['engine_id_name']),
            multipv=AUTO_ANALYSIS_MULTIPV,
            replay_plies=config.get('replay_plies',
                                    self.auto_analysis_replay_plies),
        )
        self.auto_analysis_thread.start()
        self.set_review_menu_state(window, analyzing=True)
        window['_gamestatus_'].Update(
            'Auto-analyzing move 1/{}...'.format(
                self._count_mainline_moves(self.review_game)))
        logging.info('Started auto-analysis of game with %d moves.',
                     self._count_mainline_moves(self.review_game))

    def _count_mainline_moves(self, game):
        """Return the number of half-moves on the game's mainline."""
        count = 0
        node = game
        while node.variations:
            count += 1
            node = node.variations[0]
        return count

    def cancel_auto_analysis(self, window):
        """Signal the running auto-analysis thread to stop."""
        if self.auto_analysis_thread is None:
            return
        self.auto_analysis_cancel.set()
        window['_gamestatus_'].Update('Cancelling analysis...')
        logging.info('User cancelled auto-analysis.')

    def poll_auto_analysis(self, window):
        """Consume messages from the auto-analysis background thread."""
        if self.auto_analysis_thread is None:
            return

        done = False
        cancelled = False
        while True:
            try:
                msg = self.auto_analysis_queue.get_nowait()
            except queue.Empty:
                break
            except Exception:
                logging.exception('Failed to read auto-analysis queue.')
                break

            msg_type = msg.get('type')
            if msg_type == 'progress':
                window['_gamestatus_'].Update(
                    'Auto-analyzing move {}/{}...'.format(
                        msg['current'], msg['total']))
            elif msg_type == 'done':
                annotated = msg['game']
                self.review_game = annotated
                self.review_game_index = None
                self.prepare_review_game(annotated)
                self.render_review_movelist(window)
                self.update_review_window(window)
                # The annotated copy is not a game of the list.
                self.mark_review_game(window)
                self.reset_review_engines_for_new_game(window)
                window['_gamestatus_'].Update(
                    'Analysis complete. Saved to {}.'.format(
                        AUTO_ANALYSIS_OUTPUT_FILE))
                done = True
            elif msg_type == 'cancelled':
                window['_gamestatus_'].Update('Analysis cancelled.')
                cancelled = True
            elif msg_type == 'error':
                sg.popup(msg.get('message', 'Auto-analysis failed.'),
                         title='Auto-Analyze',
                         icon=ico_path[platform]['pecg'])
                window['_gamestatus_'].Update('Analysis failed.')
                done = True

        if done or cancelled:
            self.auto_analysis_thread = None
            self.set_review_menu_state(window, analyzing=False)

    def poll_review_analysis(self, window):
        """Consume engine messages for Review mode analysis."""
        # Try to collect any stale analysis threads from previous stops.
        active_stale = []
        for s in self._stale_analysis_searches:
            if self._collect_stale_search(s, 'review_analysis_engine'):
                pass
            else:
                active_stale.append(s)
        self._stale_analysis_searches = active_stale

        updated = False
        while True:
            try:
                msg = self.review_queue.get_nowait()
            except queue.Empty:
                break
            except Exception:
                logging.exception('Failed to read Review mode analysis queue.')
                break

            if isinstance(msg, dict):
                # Skip stale analysis info: the search was stopped by navigation
                # and the engine is still draining old-position lines. A freshly
                # started search clears this flag, so its output is shown -
                # but only its own, not what an old search still posts.
                if self.review_analysis_stale \
                        or msg.get('board') is not self.review_analysis_board:
                    continue
                if 1 <= msg['multipv'] <= self.review_multipv():
                    self.review_analysis_lines[msg['multipv']] = msg
                    if self.review_analysis_status.startswith(
                            'Analysis: starting'):
                        self.review_analysis_status = \
                            'Analysing with {} at position {}'.format(
                                self.analysis_id_name, self.review_move_index)
                    updated = True
            # 'bestmove' messages need no handling here: engine recovery and
            # the "ready" status are driven by the non-blocking is_alive()
            # check below. A bestmove may originate from a stale search that
            # shares this queue, so it must never act on the active search
            # (the old blocking join(timeout=0.1) on a still-running search
            # was what froze the GUI and made the buttons feel unresponsive).

        # Recover the engine once the *active* search finishes, without ever
        # blocking the GUI thread on join().
        if self.review_analysis_search is not None \
                and not self.review_analysis_search.is_alive():
            self._keep_one_engine(
                'review_analysis_engine',
                self.review_analysis_search.get_engine())
            self.review_analysis_search = None
            if self.review_analysis_enabled and not self.review_analysis_stale:
                self.review_analysis_status = \
                    'Analysis ready - {}'.format(self.analysis_id_name)
                updated = True

        if updated:
            self.update_review_analysis_panel(window)

    def update_review_threat_panel(self, window):
        """Refresh Review mode threat analysis widgets: the status and
        the box (search figures, then the threat line)."""
        window['review_threat_status_k'].Update(self.review_threat_status)
        widget = window['review_threat_k'].Widget
        self.set_review_box(widget, self.review_info_rows(
            [self.review_threat_line], self.review_box_chars(widget)))

    def stop_review_threat(self):
        """Stop the current Review mode threat analysis search.

        Non-blocking, similar to ``stop_review_analysis``.
        """
        if self.review_threat_search is not None:
            self.review_threat_search.stop()
            self._stale_threat_searches.append(self.review_threat_search)
            self.review_threat_search = None
            logging.info('Threat analysis search stopped.')
        self.clear_queue(self.threat_queue)

    def close_review_threat(self):
        """Stop threat analysis and close its engine process."""
        self.stop_review_threat()
        # Also clean up all stale search threads.
        for s in self._stale_threat_searches:
            s.join(timeout=2.0)
            if not s.is_alive():
                eng = s.get_engine()
                if eng is not None and self.review_threat_engine is None:
                    self.review_threat_engine = eng
                elif eng is not None:
                    try:
                        eng.quit()
                    except Exception:
                        pass
        self._stale_threat_searches = []
        if self.review_threat_engine is not None:
            try:
                self.review_threat_engine.quit()
            except Exception:
                logging.exception('Failed to quit threat engine.')
            finally:
                self.review_threat_engine = None

    def create_null_move_board(self, board):
        """Return a board with the side to move flipped (simulating a pass).

        En passant is cleared because it is only valid for a single ply; once
        the current side passes, the en passant window expires before the
        opponent can use it.
        """
        fen_parts = board.fen().split(' ')
        fen_parts[1] = 'b' if fen_parts[1] == 'w' else 'w'
        fen_parts[3] = '-'  # en passant expires after one ply
        return chess.Board(' '.join(fen_parts))

    def start_review_threat(self, window):
        """Start threat analysis for the current Review mode position.

        The engine analyses the position after a null move (side to move
        passes), revealing what the opponent threatens.  If the side to move
        is in check the feature is unavailable for that position.
        """
        if self.review_game is None or not self.review_boards:
            return

        board = self.review_boards[self.review_move_index]

        if self.threat_path_and_file is None or self.threat_id_name is None:
            self.review_threat_enabled = False
            self.review_threat_status = 'No threat engine selected'
            self.review_threat_line = None
            self.update_review_threat_panel(window)
            logging.warning('Threat analysis failed to start: no threat engine selected.')
            return

        self.review_threat_enabled = True
        # Fresh search: its output is current, so poll must not discard it.
        self.review_threat_stale = False

        # Cannot use null move when the side to move is in check.
        if board.is_check():
            self.stop_review_threat()
            self.review_threat_status = 'Check - threat N/A'
            self.review_threat_line = None
            self.update_review_threat_panel(window)
            logging.info('Threat analysis is unavailable at move index %d: king is in check.', self.review_move_index)
            return

        self.stop_review_threat()
        self.review_threat_line = None
        # Give immediate feedback: a cold start (no reusable engine) must spawn
        # and hand-shake an engine process, so say so; a warm reuse is fast.
        if self.review_threat_engine is None:
            self.review_threat_status = 'Threat: starting {}...'.format(
                self.threat_id_name)
        else:
            self.review_threat_status = 'Threat: {} searching... (pos {})'.format(
                self.threat_id_name, self.review_move_index)
        self.update_review_threat_panel(window)
        # Force an immediate repaint so the click is acknowledged now instead of
        # on the next Read(timeout=50) tick.
        window.refresh()

        # Build a null-move board: flip the side to move so the engine sees
        # the position as if the current side passed their turn.
        threat_board = self.create_null_move_board(board)

        search = RunEngine(
            self.threat_queue, self.engine_config_file,
            self.threat_path_and_file, self.threat_id_name,
            self.max_depth, self.review_threat_time_sec * 1000, 0,
            tc_type='timepermove',
            period_moves=0,
            is_stream_search_info=True,
            existing_engine=self.review_threat_engine,
            multipv=1,
            option_overrides=self.get_role_options(
                'threat', self.threat_id_name),
            info_as_dict=True
        )
        self.review_threat_board = threat_board
        search.get_board(threat_board)
        search.is_move_delay = False
        search.daemon = True
        search.start()
        self.review_threat_search = search
        self.review_threat_engine = None
        logging.info('Threat analysis started for move index %d.', self.review_move_index)

    def refresh_review_threat(self, window):
        """Restart threat analysis after the Review mode position changes."""
        if not self.review_threat_enabled:
            self.review_threat_line = None
            self.review_threat_status = 'Threat stopped'
            self.update_review_threat_panel(window)
            return
        self.start_review_threat(window)

    def poll_review_threat(self, window):
        """Consume engine messages for Review mode threat analysis."""
        # Try to collect any stale threat threads from previous stops.
        active_stale = []
        for s in self._stale_threat_searches:
            if self._collect_stale_search(s, 'review_threat_engine'):
                pass
            else:
                active_stale.append(s)
        self._stale_threat_searches = active_stale

        updated = False
        while True:
            try:
                msg = self.threat_queue.get_nowait()
            except queue.Empty:
                break
            except Exception:
                logging.exception('Failed to read threat analysis queue.')
                break

            if isinstance(msg, dict):
                # Skip stale threat info from the old position; a freshly started
                # search clears this flag so its output is shown (see
                # poll_review_analysis).
                if self.review_threat_stale \
                        or msg.get('board') is not self.review_threat_board:
                    continue
                self.review_threat_line = msg
                if self.review_threat_status.startswith('Threat: starting'):
                    self.review_threat_status = \
                        'Threat: {} searching... (pos {})'.format(
                            self.threat_id_name, self.review_move_index)
                updated = True
            # 'bestmove' messages need no handling here (see
            # poll_review_analysis): engine recovery and the "ready" status come
            # from the non-blocking is_alive() check below, so a stale search's
            # bestmove can never block the GUI on join().

        # Recover the engine once the *active* search finishes, without blocking.
        if self.review_threat_search is not None \
                and not self.review_threat_search.is_alive():
            self._keep_one_engine(
                'review_threat_engine',
                self.review_threat_search.get_engine())
            self.review_threat_search = None
            if self.review_threat_enabled and not self.review_threat_stale:
                self.review_threat_status = \
                    'Threat ready - {}'.format(self.threat_id_name)
                updated = True

        if updated:
            self.update_review_threat_panel(window)

    def update_review_window(self, window):
        """Refresh review widgets based on current review state."""
        if self.review_game is None or not self.review_boards:
            return

        # Show every PGN header, one per line; the panel scrolls when the
        # list is long or a value is large.
        headers = self.review_game.headers
        header_text = '\n'.join(
            f"{tag}: {value}" for tag, value in headers.items())

        if self.review_pgn_file:
            window['review_pgn_k'].Update(self.review_pgn_file)

        game_number = (
            self.review_game_index + 1
            if self.review_game_index is not None
            else '?'
        )
        window['_gamestatus_'].Update(
            f'Mode     Review, game {game_number}/{len(self.review_games)}')
        window['review_header_k'].Update(header_text)
        window['review_nav_k'].Update(
            f'Position {self.review_move_index}/{len(self.review_boards) - 1}')
        # Highlight the current move in the multiline
        if 'review_move_list_k' in window.AllKeysDict:
            self.highlight_current_move(window['review_move_list_k'].Widget)

        # Update book moves for the current position.
        board = self.review_boards[self.review_move_index]
        book_text = ''
        for book_file in [self.computer_book_file, self.human_book_file]:
            if os.path.isfile(book_file):
                ref_book = GuiBook(book_file, board, self.is_random_book)
                all_moves, is_found = ref_book.get_all_moves()
                if is_found:
                    book_text = all_moves
                    break
        window['review_book_k'].Update(book_text if book_text else 'no book moves')

        self.side_to_move = board.turn
        self.set_board_from_board_state(
            window, self.review_boards[self.review_move_index])
        self.update_review_analysis_panel(window)
        self.update_review_threat_panel(window)

    def set_window_style(self):
        """Theme and element options shared by the Play and Review
        windows: the margin around everything and the scrollbar colours."""
        sg.change_look_and_feel(self.gui_theme)
        sg.set_options(margins=(10, 8), border_width=1, font=FONT_BASE,
                       sbar_trough_color=sg.theme_background_color(),
                       sbar_background_color=PANEL_BORDER_COLOR,
                       sbar_arrow_color=sg.theme_text_color(),
                       sbar_frame_color=PANEL_BORDER_COLOR)

    def build_review_layout(self, is_white_at_bottom=True):
        """
        Creates all elements for the Review window: the board box (the
        board with the navigation bar under it) and one panel per group
        of controls, all in a single layout row. Their placement is taken
        over by PanelLayout in create_review_window().

        :param is_white_at_bottom: board orientation, white pieces at
        the bottom when True.
        :return: GUI layout
        """
        self.set_window_style()

        def text_box(key, lines, **options):
            return sg.Multiline('', do_not_clear=True, autoscroll=False,
                                size=(48, lines), font=FONT_BASE, key=key,
                                disabled=True, expand_x=True, expand_y=True,
                                **options)

        def status(key, text):
            return sg.Text(text, size=(30, 1), font=FONT_BASE, key=key,
                           relief='sunken', expand_x=True)

        def button(label, width, key=None, tooltip=None, font=FONT_BASE,
                   **options):
            return sg.Button(label, key=key, size=(width, 1), font=font,
                             pad=(1, 3), tooltip=tooltip, **options)

        # The navigation bar belongs to the board: it sits under it in
        # the board box, as wide as the board, and moves with it. Panels
        # dropped below the board come under this bar. The buttons show
        # an icon (plain Unicode symbols, no image files); their keys are
        # the event names the Review loop and the shortcuts use.
        nav_bar = sg.Column(
            [[button(icon, 4, key, tip, FONT_NAV_ICON, expand_x=True)
              for key, icon, tip in REVIEW_NAV_BUTTONS]],
            key='review_nav_bar_k', pad=((0, TURN_MARKER_PX), 0),
            expand_x=True)
        board_box = sg.Column(
            self.create_board(is_white_at_bottom) + [[nav_bar]],
            key='review_board_box_k', pad=(0, 0))

        # The games of the PGN file; selecting one puts it on the board.
        # It is filled by fill_review_game_list().
        game_list = self.panel('review_gamelist_panel_k', 'Game list', [
            [sg.Table(values=[], headings=REVIEW_GAME_LIST_HEADINGS,
                      key='review_game_table_k', auto_size_columns=False,
                      col_widths=REVIEW_GAME_LIST_WIDTHS,
                      justification='left', num_rows=REVIEW_GAME_LIST_ROWS,
                      enable_events=True, enable_click_events=True,
                      select_mode=sg.TABLE_SELECT_MODE_BROWSE,
                      vertical_scroll_only=False, font=FONT_BASE,
                      expand_x=True, expand_y=True)],
        ])

        game = self.panel('review_game_panel_k', 'Game details', [
            [sg.Text('PGN file', size=(8, 1), font=FONT_BASE),
             sg.Text('', size=(30, 1), font=FONT_SMALL, key='review_pgn_k',
                     relief='sunken', expand_x=True)],
            [text_box('review_header_k', 3)],
        ])

        books = self.panel('review_books_panel_k', 'Book moves', [
            [text_box('review_book_k', 2)],
        ])

        moves = self.panel('review_moves_panel_k', 'Move list', [
            [text_box('review_move_list_k', REVIEW_MOVE_LIST_HEIGHT)],
            [status('review_nav_k', 'Position 0/0')],
        ])

        # Engine settings of a panel, changed in place; they are filled
        # by show_review_engine_settings().
        def label(text):
            return sg.Text(text, font=FONT_BASE, pad=((8, 3), 3))

        def hash_setting(role):
            return [sg.Text('Hash', font=FONT_BASE, pad=((0, 3), 3)),
                    sg.Combo([], key='review_{}_hash_k'.format(role),
                             size=(6, 1), font=FONT_BASE, readonly=True,
                             enable_events=True, pad=(0, 3),
                             tooltip='Hash table size of the engine'),
                    sg.Text('MB', font=FONT_BASE, pad=((3, 0), 3))]

        def number_setting(text, key, tooltip):
            return [label(text),
                    sg.Spin([1], initial_value=1, key=key, size=(3, 1),
                            font=FONT_BASE, readonly=True,
                            enable_events=True, pad=(0, 3), tooltip=tooltip)]

        def threads_setting(role):
            return number_setting(
                'Threads', 'review_{}_threads_k'.format(role),
                'Number of threads the engine searches with')

        # Each engine panel has its own on/off button beside its status,
        # its engine settings, and a box: the search figures on its first
        # line, then the score and the variation.
        threat = self.panel('review_threat_panel_k', 'Threat', [
            [button('Threat', 8, 'review_toggle_threat_k',
                    'Toggle threat analysis: engine analyses what the '
                    'opponent threatens if the side to move were to pass.'),
             status('review_threat_status_k', 'Threat stopped')],
            hash_setting('threat') + threads_setting('threat'),
            [text_box('review_threat_k', REVIEW_THREAT_BOX_HEIGHT,
                      text_color='red', wrap_lines=False)],
        ])

        analysis = self.panel('review_analysis_panel_k', 'Analysis', [
            [button('Analysis', 8, 'review_toggle_analysis_k',
                    'Toggle engine analysis for the current position.'),
             status('review_analysis_status_k', 'Analysis stopped')],
            hash_setting('analysis') + threads_setting('analysis')
            + number_setting('MultiPV', 'review_analysis_multipv_k',
                             'Number of best lines to show'),
            [text_box('review_analysis_k', REVIEW_ANALYSIS_BOX_HEIGHT,
                      wrap_lines=False)],
        ])

        self.review_menu_elem = sg.Menu(
            build_review_menu(analyzing=False), tearoff=False, font=MENU_FONT)

        layout = [
            [self.review_menu_elem],
            # One row holding the board box and every panel.
            [board_box, game_list, game, books, moves, threat, analysis],
            # Status bar along the bottom edge of the window.
            [sg.Text('Mode     Review', font=FONT_BASE, key='_gamestatus_',
                     relief='sunken', expand_x=True, pad=(0, (6, 0)))],
        ]

        return layout

    def create_review_window(self, location=None):
        """Create a review window."""
        # Built around the board size the user prefers; the board is
        # fitted to the window once the saved window size is restored.
        self.square_px = self.preferred_square_px
        layout = self.build_review_layout(self.is_white_at_bottom)
        window = sg.Window(
            '{} {}'.format(APP_NAME, APP_VERSION),
            layout,
            default_button_element_size=(12, 1),
            auto_size_buttons=False,
            finalize=True,
            resizable=True,
            location=location,
            icon=ico_path[platform]['pecg']
        )
        self.compact_review_buttons(window)
        self.bind_review_shortcuts(window)
        # Game list: the columns keep their width, so a panel too narrow
        # for them scrolls sideways instead of squeezing them all; only
        # the last one takes the spare width of a wider panel.
        tree = window['review_game_table_k'].Widget
        for heading in REVIEW_GAME_LIST_HEADINGS[:-1]:
            tree.column(heading, stretch=False)
        tree.column(REVIEW_GAME_LIST_HEADINGS[-1],
                    minwidth=tree.column(REVIEW_GAME_LIST_HEADINGS[-1],
                                         'width'))
        # Analysis and Threat boxes: how their text is drawn, and a redraw
        # when a box changes width, since the variations fill the line.
        for key, update in (
                ('review_analysis_k', self.update_review_analysis_panel),
                ('review_threat_k', self.update_review_threat_panel)):
            box = window[key].Widget
            box.tag_configure('figures', foreground=REVIEW_INFO_COLOR)
            box.tag_configure('score', font=FONT_BASE + ('bold',))

            def on_resize(event, update=update):
                try:
                    update(window)
                except tk.TclError:
                    pass    # the window is closing
            box.bind('<Configure>', on_resize, add='+')
        self.show_review_engine_settings(window)
        # Whether the window is maximized follows the Play window (see
        # start_review_mode), not what was saved.
        self.attach_panel_layout(window, 'review', restore_maximized=False)
        self.redraw_board(window)
        self.apply_menu_font(window)
        return window

    def bind_review_shortcuts(self, window):
        """Bind keyboard shortcuts on the Review window.

        Alt+A / Alt+T toggle analysis and threat; Left / Right step through
        the moves and Home / End jump to the first / last position. The
        bindings write the same event keys used by the buttons, so the
        existing event-loop handlers take over. Binding on the toplevel is
        safe: the review window has no editable text fields that need the
        arrow keys.
        """
        try:
            root = window.TKroot
            root.bind('<Alt-Key-a>',
                      lambda e: window.write_event_value(
                          'review_toggle_analysis_k', True))
            root.bind('<Alt-Key-t>',
                      lambda e: window.write_event_value(
                          'review_toggle_threat_k', True))
            root.bind('<Left>',
                      lambda e: window.write_event_value('Previous', True))
            root.bind('<Right>',
                      lambda e: window.write_event_value('Next', True))
            root.bind('<Home>',
                      lambda e: window.write_event_value('First', True))
            root.bind('<End>',
                      lambda e: window.write_event_value('Last', True))
        except Exception:
            logging.exception('Failed to bind review window shortcuts.')

    def compact_review_buttons(self, window):
        """Shrink the nav/toggle buttons' internal Tk padding.

        Classic Tk buttons default to padx='3m'/pady='1m' (~11 px per side on
        Linux/X11), which makes them much wider than on Windows. Force small,
        uniform padding so the four navigation buttons fit under the smallest
        board everywhere.
        """
        for key in ('First', 'Previous', 'Next', 'Last', 'Flip',
                    'review_toggle_analysis_k', 'review_toggle_threat_k'):
            element = window.find_element(key, silent_on_error=True)
            if element is None or element.Widget is None:
                continue
            try:
                element.Widget.configure(
                    padx=2, pady=2, borderwidth=1, highlightthickness=0)
            except Exception:
                logging.exception('Failed to compact review button %r', key)
        window.refresh()

    def apply_menu_font(self, window):
        """Match the Linux menubar font to the native Windows one.

        FreeSimpleGUI cannot set the menubar font (only submenus), so configure
        the underlying Tk menu widget directly. Only needed where Tk draws the
        menu (Linux); Windows/macOS use a native menubar and MENU_FONT is None.
        The setting survives Menu.update() (mode switches) because update() only
        rebuilds the submenu items, not the menubar's font.
        """
        if MENU_FONT is None:
            return
        try:
            root = window.TKroot
            menu_path = root.cget('menu')
            if menu_path:
                root.nametowidget(menu_path).configure(font=MENU_FONT)
                window.refresh()
        except Exception:
            logging.exception('Failed to set the menubar font')

    def start_review_mode(self, window):
        """Open review mode in a separate window."""
        if self.review_game is None:
            if self.review_games:
                selected_game_obj = self.load_review_game(
                    self.review_pgn_file, self.review_games[0])
                if selected_game_obj is not None:
                    self.prepare_review_game(selected_game_obj, 0)
                else:
                    self.prepare_review_game(chess.pgn.Game())
            else:
                self.prepare_review_game(chess.pgn.Game())

        location = window.CurrentLocation()
        # Carry the maximized state over to the Review window; its panel
        # layout then fits the board to the maximized size.
        was_maximized = self._is_window_maximized(window)
        # The board sizes when Review was entered: the one the Play window
        # shows, and the one the user wants.
        play_square_px = self.square_px
        wanted_square_px = self.preferred_square_px
        window.Hide()
        review_window = self.create_review_window(location=location)
        if was_maximized:
            self._set_window_maximized(review_window)
        self.review_window = review_window
        self.fill_review_game_list(review_window)
        self.mark_review_game(review_window)
        self.render_review_movelist(review_window)
        self.update_review_window(review_window)

        while True:
            button, value = review_window.Read(timeout=50)
            self.poll_review_analysis(review_window)
            self.poll_review_threat(review_window)
            self.poll_auto_analysis(review_window)

            # Skip timeout events as analysis updates are processed by
            # poll_review_analysis() and poll_review_threat() called earlier.
            if button == sg.TIMEOUT_KEY:
                # After navigation settles (debounce), restart each enabled role
                # that is still stale (its search was stopped by navigation and
                # not yet restarted). A role the user toggled on during the wait
                # is no longer stale, so it keeps running and its output shows.
                nav_time = self.review_nav_last_time
                if (nav_time
                        and time.time() - nav_time >= REVIEW_NAV_DEBOUNCE_SEC):
                    self.review_nav_last_time = 0
                    if self.review_analysis_enabled and self.review_analysis_stale:
                        self.start_review_analysis(review_window)
                    if self.review_threat_enabled and self.review_threat_stale:
                        self.start_review_threat(review_window)
                continue

            if button is None:
                self.cancel_auto_analysis(review_window)
                self.close_review_analysis()
                self.close_review_threat()
                review_window.Close()
                self.review_window = None
                sys.exit(0)

            if button == 'Play':
                self.cancel_auto_analysis(review_window)
                break

            if isinstance(button, str) and '::help_' in button:
                self.show_help_topic(button)
                continue

            if button == 'Select Game::review_select_game_k':
                selected_game = self.select_review_game(
                    self.review_pgn_file, self.review_games)
                if selected_game is None:
                    continue

                self.review_pgn_file = selected_game['pgn_file']
                self.review_games = selected_game['games']
                self.fill_review_game_list(review_window)
                self.show_review_game(
                    review_window, selected_game['game'],
                    selected_game['game_index'])
                self.save_settings()
                continue

            # The Game list panel: a click on a heading sorts by that
            # column, a selected row puts that game on the board.
            if button == 'review_game_table_k' or (
                    isinstance(button, tuple) and len(button) == 3
                    and button[0] == 'review_game_table_k'):
                clicked = button[2] if isinstance(button, tuple) else None
                if clicked is not None and clicked[0] == -1:
                    if clicked[1] is not None:
                        self.sort_review_game_list(review_window, clicked[1])
                else:
                    self.select_listed_review_game(review_window)
                continue

            if button == 'Auto-Analyze Game::review_auto_analyze_k':
                self.start_auto_analysis(review_window)
                continue

            if button == 'Cancel Analysis::review_cancel_analysis_k':
                self.cancel_auto_analysis(review_window)
                continue

            if button == 'Flip':
                # The board is a canvas and orientation is applied at draw
                # time: flipping is just a redraw, so the window and any
                # running analysis/threat searches are kept as they are.
                self.is_white_at_bottom = not self.is_white_at_bottom
                self.update_review_window(review_window)
                continue

            if isinstance(button, str) and ('::board_size_k' in button
                                            or '::layout_k' in button):
                self.handle_board_size_event(review_window, button)
                self.update_review_window(review_window)
                continue

            # Hash, Threads or MultiPV of the Analysis or Threat panel.
            if isinstance(button, str) and button.startswith('review_') \
                    and button.endswith(('_hash_k', '_threads_k',
                                         '_multipv_k')):
                self.change_review_engine_setting(
                    review_window, button, value.get(button))
                continue

            if button == 'review_toggle_analysis_k':
                # Toggle on the *enabled* flag, not whether a search is actively
                # computing: a finished analysis (time/depth cap reached) still
                # shows its results with search == None, and a press there must
                # stop/clear it, not restart it. A fresh search's output is no
                # longer discarded thanks to the per-role stale flag, so pressing
                # when off reliably starts and shows.
                if self.review_analysis_enabled:
                    logging.info('User toggled review analysis OFF.')
                    self.review_analysis_enabled = False
                    self.review_analysis_lines = {}
                    self.review_analysis_status = 'Analysis stopped'
                    self.stop_review_analysis()
                    self.update_review_analysis_panel(review_window)
                else:
                    logging.info('User toggled review analysis ON.')
                    self.start_review_analysis(review_window)
                continue

            if button == 'review_toggle_threat_k':
                # Toggle on the *enabled* flag (see analysis toggle above): a
                # finished threat search still shows its line with search == None,
                # and a press there must stop it, not restart it.
                if self.review_threat_enabled:
                    logging.info('User toggled review threat analysis OFF.')
                    self.review_threat_enabled = False
                    self.review_threat_line = None
                    self.review_threat_status = 'Threat stopped'
                    self.stop_review_threat()
                    self.update_review_threat_panel(review_window)
                else:
                    logging.info('User toggled review threat analysis ON.')
                    self.start_review_threat(review_window)
                continue

            position_changed = False
            if button == 'First':
                self.review_move_index = 0
                position_changed = True
            elif button == 'Previous':
                current_node = self.review_nodes[self.review_move_index]
                prev_node = current_node.parent if (current_node and hasattr(current_node, 'parent')) else None
                if prev_node in self.review_nodes:
                    self.review_move_index = self.review_nodes.index(prev_node)
                else:
                    self.review_move_index = 0
                position_changed = True
            elif button == 'Next':
                current_node = self.review_nodes[self.review_move_index]
                next_node = current_node.variations[0] if (current_node and current_node.variations) else None
                if next_node in self.review_nodes:
                    self.review_move_index = self.review_nodes.index(next_node)
                position_changed = True
            elif button == 'Last':
                current_node = self.review_nodes[self.review_move_index]
                node = current_node
                while node and node.variations:
                    node = node.variations[0]
                if node in self.review_nodes:
                    self.review_move_index = self.review_nodes.index(node)
                position_changed = True

            if position_changed:
                self.update_review_window(review_window)
                self.follow_review_position(review_window)

        self.close_review_analysis()
        self.close_review_threat()
        # Carry the maximized state back to the Play window.
        was_maximized = self._is_window_maximized(review_window)
        self.remember_layouts()
        self.panel_layouts['review'] = None
        review_window.Close()
        self.review_window = None
        self.reset_review_run_state()
        window.UnHide()
        if self.preferred_square_px != wanted_square_px:
            # A board size was chosen in Review (Board -> Size or a
            # divider): the Play window follows, as for its own menu.
            self.square_px = self.preferred_square_px
            self._apply_board_scale(window)
            self.sync_board_box(window)
            self.panel_layouts['play'].refit_later()
        else:
            # The Play window gets back the board it was showing.
            self.square_px = play_square_px
            self._apply_board_scale(window)
        if was_maximized:
            self._set_window_maximized(window)

    def get_engines(self):
        """
        Get engine filenames [a.exe, b.exe, ...]

        :return: list of engine filenames
        """
        engine_list = []
        engine_path = Path('Engines')
        files = os.listdir(engine_path)
        for file in files:
            if not file.endswith('.gz') and not file.endswith('.dll') \
                    and not file.endswith('.DS_Store') \
                    and not file.endswith('.bin') \
                    and not file.endswith('.dat'):
                engine_list.append(file)

        return engine_list

    def create_board(self, is_white_at_bottom=True):
        """
        Returns the board layout: a single Graph canvas.

        Orientation is no longer baked into the layout - it is applied at
        draw time by redraw_board/paint_square, which is what makes
        flipping a redraw instead of a window rebuild. The parameter is
        kept for call-site compatibility.
        """
        self.psg_board = copy.deepcopy(initial_board)
        # The canvas is the board plus the turn-marker strip on its right.
        width = self.board_px + TURN_MARKER_PX
        return [[sg.Graph(canvas_size=(width, self.board_px),
                          graph_bottom_left=(0, self.board_px),
                          graph_top_right=(width, 0),
                          background_color=sg.theme_background_color(),
                          pad=(0, 0), key='_board_graph_k',
                          enable_events=False, drag_submits=False)]]

    def panel(self, key, title, rows):
        """Return a panel: a column with a title bar above ``rows``.

        The title bar is what identifies the panel; PanelLayout decides
        where the panel goes and how big it is.
        """
        title_bar = sg.Text(' ' + title, font=FONT_PANEL_TITLE,
                            text_color=sg.theme_input_text_color(),
                            background_color=sg.theme_input_background_color(),
                            pad=(0, 0), expand_x=True, key=key + '_title')
        body = sg.Column(rows, pad=(6, 4), expand_x=True, expand_y=True)
        return sg.Column([[title_bar], [body]], key=key, pad=(0, 0),
                         expand_x=True, expand_y=True)

    def build_main_layout(self, is_white_at_bottom=True):
        """
        Creates all elements for the Play window: the board box and one
        panel per group of controls, all in a single layout row. Their
        placement is taken over by PanelLayout in finish_play_window().

        :param is_white_at_bottom: board orientation, white pieces at
        the bottom when True.
        :return: GUI layout
        """
        self.set_window_style()

        board_box = sg.Column(self.create_board(is_white_at_bottom),
                              key='play_board_box_k', pad=(0, 0))

        def player_row(label, name_key, default_name, base_key, elapse_key):
            # The time boxes are wider than their longest text, which is
            # centred: remaining time up to '10h:00m:00s' (11 characters),
            # elapsed time up to '100m:00s' (8). The name takes the rest
            # of the row.
            return [sg.Text(label, size=(6, 1), font=FONT_BASE),
                    sg.Text(default_name, font=FONT_BASE, key=name_key,
                            size=(17, 1), relief='sunken', expand_x=True),
                    sg.Text('', font=FONT_BASE, key=base_key,
                            size=(12, 1), relief='sunken',
                            justification='center'),
                    sg.Text('', font=FONT_BASE, key=elapse_key, size=(9, 1),
                            relief='sunken', justification='center')]

        players = self.panel('play_players_panel_k', 'Players', [
            player_row('White', '_White_', 'Human',
                       'w_base_time_k', 'w_elapse_k'),
            player_row('Black', '_Black_', 'Computer',
                       'b_base_time_k', 'b_elapse_k'),
        ])

        moves = self.panel('play_moves_panel_k', 'Move list', [
            [sg.Multiline('', do_not_clear=True, autoscroll=True, size=(48, 6),
                          font=FONT_BASE, key='_movelist_', disabled=True,
                          expand_x=True, expand_y=True)],
        ])

        comment = self.panel('play_comment_panel_k', 'Comment', [
            [sg.Multiline('', do_not_clear=True, autoscroll=True, size=(48, 2),
                          font=FONT_BASE, key='comment_k', expand_x=True,
                          expand_y=True)],
        ])

        def book_column(label, menu_key, text_key):
            return sg.Column([
                [sg.Text(label, font=FONT_BASE, expand_x=True,
                         right_click_menu=['Right', ['Show::' + menu_key,
                                                     'Hide::' + menu_key]])],
                [sg.Multiline('', do_not_clear=True, autoscroll=False,
                              size=(22, 3), font=FONT_BASE, key=text_key,
                              disabled=True, expand_x=True, expand_y=True)],
            ], pad=(0, 0), expand_x=True, expand_y=True)

        books = self.panel('play_books_panel_k', 'Opening books', [
            [book_column('BOOK 1, Comp games', 'right_book1_k',
                         'polyglot_book1_k'),
             book_column('BOOK 2, Human games', 'right_book2_k',
                         'polyglot_book2_k')],
        ])

        engine = self.panel('play_engine_panel_k', 'Engine', [
            [sg.Text('Adviser', size=(8, 1), font=FONT_BASE, key='adviser_k',
                     right_click_menu=[
                        'Right',
                        ['Start::right_adviser_k', 'Stop::right_adviser_k']
                    ]),
             sg.Text('', font=FONT_BASE, key='advise_info_k', relief='sunken',
                     size=(38, 1), expand_x=True)],
            [sg.Text('Opponent Search Info', font=FONT_BASE, expand_x=True,
                     right_click_menu=['Right',
                                       ['Show::right_search_info_k',
                                        'Hide::right_search_info_k']])],
            [sg.Text('', key='search_info_all_k', size=(47, 1),
                     font=FONT_BASE, relief='sunken', expand_x=True)],
        ])

        self.menu_elem = sg.Menu(self.current_menu_def, tearoff=False,
                                 font=MENU_FONT)

        layout = [
                [self.menu_elem],
                # One row holding the board box and every panel.
                [board_box, players, moves, comment, books, engine],
                # Status bar along the bottom edge of the window.
                [sg.Text('Mode     Play', font=FONT_BASE, key='_gamestatus_',
                         relief='sunken', expand_x=True, pad=(0, (6, 0)))],
        ]

        return layout

    def finish_play_window(self, window):
        """Set up a newly built Play window: panel placement (restoring
        the saved arrangement and sizes), board input and the menubar
        font."""
        self.attach_panel_layout(window, 'play')

        # Set up drag-and-drop bindings for board squares
        self.setup_board_drag_drop(window)
        self.redraw_board(window)

        # Match the Linux menubar font to Windows (no-op on Windows/macOS).
        self.apply_menu_font(window)

    def attach_panel_layout(self, window, mode, restore_maximized=True):
        """Hand the placement of the panels of a newly built 'play' or
        'review' window to a PanelLayout: draw the panel borders and
        restore the arrangement, sizes and window size saved for that
        mode (and whether it was maximized, with ``restore_maximized``).
        """
        spec = PANEL_LAYOUTS[mode]
        for key in spec['panels']:
            window[key].Widget.config(highlightthickness=1,
                                      highlightbackground=PANEL_BORDER_COLOR,
                                      highlightcolor=PANEL_BORDER_COLOR)

        # A window that replaces another one (theme or colour change)
        # starts from the layout the user had in the old one.
        if self.panel_layouts[mode] is not None:
            self.remember_layouts()

        # Height of what is fixed under the board in its box (the row
        # holding it, so its padding counts).
        extra_px = 0
        if spec['below_board']:
            window.TKroot.update_idletasks()
            extra_px = window[spec['below_board']].Widget.master \
                .winfo_reqheight()

        layout = PanelLayout(
            window, spec['board'], spec['panels'],
            on_resize=lambda room, grow_only: self.fit_board(
                window, room, grow_only),
            on_change=self.remember_layouts,
            stretch_panels=spec['stretch'],
            divider_color=sg.theme_background_color(),
            marker_color=TURN_MARKER_ON, board_extra_px=extra_px)
        self.panel_layouts[mode] = None   # no callbacks act until it is ready
        layout.set_board_box(self.board_px + TURN_MARKER_PX, self.board_px)

        saved = self.panel_layout_states[mode]
        if not isinstance(saved, dict):
            saved = {}
        layout.arrange(saved.get('arrangement')
                       or spec['arrangements'][DEFAULT_ARRANGEMENT],
                       sizes=saved if saved else None)
        size = saved.get('window')
        try:
            if restore_maximized and saved.get('maximized'):
                self._set_window_maximized(window)
            elif isinstance(size, list) and len(size) == 2:
                root = window.TKroot
                root.geometry('{}x{}'.format(
                    max(400, min(int(size[0]),
                                 root.winfo_screenwidth() - 40)),
                    max(300, min(int(size[1]),
                                 root.winfo_screenheight() - 100))))
        except (TypeError, ValueError, tk.TclError):
            logging.exception('Failed to restore the window size.')
        self.panel_layouts[mode] = layout

    def panel_layout_of(self, window):
        """Return (mode, PanelLayout) for a window whose panels are placed
        by a PanelLayout, or (None, None)."""
        for mode, layout in self.panel_layouts.items():
            if layout is not None and layout.window is window:
                return mode, layout
        return None, None

    def remember_layouts(self):
        """Keep the current arrangement and sizes of the window that is
        showing, and save them with the other settings."""
        changed = False
        for mode, layout in self.panel_layouts.items():
            if layout is None:
                continue
            try:
                # The Play window is hidden while Review is open; what it
                # reports then is not how the user left it.
                if layout.root.state() == 'withdrawn':
                    continue
                state = layout.state()
            except tk.TclError:
                continue        # the window is gone; keep what we had
            old = self.panel_layout_states[mode]
            if 'window' not in state and isinstance(old, dict) \
                    and 'window' in old:
                # Maximized: remember the size it had before that.
                state['window'] = old['window']
            self.panel_layout_states[mode] = state
            changed = True
        if changed:
            self.save_settings()

    def handle_layout_event(self, window, button):
        """Apply a View menu selection ('<label>::layout_k:<action>:...'):
        a ready-made arrangement, one panel to another zone, or a reset."""
        mode, layout = self.panel_layout_of(window)
        if layout is None:
            return
        arrangements = PANEL_LAYOUTS[mode]['arrangements']
        parts = str(button).split('::layout_k:', 1)[-1].split(':')
        if parts[0] == 'reset':
            self.reset_layout(window)
        elif parts[0] == 'preset' and parts[1] in arrangements:
            self.use_preferred_board(window)
            layout.arrange(arrangements[parts[1]], natural=True)
            layout.refit_later()
        elif parts[0] == 'move' and len(parts) == 3:
            layout.move_panel(parts[2], parts[1])

    def reset_layout(self, window):
        """Back to the default arrangement, sizes and window size."""
        mode, layout = self.panel_layout_of(window)
        if layout is None:
            return
        root = window.TKroot
        try:
            if layout.is_maximized():
                if root.state() == 'zoomed':
                    root.state('normal')
                else:
                    root.wm_attributes('-zoomed', 0)
                # Let the window take its un-maximized size before it is
                # measured (idle tasks alone leave its content at the old
                # size).
                root.update()
        except tk.TclError:
            pass
        self.use_preferred_board(window)
        layout.arrange(PANEL_LAYOUTS[mode]['arrangements'][DEFAULT_ARRANGEMENT],
                       natural=True)
        # None in the settings means "the default layout".
        self.panel_layout_states[mode] = None
        self.save_settings()

    def use_preferred_board(self, window):
        """Put the board and its box back at the preferred size, before
        the window is sized around a new arrangement."""
        layout = self.panel_layout_of(window)[1]
        if layout is None:
            return
        if self.square_px != self.preferred_square_px:
            self.square_px = self.preferred_square_px
            self._apply_board_scale(window)
        layout.set_board_box(self.board_px + TURN_MARKER_PX, self.board_px)

    def fit_board(self, window, room=None, grow_only=False):
        """Choose the board size for the room the window has.

        The board is as large as the size the user prefers (picked from
        Board -> Size or by dragging a divider next to the board), reduced
        while the window is too small for it. The board box is kept exactly
        as wide as the board, so the panels get all the remaining width.

        ``room`` is the (width, height) the user left for the board by
        dragging a divider next to it, or None. With ``grow_only`` that
        room can only make the preferred size larger (the layout itself
        keeps a board from being too large for it).
        """
        layout = self.panel_layout_of(window)[1]
        if layout is None:
            return
        if room is not None:
            # The user made this room by hand: that is the size they want.
            square_px = fit_square_px(
                min(room[0] - TURN_MARKER_PX, room[1]) // 8)
            if not grow_only or square_px > self.preferred_square_px:
                self.preferred_square_px = square_px
        max_width, max_height = layout.board_space()
        square_px = fit_square_px(min(self.preferred_square_px,
                                      (max_width - TURN_MARKER_PX) // 8,
                                      max_height // 8))
        if square_px != self.square_px:
            self.square_px = square_px
            self._apply_board_scale(window)
        layout.set_board_box(self.board_px + TURN_MARKER_PX, self.board_px)
        # Window size, dividers and board size are saved together.
        self.remember_layouts()

    def set_board_square(self, window, square_px):
        """Board -> Size: make this the preferred board size, resize the
        board and its box and let the window follow."""
        self.preferred_square_px = fit_square_px(square_px)
        self.square_px = self.preferred_square_px
        self._apply_board_scale(window)
        self.sync_board_box(window)
        self.save_settings()

    def sync_board_box(self, window):
        """Give the window's board box the size of the current board
        (after Board -> Size, or a size change made in the other mode)."""
        layout = self.panel_layout_of(window)[1]
        if layout is None:
            return
        box = (self.board_px + TURN_MARKER_PX, self.board_px)
        layout.resize_window_for_board_box(*box)
        layout.set_board_box(*box)

    def set_default_adviser_engine(self):
        try:
            self.adviser_id_name = self.engine_id_name_list[1] \
                   if len(self.engine_id_name_list) >= 2 \
                   else self.engine_id_name_list[0]
            self.adviser_file, self.adviser_path_and_file = \
                self.get_engine_file(self.adviser_id_name)
        except IndexError as e:
            logging.warning(e)
        except Exception:
            logging.exception('Error in getting adviser engine!')

    def set_default_analysis_engine(self):
        """Define the default engine used by Review mode analysis."""
        try:
            self.analysis_id_name = self.engine_id_name_list[0]
            self.analysis_file, self.analysis_path_and_file = \
                self.get_engine_file(self.analysis_id_name)
        except IndexError as e:
            logging.warning(e)
        except Exception:
            logging.exception('Error in getting analysis engine!')

    def set_default_threat_engine(self):
        """Define the default engine used by Review mode threat analysis."""
        try:
            self.threat_id_name = self.engine_id_name_list[0]
            self.threat_file, self.threat_path_and_file = \
                self.get_engine_file(self.threat_id_name)
        except IndexError as e:
            logging.warning(e)
        except Exception:
            logging.exception('Error in getting threat engine!')

    def get_default_engine_opponent(self):
        engine_id_name = None
        try:
            engine_id_name = self.opp_id_name = self.engine_id_name_list[0]
            self.opp_file, self.opp_path_and_file = self.get_engine_file(
                engine_id_name)
        except IndexError as e:
            logging.warning(e)
        except Exception:
            logging.exception('Error in getting opponent engine!')

        return engine_id_name

    def handle_setup_event(self, button, window):
        """Handle an idle-state (game not started) setup menu event.

        These handlers are shared by the Play mode loops; most open a modal
        dialog over the still-visible main window (begin_dialog/end_dialog
        keep it inert), while theme and board color changes rebuild the
        main window.

        :return: (is_handled, window) - window is the (possibly rebuilt)
            main window.
        """
        is_handled = True
        while True:
            # Idle setup, Delete player
            if button == 'Delete Player::delete_player_k':
                win_title = 'Settings/PGN/Delete Player'
                player_list = []
                sum_games = 0
                layout = [
                    [sg.Text('PGN', size=(4, 1)),
                     sg.Input(size=(40, 1), key='pgn_k'), sg.FileBrowse()],
                    [sg.Button('Display Players', size=(53, 1))],
                    [sg.Text('Status:', size=(53, 1), key='status_k', relief='sunken')],
                    [sg.T('Current players in the pgn', size=(43, 1))],
                    [sg.Listbox([], size=(53, 10), key='player_k')],
                    [sg.Button('Delete Player'), sg.Cancel()]
                ]

                self.begin_dialog(window)
                w = sg.Window(win_title, layout,
                              icon=ico_path[platform]['pecg'], modal=True)
                while True:
                    e, v = w.Read(timeout=10)
                    if e is None or e == 'Cancel':
                        break
                    if e == 'Display Players':
                        pgn = v['pgn_k']
                        if pgn == '':
                            logging.info('Missing pgn file.')
                            sg.popup(
                                'Please locate your pgn file by pressing \
                                the Browse button followed by Display Players.',
                                title=win_title,
                                icon=ico_path[platform]['pecg']
                            )
                            break

                        if not os.path.isfile(pgn):
                            w.Element('status_k').Update(
                                'Status: PGN file not found.')
                            continue

                        t1 = time.perf_counter()
                        que = queue.Queue()
                        t = threading.Thread(
                            target=self.get_players,
                            args=(pgn, que,),
                            daemon=True
                        )
                        t.start()
                        w.Element('status_k').Update(
                            'Display Players: processing ...')
                        while True:
                            e1, v1 = w.Read(timeout=100)
                            try:
                                msg = que.get_nowait()
                                break
                            except queue.Empty:
                                continue
                        t.join()

                        # None: the worker could not read the file.
                        if msg is None:
                            w.Element('status_k').Update(
                                'Status: Cannot read the PGN file, '
                                'see pecg_log.txt.')
                            continue

                        elapse = int(time.perf_counter() - t1)
                        w.Element('status_k').Update(
                            'Players are displayed. Done! in ' +
                            str(elapse) + 's')
                        player_list = msg[0]
                        sum_games = msg[1]
                        w.Element('player_k').Update(sorted(player_list))

                    if e == 'Delete Player':
                        try:
                            player_name = v['player_k'][0]
                        except IndexError as e:
                            logging.info(e)
                            sg.popup('Please locate your pgn file by '
                                     'pressing the Browse button followed by Display Players.',
                                     title=win_title,
                                     icon=ico_path[platform]['pecg'])
                            break
                        except Exception:
                            logging.exception('Failed to get player.')
                            break

                        if not os.path.isfile(v['pgn_k']):
                            w.Element('status_k').Update(
                                'Status: PGN file not found.')
                            continue

                        t1 = time.perf_counter()
                        que = queue.Queue()
                        t = threading.Thread(
                            target=self.delete_player,
                            args=(player_name, v['pgn_k'], que,),
                            daemon=True
                        )
                        t.start()
                        w.Element('status_k').Update(
                            'Status: Delete: processing ...')
                        msg = None
                        while msg not in ('Done', 'Failed'):
                            e1, v1 = w.Read(timeout=100)
                            # Take everything the worker has posted so far
                            # and show only the latest progress line.
                            progress = None
                            while msg not in ('Done', 'Failed'):
                                try:
                                    msg = que.get_nowait()
                                except queue.Empty:
                                    break
                                progress = msg
                            if progress not in (None, 'Done', 'Failed'):
                                w.Element('status_k').Update(
                                    progress + '/' + str(sum_games))
                        t.join()

                        if msg == 'Failed':
                            w.Element('status_k').Update(
                                'Status: Delete failed, see pecg_log.txt.')
                            continue

                        elapse = int(time.perf_counter() - t1)
                        w.Element('status_k').Update(
                            player_name + ' was deleted. Done! '
                            'in ' + str(elapse) + 's')

                        # Update player list in listbox
                        player_list.remove(player_name)
                        w.Element('player_k').Update(sorted(player_list))

                w.Close()
                self.end_dialog(window)
                break

            # Idle setup, Set User time control
            if button == 'User::tc_k':
                win_title = 'Settings/Time/User'
                layout = self.time_control_rows(
                    self.human_base_time_ms, self.human_inc_time_ms) + [
                    [sg.T('Period moves', size=(16, 1), visible=False),
                     sg.Input(self.human_period_moves, key='period_moves_k',
                              size=(8, 1), visible=False)],
                    [sg.Radio('Fischer', 'tc_radio', key='fischer_type_k',
                              default=True if self.human_tc_type == 'fischer' else False),
                     sg.Radio('Delay', 'tc_radio', key='delay_type_k',
                              default=True if self.human_tc_type == 'delay' else False)],
                    [sg.OK(), sg.Cancel()]
                ]

                self.begin_dialog(window)
                w = sg.Window(win_title, layout,
                              icon=ico_path[platform]['pecg'], modal=True)
                while True:
                    e, v = w.Read(timeout=10)
                    if e is None:
                        break
                    if e == 'Cancel':
                        break
                    if e == 'OK':
                        tc_times = self.read_time_control(v, win_title)
                        if tc_times is None:
                            continue
                        base_time_ms, inc_time_ms = tc_times
                        period_moves = int(v['period_moves_k'])

                        tc_type = 'fischer'
                        if v['fischer_type_k']:
                            tc_type = 'fischer'
                        elif v['delay_type_k']:
                            tc_type = 'delay'

                        self.human_base_time_ms = base_time_ms
                        self.human_inc_time_ms = inc_time_ms
                        self.human_period_moves = period_moves
                        self.human_tc_type = tc_type
                        break
                w.Close()
                self.end_dialog(window)
                break

            # Idle setup, Set engine time control
            if button == 'Engine::tc_k':
                win_title = 'Settings/Time/Engine'
                layout = self.time_control_rows(
                    self.engine_base_time_ms, self.engine_inc_time_ms) + [
                    [sg.T('Period moves', size=(16, 1), visible=False),
                     sg.Input(self.engine_period_moves,
                              key='period_moves_k', size=(8, 1),
                              visible=False)],
                    [sg.Radio('Fischer', 'tc_radio', key='fischer_type_k',
                              default=True if
                              self.engine_tc_type == 'fischer' else False),
                     sg.Radio('Time Per Move', 'tc_radio', key='timepermove_k',
                              default=True if
                              self.engine_tc_type == 'timepermove' else
                              False, tooltip='Only base time will be used.')
                     ],
                    [sg.OK(), sg.Cancel()]
                ]

                self.begin_dialog(window)
                w = sg.Window(win_title, layout,
                              icon=ico_path[platform]['pecg'], modal=True)
                while True:
                    e, v = w.Read(timeout=10)
                    if e is None:
                        break
                    if e == 'Cancel':
                        break
                    if e == 'OK':
                        tc_times = self.read_time_control(v, win_title)
                        if tc_times is None:
                            continue
                        base_time_ms, inc_time_ms = tc_times
                        period_moves = int(v['period_moves_k'])

                        tc_type = 'fischer'
                        if v['fischer_type_k']:
                            tc_type = 'fischer'
                        elif v['timepermove_k']:
                            tc_type = 'timepermove'

                        self.engine_base_time_ms = base_time_ms
                        self.engine_inc_time_ms = inc_time_ms
                        self.engine_period_moves = period_moves
                        self.engine_tc_type = tc_type
                        break
                w.Close()
                self.end_dialog(window)
                break

            # Idle setup, manage player names
            if button == 'User Name::user_name_k':
                win_title = 'Settings/User Name'
                names = self.get_usernames() or [self.username]
                preselect = [self.username] if self.username in names else []
                layout = [
                    [sg.Text('Current player:', size=(13, 1)),
                     sg.Text(self.username, key='user_current_k',
                             font=('Helvetica', 10, 'bold'), size=(28, 1))],
                    [sg.HorizontalSeparator()],
                    [sg.Text('Add a new name')],
                    [sg.Input('', key='user_new_k', size=(30, 1),
                              tooltip='Type a name and press Save and Use'),
                     sg.Button('Save and Use', key='user_save_k')],
                    [sg.HorizontalSeparator()],
                    [sg.Text('Saved players (double-click to use)')],
                    [sg.Listbox(values=names, size=(44, 8), key='user_list_k',
                                default_values=preselect)],
                    [sg.Button('Use Selected', key='user_use_k'),
                     sg.Button('Delete', key='user_del_k'),
                     sg.Button('Close')],
                ]
                self.begin_dialog(window)
                w = sg.Window(win_title, layout,
                              icon=ico_path[platform]['pecg'], finalize=True,
                              modal=True)
                # Keyboard / double-click affordances bound directly on the
                # tk widgets (the element kwargs are unavailable in this
                # FreeSimpleGUI version).
                try:
                    w['user_new_k'].Widget.bind(
                        '<Return>',
                        lambda e: w.write_event_value('user_save_k', True))
                    w['user_list_k'].Widget.bind(
                        '<Double-Button-1>',
                        lambda e: w.write_event_value('user_use_k', True))
                    w['user_list_k'].Widget.bind(
                        '<Return>',
                        lambda e: w.write_event_value('user_use_k', True))
                except Exception:
                    logging.exception('Failed to bind user dialog keys.')

                def _refresh_users():
                    names2 = self.get_usernames() or [self.username]
                    idx = [names2.index(self.username)] \
                        if self.username in names2 else None
                    w['user_list_k'].Update(values=names2, set_to_index=idx)
                    w['user_current_k'].Update(self.username)

                while True:
                    e, v = w.Read()
                    if e in (None, 'Close'):
                        break
                    if e in ('user_save_k', 'user_new_k'):
                        if not (v['user_new_k'] and v['user_new_k'].strip()):
                            sg.popup('Please enter a name.', title=win_title,
                                     icon=ico_path[platform]['pecg'])
                            continue
                        self.set_current_user(v['user_new_k'])
                        w['user_new_k'].Update('')
                        _refresh_users()
                    elif e in ('user_use_k', 'user_list_k'):
                        sel = v['user_list_k']
                        if not sel:
                            if e == 'user_use_k':
                                sg.popup('Please select a saved player.',
                                         title=win_title,
                                         icon=ico_path[platform]['pecg'])
                            continue
                        self.set_current_user(sel[0])
                        _refresh_users()
                    elif e == 'user_del_k':
                        sel = v['user_list_k']
                        if not sel:
                            sg.popup('Please select a saved player to delete.',
                                     title=win_title,
                                     icon=ico_path[platform]['pecg'])
                            continue
                        if sg.popup_yes_no(
                                'Delete player "{}"?'.format(sel[0]),
                                title=win_title,
                                icon=ico_path[platform]['pecg']) == 'Yes':
                            self.delete_username(sel[0])
                            _refresh_users()
                w.Close()
                self.end_dialog(window)
                self.update_labels_and_game_tags(window, human=self.username)
                break

            # Idle setup
            if button == 'Install':
                button_title = 'Engine/Manage/' + button
                new_engine_path_file, new_engine_id_name = None, None

                install_layout = [
                        [sg.Text('Current configured engine names')],
                        [sg.Listbox(values=self.engine_id_name_list,
                                    size=(48, 10), disabled=True)],
                        [sg.Button('Add'), sg.Button('Cancel')]
                ]

                self.begin_dialog(window)
                install_win = sg.Window(title=button_title,
                                        layout=install_layout,
                                        icon=ico_path[platform]['pecg'],
                                        modal=True)

                while True:
                    e, v = install_win.Read(timeout=100)
                    if e is None or e == 'Cancel':
                        break
                    if e == 'Add':
                        button_title += '/' + e

                        add_layout = [
                            [sg.Text('Engine', size=(6, 1)), sg.Input(key='engine_path_file_k'), sg.FileBrowse()],
                            [
                                sg.Text('Name', size=(6, 1)),
                                sg.Input(key='engine_id_name_k', tooltip='Input name'),
                                sg.Button('Get Id Name')
                            ],
                            [sg.OK(), sg.Cancel()]
                        ]

                        add_win = sg.Window(button_title, add_layout,
                                            modal=True)
                        is_cancel_add_win = False
                        while True:
                            e1, v1 = add_win.Read(timeout=100)
                            if e1 is None:
                                is_cancel_add_win = True
                                break
                            if e1 == 'Cancel':
                                is_cancel_add_win = True
                                break
                            if e1 == 'Get Id Name':
                                new_engine_path_file = v1['engine_path_file_k']

                                # We can only get the engine id name if the engine is defined.
                                if new_engine_path_file.strip():
                                    que = queue.Queue()
                                    t = threading.Thread(
                                        target=self.get_engine_id_name,
                                        args=(new_engine_path_file, que,),
                                        daemon=True
                                    )
                                    t.start()
                                    is_update_list = False
                                    # The worker always answers; wait for
                                    # it without spinning the CPU.
                                    msg = que.get()
                                    t.join()

                                    if msg[0] == 'Done' and msg[1] is not None:
                                        is_update_list = True
                                        new_engine_id_name = msg[1]
                                    else:
                                        is_cancel_add_win = True
                                        sg.popup(
                                            'This engine cannot be '
                                            'installed. Please select '
                                            'another engine. It should be uci '
                                            'engine.',
                                            title=button_title + '/Get Id name')

                                    if is_update_list:
                                        add_win.Element('engine_id_name_k').Update(
                                            new_engine_id_name)

                                    # If we fail to install the engine, we exit
                                    # the install window
                                    if is_cancel_add_win:
                                        break

                                else:
                                    sg.popup(
                                        'Please define the engine or browse to the location of the engine file first.',
                                        title=button_title + '/Get Id name'
                                    )

                            if e1 == 'OK':
                                try:
                                    new_engine_path_file = v1[
                                        'engine_path_file_k']
                                    new_engine_id_name = v1['engine_id_name_k']

                                    # The engine file is required; a name
                                    # alone cannot be installed.
                                    if not new_engine_path_file.strip():
                                        sg.popup(
                                            'Please define the engine or browse to the location of the engine file first.',
                                            title=button_title,
                                            icon=ico_path[platform]['pecg']
                                        )
                                        continue

                                    if new_engine_id_name != '':
                                        # Check if new_engine_id_name is already existing
                                        if self.is_name_exists(new_engine_id_name):
                                            sg.popup(
                                                f'{new_engine_id_name} is existing. Please modify the name! \
                                                You can modify the config later thru Engine->Manage->Edit',
                                                title=button_title,
                                                icon=ico_path[platform]['pecg']
                                            )
                                            continue
                                        break
                                    else:
                                        sg.popup(
                                            'Please input engine id name, or press Get Id Name button.',
                                            title=button_title,
                                            icon=ico_path[platform]['pecg']
                                        )
                                except Exception:
                                    logging.exception('Failed to get engine '
                                                      'path and file')

                        # Outside add window while loop
                        add_win.Close()
                        try:
                            install_win.make_modal()
                        except Exception:
                            pass

                        # Save the new configured engine to pecg_engines.json.
                        if not is_cancel_add_win:
                            que = queue.Queue()
                            t = threading.Thread(
                                target=self.add_engine_to_config_file,
                                args=(new_engine_path_file,
                                      new_engine_id_name, que,), daemon=True)
                            t.start()
                            while True:
                                try:
                                    msg = que.get_nowait()
                                    break
                                except Exception:
                                    continue
                            t.join()

                            if msg == 'Failure':
                                sg.popup(
                                    f'Failed to add {new_engine_id_name} in config file!',
                                    title=button_title,
                                    icon=ico_path[platform]['pecg']
                                )

                            self.engine_id_name_list = \
                                self.get_engine_id_name_list()
                        break

                install_win.Close()
                self.end_dialog(window)

                # Define default engine opponent, adviser, analysis, threat
                if self.opp_id_name is None:
                    self.get_default_engine_opponent()
                if self.adviser_id_name is None:
                    self.set_default_adviser_engine()
                if self.analysis_id_name is None:
                    self.set_default_analysis_engine()
                if self.threat_id_name is None:
                    self.set_default_threat_engine()

                self.update_labels_and_game_tags(window, human=self.username)

                break

            # Idle setup
            if button == 'Edit':
                button_title = 'Engine/Manage/' + button
                opt_name = []
                ret_opt_name = []
                engine_path_file, engine_id_name = None, None

                edit_layout = [
                        [sg.Text('Current configured engine names')],
                        [
                            sg.Listbox(
                                values=self.engine_id_name_list,
                                size=(48, 10),
                                key='engine_id_name_k'
                            )
                        ],
                        [sg.Button('Modify'), sg.Button('Cancel')]
                ]

                self.begin_dialog(window)
                edit_win = sg.Window(
                    button_title,
                    layout=edit_layout,
                    icon=ico_path[platform]['pecg'],
                    modal=True
                )
                is_cancel_edit_win = False
                while True:
                    e, v = edit_win.Read(timeout=100)
                    if e is None or e == 'Cancel':
                        is_cancel_edit_win = True
                        break
                    if e == 'Modify':
                        button_title += '/' + e

                        try:
                            orig_idname = engine_id_name = v['engine_id_name_k'][0]
                        except Exception:
                            sg.popup('Please select an engine to modify.',
                                     title='/Edit/Modify',
                                     icon=ico_path[platform]['pecg'])
                            continue

                        # Locate the engine record (path + options).
                        with open(self.engine_config_file, 'r') as json_file:
                            data = json.load(json_file)
                        option = []
                        engine_path_file = None
                        for p in data:
                            if p['name'] == engine_id_name:
                                engine_path_file = Path(
                                    p['workingDirectory'], p['command'])
                                option = p['options']
                                break

                        opt_layout, opt_layout2, opt_meta = \
                            self.build_engine_options_layout(option)
                        # Prepend the engine-name field (renames the engine).
                        opt_layout = [
                            [sg.Text('name', size=(4, 1)),
                             sg.Input(engine_id_name, size=(38, 1),
                                      key='string_name_k')]] + opt_layout
                        modify_layout = self._build_options_window_layout(
                            opt_layout, opt_layout2)

                        modify_win = sg.Window(button_title,
                                               layout=modify_layout,
                                               icon=ico_path[platform]['pecg'],
                                               resizable=True, finalize=True,
                                               modal=True)
                        is_cancel_modify_win = False
                        while True:
                            e1, v1 = modify_win.Read(timeout=100)
                            if e1 is None or e1 == 'Cancel':
                                is_cancel_modify_win = True
                                break
                            if e1 == 'OK':
                                # The name identifies the engine: it must
                                # not be empty or used by another engine.
                                new_name = v1['string_name_k'].strip()
                                if not new_name:
                                    sg.popup(
                                        'Please input engine id name.',
                                        title=button_title,
                                        icon=ico_path[platform]['pecg'])
                                    continue
                                if new_name != orig_idname and \
                                        self.is_name_exists(new_name):
                                    sg.popup(
                                        f'{new_name} is existing. '
                                        'Please modify the name!',
                                        title=button_title,
                                        icon=ico_path[platform]['pecg'])
                                    continue

                                # Keep the window open on a bad number.
                                if not self.check_spin_options(
                                        v1, opt_meta, button_title):
                                    continue

                                engine_id_name = new_name
                                ret_opt_name = [
                                    {n: val} for n, val in
                                    self.read_option_values(
                                        v1, opt_meta).items()]
                                break

                        modify_win.Close()
                        try:
                            edit_win.make_modal()
                        except Exception:
                            pass
                        break  # Get out of edit_win loop

                # Outside edit_win while loop

                # Save the new configured engine to pecg_engines.json file
                if not is_cancel_edit_win and not is_cancel_modify_win:
                    self.update_engine_to_config_file(
                        engine_path_file, engine_id_name,
                        orig_idname, ret_opt_name)
                    self.engine_id_name_list = self.get_engine_id_name_list()

                    # A renamed engine keeps its roles and overrides.
                    if engine_id_name != orig_idname:
                        self.rename_engine_references(
                            orig_idname, engine_id_name)
                        self.update_labels_and_game_tags(
                            window, human=self.username)

                edit_win.Close()
                self.end_dialog(window)
                break

            # Idle setup
            if button == 'Delete':
                button_title = 'Engine/Manage/' + button
                delete_layout = [
                    [sg.Text('Current configured engine names')],
                    [sg.Listbox(values=self.engine_id_name_list, size=(48, 10),
                                key='engine_id_name_k')],
                    [sg.Button('Delete'), sg.Cancel()]
                ]
                self.begin_dialog(window)
                delete_win = sg.Window(
                    button_title,
                    layout=delete_layout,
                    icon=ico_path[platform]['pecg'],
                    modal=True
                )
                is_cancel = False
                while True:
                    e, v = delete_win.Read(timeout=100)
                    if e is None or e == 'Cancel':
                        is_cancel = True
                        break
                    if e == 'Delete':
                        try:
                            engine_id_name = v['engine_id_name_k'][0]
                        except Exception:
                            sg.popup('Please select an engine to delete.',
                                     title=button_title,
                                     icon=ico_path[platform]['pecg'])
                            continue
                        with open(self.engine_config_file, 'r') as json_file:
                            data = json.load(json_file)

                        for i in range(len(data)):
                            if data[i]['name'] == engine_id_name:
                                logging.info('{} is found for deletion.'.format(
                                    engine_id_name))
                                data.pop(i)
                                break

                        # Save data to pecg_engines.json
                        with open(self.engine_config_file, 'w') as h:
                            json.dump(data, h, indent=4)

                        break

                # Save the new configured engine to pecg_engines.json file
                if not is_cancel:
                    self.engine_id_name_list = self.get_engine_id_name_list()

                    # Refresh role engines in case a deleted engine was active.
                    if self.opp_id_name not in self.engine_id_name_list:
                        self.opp_id_name = None
                        self.opp_file = None
                        self.opp_path_and_file = None
                        self.get_default_engine_opponent()
                    if self.adviser_id_name not in self.engine_id_name_list:
                        self.adviser_id_name = None
                        self.adviser_file = None
                        self.adviser_path_and_file = None
                        self.set_default_adviser_engine()
                    if self.analysis_id_name not in self.engine_id_name_list:
                        self.analysis_id_name = None
                        self.analysis_file = None
                        self.analysis_path_and_file = None
                        self.set_default_analysis_engine()
                    if self.threat_id_name not in self.engine_id_name_list:
                        self.threat_id_name = None
                        self.threat_file = None
                        self.threat_path_and_file = None
                        self.set_default_threat_engine()

                    self.update_labels_and_game_tags(window, human=self.username)

                delete_win.Close()
                self.end_dialog(window)

                break

            # Idle setup, engine role managers (configure options + select).
            if button == 'Set Engine Opponent':
                self.manage_role_engine(window, 'opponent')
                self.update_labels_and_game_tags(window, human=self.username)
                break

            if button == 'Set Engine Adviser':
                self.manage_role_engine(window, 'adviser')
                break

            if button == 'Set Engine Analysis':
                self.manage_role_engine(window, 'analysis')
                break

            if button == 'Set Engine Threat':
                self.manage_role_engine(window, 'threat')
                break

            # Idle setup
            if button == 'Set Depth':
                self.set_depth_limit(window)
                break

            # Idle setup, Allow user to change book settings
            if button == 'Set Book::book_set_k':
                # Backup current values, we will restore these value in case
                # the user presses cancel or X button
                current_is_use_gui_book = self.is_use_gui_book
                current_is_random_book = self.is_random_book
                current_max_book_ply = self.max_book_ply

                layout = [
                        [sg.Text('This is the book used by your engine opponent.')],
                        [sg.T('Book File', size=(8, 1)),
                         sg.T(self.gui_book_file, size=(36, 1), relief='sunken')],
                        [sg.T('Max Ply', size=(8, 1)),
                         sg.Spin(choices_with(range(1, MAX_BOOK_PLY + 1),
                                              self.max_book_ply),
                                 initial_value=self.max_book_ply,
                                 readonly=True,
                                 size=(6, 1), key='book_ply_k')],
                        [sg.CBox('Use book', key='use_gui_book_k',
                                 default=self.is_use_gui_book)],
                        [sg.Radio('Best move', 'Book Radio',
                                  default=False if self.is_random_book else True),
                         sg.Radio('Random move', 'Book Radio',
                                  key='random_move_k',
                                  default=True if self.is_random_book else False)],
                        [sg.OK(), sg.Cancel()],
                ]

                w = sg.Window(BOX_TITLE + '/Set Book', layout,
                              icon=ico_path[platform]['pecg'], modal=True)
                self.begin_dialog(window)

                while True:
                    e, v = w.Read(timeout=10)

                    # If user presses X button
                    if e is None:
                        self.is_use_gui_book = current_is_use_gui_book
                        self.is_random_book = current_is_random_book
                        self.max_book_ply = current_max_book_ply
                        logging.info('Book setting is exited.')
                        break

                    if e == 'Cancel':
                        self.is_use_gui_book = current_is_use_gui_book
                        self.is_random_book = current_is_random_book
                        self.max_book_ply = current_max_book_ply
                        logging.info('Book setting is cancelled.')
                        break

                    if e == 'OK':
                        self.max_book_ply = int(v['book_ply_k'])
                        self.is_use_gui_book = v['use_gui_book_k']
                        self.is_random_book = v['random_move_k']
                        logging.info('Book setting is OK')
                        break

                self.end_dialog(window)
                w.Close()
                break

            # Idle setup, Settings menu
            if button == 'General::settings_game_k':
                win_title = 'Settings/General'
                layout = [
                    [sg.CBox('Save time left in game notation',
                             key='save_time_left_k',
                             default=self.is_save_time_left,
                             tooltip='[%clk h:mm:ss] will appear as\n' +
                                     'move comment and is shown in move\n' +
                                     'list and saved in pgn file.')],
                    [sg.CBox('Adjudicate game on time forfeit',
                             key='time_forfeit_k',
                             default=self.is_time_forfeit_enabled,
                             tooltip='When enabled, the game is\n' +
                                     'adjudicated when the player\n' +
                                     'runs out of time.')],
                    [sg.Text('Review analysis time (sec)', size=(24, 1),
                             tooltip='Maximum time the Review analysis engine\n' +
                                     'searches a position before stopping\n' +
                                     '({} to {}).'.format(
                                         REVIEW_ANALYSIS_TIME_MIN,
                                         REVIEW_ANALYSIS_TIME_MAX)),
                     sg.Combo(choices_with(TIME_CHOICES_SEC,
                                           self.review_analysis_time_sec),
                              default_value=self.review_analysis_time_sec,
                              readonly=True,
                              key='review_analysis_time_k', size=(6, 1))],
                    [sg.Text('Review threat time (sec)', size=(24, 1),
                             tooltip='Maximum time the Review threat engine\n' +
                                     'searches a position before stopping\n' +
                                     '({} to {}).'.format(
                                         REVIEW_ANALYSIS_TIME_MIN,
                                         REVIEW_ANALYSIS_TIME_MAX)),
                     sg.Combo(choices_with(TIME_CHOICES_SEC,
                                           self.review_threat_time_sec),
                              default_value=self.review_threat_time_sec,
                              readonly=True,
                              key='review_threat_time_k', size=(6, 1))],
                    [sg.OK(), sg.Cancel()],
                ]

                w = sg.Window(win_title, layout,
                              icon=ico_path[platform]['pecg'], modal=True)
                self.begin_dialog(window)

                while True:
                    e, v = w.Read(timeout=10)
                    if e is None or e == 'Cancel':
                        break
                    if e == 'OK':
                        self.is_save_time_left = v['save_time_left_k']
                        self.is_time_forfeit_enabled = v['time_forfeit_k']
                        self.review_analysis_time_sec = int(
                            v['review_analysis_time_k'])
                        self.review_threat_time_sec = int(
                            v['review_threat_time_k'])
                        self.save_settings()
                        break

                self.end_dialog(window)
                w.Close()
                break

            # Idle setup, Change theme
            if button in GUI_THEME:
                self.gui_theme = button
                window = self.create_new_window(window)
                break

            # Idle setup, Change board to gray
            if button == 'Gray::board_color_k':
                self.sq_light_color = '#D8D8D8'
                self.sq_dark_color = '#808080'
                self.move_sq_light_color = '#e0e0ad'
                self.move_sq_dark_color = '#999966'
                window = self.create_new_window(window)
                break

            # Idle setup, Change board to green
            if button == 'Green::board_color_k':
                self.sq_light_color = '#daf1e3'
                self.sq_dark_color = '#3a7859'
                self.move_sq_light_color = '#bae58f'
                self.move_sq_dark_color = '#6fbc55'
                window = self.create_new_window(window)
                break

            # Idle setup, Change board to blue
            if button == 'Blue::board_color_k':
                self.sq_light_color = '#b9d6e8'
                self.sq_dark_color = '#4790c0'
                self.move_sq_light_color = '#d2e4ba'
                self.move_sq_dark_color = '#91bc9c'
                window = self.create_new_window(window)
                break

            # Idle setup, Change board to brown, default
            if button == 'Brown::board_color_k':
                self.sq_light_color = '#F0D9B5'
                self.sq_dark_color = '#B58863'
                self.move_sq_light_color = '#E8E18E'
                self.move_sq_dark_color = '#B8AF4E'
                window = self.create_new_window(window)
                break

            is_handled = False
            break

        return is_handled, window

    def main_loop(self):
        """
        Build GUI, read user and engine config files and take user inputs.

        The GUI runs directly in Play mode: each loop iteration is one game.
        Setup (engine, time control, book, theme ...) is done through the
        same menubar while no game is running; play_game() delegates those
        events to handle_setup_event(). The app exits from inside play_game
        (window X) via sys.exit.
        """
        # Load persisted Settings/Game values (checkboxes, review times,
        # board scale) before the first layout is built so the window opens
        # at the right board size. On a first start (no saved size) pick
        # the largest board that fits the screen.
        self.load_settings()
        if not self._board_size_from_settings:
            self.auto_fit_board_size()
        self.preferred_square_px = self.square_px

        layout = self.build_main_layout(self.is_white_at_bottom)

        # Use white layout as default window
        window = sg.Window('{} {}'.format(APP_NAME, APP_VERSION),
                           layout, default_button_element_size=(12, 1),
                           auto_size_buttons=False,
                           finalize=True,
                           resizable=True,
                           icon=ico_path[platform]['pecg'])

        # Read user config file, if missing create and new one
        self.check_user_config_file()

        # If engine config file (pecg_engines.json) is missing, then create it.
        self.check_engine_config_file()
        self.engine_id_name_list = self.get_engine_id_name_list()

        # Define default opponent engine, user can change this later.
        self.get_default_engine_opponent()

        # Define default adviser engine, user can change this later.
        self.set_default_adviser_engine()

        # Define default analysis engine for Review mode.
        self.set_default_analysis_engine()

        # Define default threat engine for Review mode.
        self.set_default_threat_engine()

        # Override defaults with any persisted per-role engine selections.
        self.restore_engine_roles()

        self.init_game()

        # Initialize White and black boxes
        self.update_labels_and_game_tags(window, human=self.username)

        # Panels, board input and menubar font.
        self.finish_play_window(window)

        # Mode: Play. One game per loop iteration.
        while True:
            self.psg_board = copy.deepcopy(initial_board)
            board = chess.Board()

            # Each new game defaults to the user playing white; pressing
            # Engine->Go before the first move switches to black.
            self.is_user_white = True
            self.update_labels_and_game_tags(window, human=self.username)
            self.set_menu_state(window, in_game=False)
            self.redraw_board(window)
            window.find_element('_gamestatus_').Update('Mode     Play')
            self.update_turn_marker(window, board)

            start_new_game, window = self.play_game(window, board)

            self.set_new_game()


def install_error_logging():
    """Send errors that nothing else handles to the log file.

    Covers background threads and Tk callbacks (mouse and resize handlers),
    whose errors would otherwise only go to a console the user may not
    have. Errors in the main loop are logged by main().
    """
    default_thread_hook = threading.excepthook

    def log_thread_error(args):
        if args.exc_type is not SystemExit:
            logging.error(
                'Unexpected error in thread %s.',
                args.thread.name if args.thread else '?',
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
        default_thread_hook(args)

    def log_tk_callback_error(self, exc_type, exc_value, exc_tb):
        logging.error('Unexpected error in a window callback.',
                      exc_info=(exc_type, exc_value, exc_tb))

    threading.excepthook = log_thread_error
    tk.Tk.report_callback_exception = log_tk_callback_error


def main():
    install_error_logging()

    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    engine_config_file = 'pecg_engines.json'
    user_config_file = 'pecg_user.json'

    pecg_book = 'Book/pecg_book.bin'
    book_from_computer_games = 'Book/computer.bin'
    book_from_human_games = 'Book/human.bin'

    is_use_gui_book = True
    is_random_book = True  # If false then use best book move
    max_book_ply = 8
    theme = 'Reddit'

    try:
        pecg = EasyChessGui(theme, engine_config_file, user_config_file,
                            pecg_book, book_from_computer_games,
                            book_from_human_games, is_use_gui_book,
                            is_random_book, max_book_ply)

        pecg.main_loop()
    except Exception:
        # Anything unexpected: record it, tell the user where to look, then
        # let it end the program as before. (A normal exit is SystemExit
        # and does not come through here.)
        logging.critical('Unexpected error, the program stops.',
                         exc_info=True)
        try:
            sg.popup('An unexpected error occurred and the program has to '
                     'close.\n\nThe details are in pecg_log.txt.',
                     title=BOX_TITLE)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
