#!/usr/bin/env python3
"""
python_easy_chess_gui.py

Requirements:
    Python 3.7.3 and up

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
import pyperclip
import chess
import chess.pgn
import chess.engine
import chess.polyglot
import logging
import webbrowser
import tkinter as tk
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
APP_VERSION = 'v2.14.1'
BOX_TITLE = f'{APP_NAME} {APP_VERSION}'
REVIEW_MAX_DISPLAY_GAMES = 10000
REVIEW_ANALYSIS_MULTIPV_LINES = 3
REVIEW_ANALYSIS_PV_MOVES = 7
REVIEW_NAV_DEBOUNCE_SEC = 0.3
REVIEW_MOVE_LIST_HEIGHT = 8   # reduced from 11 to make room for the threat panel
REVIEW_ANALYSIS_BOX_HEIGHT = 3
REVIEW_THREAT_BOX_HEIGHT = 1
REVIEW_THREAT_PV_PLIES = 5
# Output file for games annotated by the Review-mode auto-analyzer.
AUTO_ANALYSIS_OUTPUT_FILE = 'pecg_analyzed_games.pgn'
# Number of plies to include when adding an engine PV as a sub-variation.
AUTO_ANALYSIS_PV_PLIES = 9
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

IMAGE_PATH = 'Images/60'  # path to the chess pieces
SQUARE_PX = 60            # piece images are 60x60, so the board is 8 * 60 wide
BOARD_PX = 8 * SQUARE_PX


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
# reference lives in the project README, opened via Help -> Online Help.
# Each dict key doubles as the "::key" suffix of its Help menu item.
HELP_TOPICS = {
    'help_start': (
        'Getting Started',
        'Python Easy Chess GUI has 3 modes: Neutral, Play and Review.\n'
        'You start in Neutral; switch using the Mode menu.\n\n'
        '1. Install a UCI engine:  Engine -> Manage -> Install.\n'
        '2. Choose your opponent:  Engine -> Set Engine Opponent.\n'
        '3. Play:  Mode -> Play, then move on the board.\n\n'
        'Games auto-save to pecg_auto_save_games.pgn.\n'
        'For the full manual use Help -> Online Help.'),
    'help_eng_install': (
        'Install / Manage Engines',
        'Neutral mode only. Only UCI engines are supported.\n\n'
        'Install:    Engine -> Manage -> Install -> Add.\n'
        'Configure:  Engine -> Manage -> Edit -> pick engine -> Modify\n'
        '            (Hash, Threads and other options).\n'
        'Remove:     Engine -> Manage -> Delete.'),
    'help_eng_opponent': (
        'Set Engine Opponent',
        'Neutral mode:  Engine -> Set Engine Opponent.\n\n'
        'This is the engine you play against; the list shows the engines\n'
        'you have installed. Set its clock under Time -> Engine.'),
    'help_eng_adviser': (
        'Engine Adviser',
        'Select it with  Engine -> Set Engine Adviser.\n\n'
        'During a game (Play mode) right-click the Adviser label and press\n'
        'Start to get a suggested move and score for the current position.'),
    'help_eng_analysis': (
        'Review Analysis Engine',
        'Select it with  Engine -> Set Engine Analysis.\n\n'
        'In Review mode press the Analysis button to evaluate the current\n'
        'position (multiple lines). The search stops after the analysis\n'
        'time in Settings -> Game (default 60s).'),
    'help_eng_threat': (
        'Review Threat Engine',
        'Select it with  Engine -> Set Engine Threat.\n\n'
        'In Review mode press the Threat button to see what the opponent\n'
        'would play if the side to move passed (null move). Unavailable\n'
        'while in check. Time limit: Settings -> Game (default 30s).'),
    'help_eng_depth': (
        'Search Depth',
        'Engine -> Set Depth caps the search depth of the playing and\n'
        'adviser engines. Leave at the default for no depth limit.\n'
        'Review analysis/threat are limited by time, not depth.'),
    'help_game_play': (
        'Play a Game',
        'Mode -> Play, then click the piece and its destination square\n'
        '(or drag it). Engine -> Move Now forces the engine to move;\n'
        'Game -> New starts a new game.'),
    'help_game_black': (
        'Play as Black',
        'In Neutral mode:  Board -> Flip (black at the bottom), then\n'
        'Mode -> Play and Engine -> Go so the engine moves first.\n'
        '(If already in Play, switch to Neutral first.)'),
    'help_game_fen': (
        'Paste a FEN',
        'In Play mode:  FEN -> Paste to set up a position from the\n'
        'clipboard. If it is Black to move, use Engine -> Go.'),
    'help_game_save': (
        'Save Games and Repertoire',
        'Every game auto-saves to pecg_auto_save_games.pgn.\n\n'
        'In Play mode the Game menu also offers Save to My Games and\n'
        'Save to White / Black Repertoire.'),
    'help_game_time': (
        'Time Control',
        'Time -> User sets your clock; Time -> Engine sets the opponent\n'
        'clock. Adjudication on flag-fall is toggled in Settings -> Game.'),
    'help_review_open': (
        'Open a Game to Review',
        'Mode -> Review, choose a PGN file, select a game and press OK.\n'
        'Use Game -> Load PGN / Select Game to change games later.'),
    'help_review_nav': (
        'Navigate Moves',
        'Use the First, Previous, Next and Last buttons below the board,\n'
        'or click a move in the move list to jump to that position.'),
    'help_review_engine': (
        'Analysis and Threat (Review)',
        'Analysis button: evaluate the position with the analysis engine.\n'
        'Threat button: show the opponent threat (null move).\n'
        'Both stop after their time limits in Settings -> Game (analysis\n'
        '60s, threat 30s) and restart automatically when you change move.'),
    'help_review_auto': (
        'Auto-Analyze Game',
        'Game -> Auto-Analyze Game annotates every move of the loaded game\n'
        'with an engine and time per move that you choose. Each move gets an\n'
        'evaluation comment and engine-best lines are added as variations.\n'
        'Results are appended to pecg_analyzed_games.pgn and the annotated\n'
        'game replaces the current review game. Use Game -> Cancel Analysis\n'
        'to stop early.'),
    'help_board_flip': (
        'Flip Board',
        'Board -> Flip swaps the side shown at the bottom. Use it in\n'
        'Neutral mode, or in Review mode via its Board menu.'),
    'help_board_color': (
        'Board Colors and Themes',
        'Neutral mode:  Board -> Color changes the square colors and\n'
        'Board -> Theme changes the overall GUI theme.'),
}

# Online (detailed) help target for Help -> Online Help.
ONLINE_HELP_URL = 'https://github.com/fsmosca/Python-Easy-Chess-GUI#readme'


# Help submenu fragments. Note: a literal '&' marks a keyboard accelerator in
# menu labels, so plain words are used instead.
HELP_ENGINE_MENU = ['Engine', ['Install / Manage::help_eng_install',
                               'Set Opponent::help_eng_opponent',
                               'Adviser::help_eng_adviser',
                               'Analysis::help_eng_analysis',
                               'Threat::help_eng_threat',
                               'Search Depth::help_eng_depth']]
HELP_GAME_MENU = ['Game', ['Play a Game::help_game_play',
                           'Play as Black::help_game_black',
                           'Paste FEN::help_game_fen',
                           'Save and Repertoire::help_game_save',
                           'Time Control::help_game_time']]
HELP_REVIEW_MENU = ['Review', ['Open a Game::help_review_open',
                               'Navigate Moves::help_review_nav',
                               'Analysis and Threat::help_review_engine',
                               'Auto-Analyze Game::help_review_auto']]
HELP_BOARD_MENU = ['Board', ['Flip::help_board_flip',
                             'Colors and Themes::help_board_color']]


def make_help_menu(*sections):
    """Return a fresh Help menu definition for a mode.

    ``sections`` are submenu fragments of the form ``['Label', [items]]``.
    They are flattened into the parent so the label string and its item list
    become siblings (the format FreeSimpleGUI expects: a cascade is a string
    immediately followed by a list). A deep copy is returned so FreeSimpleGUI
    cannot mutate the shared fragment lists across the three menu definitions.
    """
    items = ['Getting Started::help_start']
    for section in sections:
        items.extend(section)  # 'Label', [subitems] as two sibling elements
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


# (1) Mode: Neutral
menu_def_neutral = [
        ['&Mode', ['Play', 'Review']],
        ['Boar&d', ['Flip', 'Color', ['Brown::board_color_k',
                                      'Blue::board_color_k',
                                      'Green::board_color_k',
                                      'Gray::board_color_k'],
                    'Theme', GUI_THEME]],
        ['&Engine', ['Set Engine Adviser', 'Set Engine Analysis',
                     'Set Engine Threat', 'Set Engine Opponent', 'Set Depth',
                     'Manage', ['Install', 'Edit', 'Delete']]],
        ['&Time', ['User::tc_k', 'Engine::tc_k']],
        ['&Book', ['Set Book::book_set_k']],
        ['&User', ['Set Name::user_name_k']],
        ['Tools', ['PGN', ['Delete Player::delete_player_k']]],
        ['&Settings', ['Game::settings_game_k']],
        make_help_menu(HELP_ENGINE_MENU, HELP_GAME_MENU,
                       HELP_REVIEW_MENU, HELP_BOARD_MENU),
]

# (2) Mode: Play, info: hide
menu_def_play = [
        ['&Mode', ['Neutral']],
        ['&Game', ['&New::new_game_k',
                   'Save to My Games::save_game_k',
                   'Save to White Repertoire',
                   'Save to Black Repertoire',
                   'Resign::resign_game_k',
                   'User Wins::user_wins_k',
                   'User Draws::user_draws_k']],
        ['FEN', ['Paste']],
        ['&Engine', ['Go', 'Move Now']],
        make_help_menu(HELP_GAME_MENU, HELP_ENGINE_MENU),
]

# (3) Mode: Review
menu_def_review = [
        ['&Mode', ['Neutral']],
        ['&Game', ['Load PGN::review_load_pgn_k',
                   'Select Game::review_select_game_k',
                   'Auto-Analyze Game::review_auto_analyze_k',
                   'Cancel Analysis::review_cancel_analysis_k']],
        ['Boar&d', ['Flip']],
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

    def update_base(self) -> None:
        """Updates base time after every move."""
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
                 existing_engine=None, multipv=1, option_overrides=None):
        """
        Run engine as opponent or as adviser.

        :param eng_queue:
        :param engine_config_file: pecg_engines.json
        :param engine_path_and_file:
        :param engine_id_name:
        :param max_depth:
        :param existing_engine: An existing chess.engine.SimpleEngine instance
            to reuse instead of spawning a new process.
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

                            if score is not None and pv is not None and depth is not None:
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

    Walks the mainline of the supplied game, evaluates each position with the
    configured analysis engine, writes the evaluation as a comment from White's
    point of view, and adds the engine's PV as a sub-variation when it disagrees
    with the move played in the game.
    """

    def __init__(self, game, engine_config_file, engine_path_and_file,
                 engine_id_name, time_sec, output_queue, cancel_event,
                 max_depth=MAX_DEPTH, option_overrides=None,
                 output_file=AUTO_ANALYSIS_OUTPUT_FILE):
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
        self.engine = None
        self.daemon = True

    def _format_score(self, score):
        """Return a human-readable score string from White's POV."""
        white_score = score.white()
        if white_score.is_mate():
            mate = white_score.mate()
            return 'Mate in {}'.format(mate) if mate > 0 \
                else 'Mated in {}'.format(abs(mate))
        cp = white_score.score(mate_score=32000)
        return '{:+.2f}'.format(cp / 100.0)

    def _build_engine_variation(self, node, best_move, pv, board, score):
        """Add best_move and the rest of the PV as a variation on node."""
        if best_move not in board.legal_moves:
            return
        comment = self._format_score(score) if score is not None else ''
        var_board = board.copy()
        var_node = node.add_variation(best_move, comment=comment)
        var_board.push(best_move)
        for move in pv[1:AUTO_ANALYSIS_PV_PLIES]:
            if move not in var_board.legal_moves:
                break
            var_node = var_node.add_variation(move)
            var_board.push(move)

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
                infos = self.engine.analyse(board, limit, multipv=1)
                info = infos[0] if isinstance(infos, list) else infos

                score = info.get('score')
                pv = info.get('pv', [])
                best_move = pv[0] if pv else None
                engine_cp = self._centipawns(score) if score is not None else None

                # Determine the actual evaluation of the move played in the game.
                if score is not None and best_move == child.move:
                    game_move_score = score
                elif score is not None:
                    after_board = board.copy()
                    after_board.push(child.move)
                    after_infos = self.engine.analyse(
                        after_board, limit, multipv=1)
                    after_info = after_infos[0] if isinstance(
                        after_infos, list) else after_infos
                    game_move_score = after_info.get('score')
                else:
                    game_move_score = None

                if game_move_score is not None:
                    score_text = self._format_score(game_move_score)
                    child.comment = score_text

                    if engine_cp is not None:
                        if best_move == child.move:
                            game_move_cp = engine_cp
                        else:
                            game_move_cp = -self._centipawns(game_move_score)
                        nag = self._classify_nag(engine_cp, game_move_cp)
                        if nag is not None:
                            child.nags.add(nag)

                if best_move is not None and best_move != child.move:
                    self._build_engine_variation(node, best_move, pv, board, score)

                self.output_queue.put({
                    'type': 'progress',
                    'current': current,
                    'total': total,
                })

                board.push(child.move)
                node = child

            self.game.headers['Annotator'] = self.engine_id_name
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


class EasyChessGui:
    queue = queue.Queue()
    is_user_white = True  # White is at the bottom in board layout

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
        self.init_game()
        self.fen = None
        self.psg_board = None
        self.menu_elem = None

        # Drag-and-drop state
        self._drag_source = None
        self._widget_to_square = {}
        self._drag_window = None
        self._drag_piece = None    # piece code currently being dragged
        self._drag_ghost = None    # floating Toplevel showing the dragged piece
        self._drag_photo = None    # PhotoImage ref kept alive during the drag
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
        # Auto-analysis defaults to the analysis engine/time, but the user can
        # pick any installed engine and a separate time cap per move.
        self.auto_analysis_engine_id_name = None
        self.auto_analysis_time_sec = REVIEW_ANALYSIS_TIME_SEC
        # Per-(role, engine) UCI option overrides:
        # {role: {engine_id_name: {option_name: value}}}, deltas vs base.
        self.role_engine_options = {}
        self.analysis_file = None
        self.analysis_path_and_file = None
        self.analysis_id_name = None
        self.threat_file = None
        self.threat_path_and_file = None
        self.threat_id_name = None
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
        self.review_move_index = 0
        self.review_move_labels = []
        self.review_boards = []
        self.review_nodes = []
        self.review_window = None
        self.review_analysis_lines = [''] * REVIEW_ANALYSIS_MULTIPV_LINES
        self.review_analysis_enabled = False
        self.review_analysis_status = 'Analysis stopped'
        self.review_analysis_search = None
        self.review_analysis_engine = None
        self._stale_analysis_searches = []
        self.review_analysis_stale = False
        self.review_threat_enabled = False
        self.review_threat_status = 'Threat stopped'
        self.review_threat_line = ''
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
        self.review_analysis_lines = [''] * REVIEW_ANALYSIS_MULTIPV_LINES
        self.review_analysis_enabled = False
        self.review_analysis_status = 'Analysis stopped'
        self.review_analysis_search = None
        self.review_analysis_engine = None
        self._stale_analysis_searches = []
        self.review_analysis_stale = False
        self.review_threat_enabled = False
        self.review_threat_status = 'Threat stopped'
        self.review_threat_line = ''
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
        if self.review_analysis_enabled or self.review_threat_enabled:
            # Stop currently running analysis and trigger a debounce restart
            if self.review_analysis_search is not None:
                self.review_analysis_search.stop()
            if self.review_threat_search is not None:
                self.review_threat_search.stop()
            # Mark output stale so poll discards the old position's lines and the
            # debounce restart knows these roles still need restarting.
            self.review_analysis_stale = True
            self.review_threat_stale = True
            self.review_nav_last_time = time.time()
            self.review_analysis_lines = [''] * REVIEW_ANALYSIS_MULTIPV_LINES
            self.review_analysis_status = 'Waiting...'
            self.review_threat_line = ''
            self.review_threat_status = 'Waiting...'
            self.update_review_analysis_panel(self.review_window)
            self.update_review_threat_panel(self.review_window)
        else:
            self.refresh_review_analysis(self.review_window)
            self.refresh_review_threat(self.review_window)

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

    def create_new_window(self, window, flip=False):
        """Hide current window and creates a new window."""
        loc = window.CurrentLocation()
        window.Hide()
        if flip:
            self.is_user_white = not self.is_user_white

        layout = self.build_main_layout(self.is_user_white)

        w = sg.Window(
            '{} {}'.format(APP_NAME, APP_VERSION),
            layout,
            default_button_element_size=(12, 1),
            auto_size_buttons=False,
            location=(loc[0], loc[1]),
            finalize=True,
            icon=ico_path[platform]['pecg']
        )

        # Initialize White and black boxes
        self.update_labels_and_game_tags(w, human=self.username)

        # Re-bind drag-and-drop on the new window's board squares
        self.setup_board_drag_drop(w)
        self.redraw_board(w)

        # Match the Linux menubar font to Windows (no-op on Windows/macOS).
        self.apply_menu_font(w)

        window.Close()
        return w

    def delete_player(self, name, pgn, que):
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

        # Create backup of orig
        backup = pgn_file + '.backup'
        backup_path = Path(folder_path, backup)
        backup_path.touch()
        origfile_text = Path(pgn).read_text()
        backup_path.write_text(origfile_text)
        logging.info(f'backup copy {backup_path} is successfully created.')

        # Define output file
        output = 'out_' + pgn_file
        output_path = Path(folder_path, output)
        logging.info(f'output {output_path} is successfully created.')

        logging.info(f'Deleting player {name}.')
        gcnt = 0

        # read pgn and save each game if player name to be deleted is not in
        # the game, either white or black.
        with open(output_path, 'a') as f:
            with open(pgn_path) as h:
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

        que.put('Done')

    def get_players(self, pgn, q):
        logging.info('Enters get_players()')
        players = []
        games = 0
        with open(pgn) as h:
            while True:
                headers = chess.pgn.read_headers(h)
                if headers is None:
                    break

                wp = headers['White']
                bp = headers['Black']

                players.append(wp)
                players.append(bp)
                games += 1

        p = list(set(players))
        ret = [p, games]

        q.put(ret)

    def get_engine_id_name(self, path_and_file, q):
        """ Returns id name of uci engine """
        id_name = None
        folder = Path(path_and_file)
        folder = folder.parents[0]

        try:
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
        if 'adviser_movetime_sec' in data:
            self.adviser_movetime_sec = self._read_review_time(
                data['adviser_movetime_sec'], self.adviser_movetime_sec)
        if 'auto_analysis_engine_id_name' in data:
            self.auto_analysis_engine_id_name = data['auto_analysis_engine_id_name']
        if 'auto_analysis_time_sec' in data:
            self.auto_analysis_time_sec = self._read_review_time(
                data['auto_analysis_time_sec'], self.auto_analysis_time_sec)
        # Per-role engine option overrides (the active role ids are applied
        # later by restore_engine_roles, once the engine list exists).
        if isinstance(data.get('role_engine_options'), dict):
            self.role_engine_options = data['role_engine_options']
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
            'opp_id_name': self.opp_id_name,
            'adviser_id_name': self.adviser_id_name,
            'analysis_id_name': self.analysis_id_name,
            'threat_id_name': self.threat_id_name,
            'adviser_movetime_sec': self.adviser_movetime_sec,
            'auto_analysis_engine_id_name': self.auto_analysis_engine_id_name,
            'auto_analysis_time_sec': self.auto_analysis_time_sec,
            'role_engine_options': self.role_engine_options,
            'review_pgn_file': self.review_pgn_file,
        }
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
                             'type': type_, 'base': base})
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
                      resizable=True, finalize=True)
        while True:
            e, v = w.Read()
            if e in (None, 'Cancel'):
                break
            if e == 'OK':
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
                      sg.Spin([t for t in range(1, 3600)],
                              initial_value=self.adviser_movetime_sec,
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
        window.Hide()
        w = sg.Window('{} Manager'.format(title), layout,
                      icon=role_icon, finalize=True)
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
                try:
                    self.adviser_movetime_sec = min(
                        3600, max(1, int(values['role_movetime_k'])))
                    self.save_settings()
                except (TypeError, ValueError):
                    pass

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
                w.Hide()
                self.configure_role_engine(role, sel)
                w.UnHide()
                refresh()
            elif e == 'role_del_k':
                if sel:
                    self.delete_role_options(role, sel)
                    refresh()
        w.Close()
        window.UnHide()
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
        folder = Path(engine_path_and_file).parents[0]
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
                    Back to Neutral mode, it is better to change engine {self.opp_id_name}.',
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

    def get_fen(self):
        """ Get fen from clipboard """
        self.fen = pyperclip.paste()

        # Remove empty char at the end of FEN
        if self.fen.endswith(' '):
            self.fen = self.fen[:-1]

    def fen_to_psg_board(self, window):
        """ Update psg_board based on FEN """
        psgboard = []

        # Get piece locations only to build psg board
        pc_locations = self.fen.split()[0]

        board = chess.BaseBoard(pc_locations)
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
        self.redraw_board(window)

    def change_square_color(self, window, row, col):
        """
        Change the color of a square based on square row and col.
        """
        btn_sq = window.find_element(key=(row, col))
        is_dark_square = True if (row + col) % 2 else False
        bd_sq_color = self.move_sq_dark_color if is_dark_square else self.move_sq_light_color
        btn_sq.Update(button_color=('white', bd_sq_color))

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
        """
        Redraw board at start and afte a move.

        :param window:
        :return:
        """
        for i in range(8):
            for j in range(8):
                color = self.sq_dark_color if (i + j) % 2 else \
                        self.sq_light_color
                piece_image = images[self.psg_board[i][j]]
                elem = window.find_element(key=(i, j))
                elem.Update(button_color=('white', color),
                            image_filename=piece_image, )
        self.configure_board_widgets(window)

    def configure_board_widgets(self, window):
        """Configure board square Tkinter buttons to ensure no gaps or borders."""
        configured_count = 0
        for i in range(8):
            for j in range(8):
                elem = window.find_element(key=(i, j), silent_on_error=True)
                if elem is not None and elem.Widget is not None:
                    try:
                        if platform == 'linux':
                            elem.Widget.configure(borderwidth=0, bd=0, highlightthickness=0, padx=0, pady=0, relief='flat', width=58, height=58)
                        else:
                            elem.Widget.configure(borderwidth=0, bd=0, highlightthickness=0, padx=0, pady=0, relief='flat')
                        configured_count += 1
                    except Exception as e:
                        logging.warning('Failed to configure board square widget (%d, %d): %s', i, j, e)
        logging.info('Successfully configured %d board square widgets.', configured_count)

    def setup_board_drag_drop(self, window):
        """Bind drag-and-drop events to board square buttons.

        After window finalization, this binds mouse press/release events
        to each board square so that pieces can be moved by dragging.
        """
        self._widget_to_square = {}
        self._drag_window = window
        window.refresh()
        self.configure_board_widgets(window)
        for i in range(8):
            for j in range(8):
                elem = window.find_element(key=(i, j))
                widget = elem.Widget
                self._widget_to_square[widget] = (i, j)
                widget.bind('<ButtonPress-1>',
                            self._on_drag_press, add='+')
                widget.bind('<B1-Motion>',
                            self._on_drag_motion, add='+')
                widget.bind('<ButtonRelease-1>',
                            self._on_drag_release, add='+')

    def _on_drag_press(self, event):
        """Record the source square (and its piece) on mouse press."""
        self._drag_source = self._widget_to_square.get(event.widget)
        if self._drag_source is not None:
            row, col = self._drag_source
            self._drag_piece = self.psg_board[row][col]
        else:
            self._drag_piece = None

    def _on_drag_motion(self, event):
        """Show a floating piece that follows the cursor while dragging.

        The ghost is created lazily on the first motion, so a plain click
        (press + release without movement) shows no ghost. Only the source
        square's button image is blanked here; ``self.psg_board`` (the move
        data) is left untouched so move validation stays correct.
        """
        if self._drag_source is None or self._drag_piece in (None, BLANK):
            return

        if self._drag_ghost is None:
            row, col = self._drag_source
            try:
                root = self._drag_window.TKroot
                # Lift the piece: blank the source square image only.
                self._drag_window.find_element(key=(row, col)).Update(
                    image_filename=images[BLANK])
                self._drag_photo = tk.PhotoImage(
                    file=images[self._drag_piece], master=root)
                ghost = tk.Toplevel(root)
                ghost.overrideredirect(True)
                ghost.attributes('-topmost', True)
                label_bg = None
                try:
                    # Windows: transparent background so only the piece shows.
                    transparent = 'magenta'
                    ghost.configure(bg=transparent)
                    ghost.attributes('-transparentcolor', transparent)
                    label_bg = transparent
                except Exception:
                    label_bg = None
                lbl = tk.Label(ghost, image=self._drag_photo,
                               borderwidth=0, highlightthickness=0)
                if label_bg is not None:
                    lbl.configure(bg=label_bg)
                lbl.pack()
                self._drag_ghost = ghost
            except Exception:
                logging.exception('Failed to create drag ghost.')
                self._destroy_drag_ghost()
                return

        try:
            self._drag_ghost.geometry(
                '+{}+{}'.format(event.x_root - 30, event.y_root - 30))
        except Exception:
            self._destroy_drag_ghost()

    def _destroy_drag_ghost(self):
        """Destroy the floating drag piece and release its image reference."""
        if self._drag_ghost is not None:
            try:
                self._drag_ghost.destroy()
            except Exception:
                pass
            self._drag_ghost = None
        self._drag_photo = None

    def _on_drag_release(self, event):
        """Handle mouse release for drag-and-drop moves.

        Uses winfo_containing to find which board square the cursor is
        over when the mouse button is released. If the target is a
        different square from the source, injects a drag move event
        into the FreeSimpleGUI event queue.
        """
        had_ghost = self._drag_ghost is not None
        self._destroy_drag_ghost()

        if self._drag_source is None:
            self._drag_piece = None
            return
        source = self._drag_source
        drag_piece = self._drag_piece
        self._drag_source = None
        self._drag_piece = None

        # If the piece was lifted, restore the source square image. A legal
        # move is redrawn by the __drag_move__ handler; an illegal or
        # cancelled drag keeps the piece on its origin square.
        if had_ghost and drag_piece is not None:
            try:
                self._drag_window.find_element(key=source).Update(
                    image_filename=images[drag_piece])
            except Exception:
                logging.exception('Failed to restore dragged piece image.')

        # Find the widget under the cursor at release position
        target_widget = event.widget.winfo_containing(
            event.x_root, event.y_root)

        # Check directly first, then walk up the widget hierarchy
        target_square = self._widget_to_square.get(target_widget)
        if target_square is None:
            w = getattr(target_widget, 'master', None) \
                if target_widget is not None else None
            while w is not None:
                target_square = self._widget_to_square.get(w)
                if target_square is not None:
                    break
                w = getattr(w, 'master', None)

        if target_square is not None and target_square != source:
            self._drag_window.write_event_value(
                '__drag_move__', (source, target_square))

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

    def set_depth_limit(self):
        """ Returns max depth based from user setting """
        user_depth = sg.popup_get_text(
            f'Current depth is {self.max_depth}\n\nInput depth [{MIN_DEPTH} to {MAX_DEPTH}]',
            title=BOX_TITLE,
            icon=ico_path[platform]['pecg']
        )

        try:
            user_depth = int(user_depth)
        except Exception:
            user_depth = self.max_depth
            logging.exception('Failed to get user depth.')

        self.max_depth = min(MAX_DEPTH, max(MIN_DEPTH, user_depth))

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
            key, ('Help', 'See Help -> Online Help for the full manual.'))
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

    def play_game(self, window: sg.Window, board: chess.Board):
        """Play a game against an engine or human.

        Args:
          window: A PySimplegUI window.
          board: current board position
        """
        window.find_element('_movelist_').Update(disabled=False)
        window.find_element('_movelist_').Update('', disabled=True)

        is_human_stm = True if self.is_user_white else False

        move_state = 0
        move_from, move_to = None, None
        is_new_game, is_exit_game, is_exit_app = False, False, False

        # Do not play immediately when stm is computer
        is_engine_ready = True if is_human_stm else False

        # For saving game
        move_cnt = 0

        is_user_resigns = False
        is_user_wins = False
        is_user_draws = False
        is_user_time_forfeit = False
        is_search_stop_for_exit = False
        is_search_stop_for_new_game = False
        is_search_stop_for_neutral = False
        is_search_stop_for_resign = False
        is_search_stop_for_user_wins = False
        is_search_stop_for_user_draws = False

        # Engine instance that persists across moves
        persistent_engine = None
        is_hide_book1 = True
        is_hide_book2 = True
        is_hide_search_info = True

        # Init timer
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

                    # Mode: Play, Stm: Computer first move
                    if button == 'Neutral':
                        is_exit_game = True
                        break

                    if isinstance(button, str) and '::help_' in button:
                        self.show_help_topic(button)
                        continue

                    if button == 'Paste':
                        try:
                            self.get_fen()
                            self.set_new_game()
                            board = chess.Board(self.fen)
                        except Exception:
                            logging.exception('Error in parsing FEN from clipboard.')
                            continue

                        self.fen_to_psg_board(window)

                        # If user is black and side to move is black
                        if not self.is_user_white and not board.turn:
                            is_human_stm = True
                            window.find_element('_gamestatus_').Update(
                                'Mode     Play')

                        # Elif user is black and side to move is white
                        elif not self.is_user_white and board.turn:
                            is_human_stm = False
                            window.find_element('_gamestatus_').Update(
                                    'Mode     Play, press Engine->Go')

                        # When computer is to move in the first move, don't
                        # allow the engine to search immediately, wait for the
                        # user to press Engine->Go menu.
                        is_engine_ready = True if is_human_stm else False

                        self.game.headers['FEN'] = self.fen
                        break

                    if button == 'Go':
                        is_engine_ready = True
                        break

                    if button is None:
                        logging.info('Quit app X is pressed.')
                        is_exit_app = True
                        break

                if is_exit_app or is_exit_game or is_new_game:
                    break

            # If side to move is human
            if is_human_stm:
                move_state = 0

                while True:
                    button, value = window.Read(timeout=100)

                    # Update elapse box in m:s format
                    elapse_str = self.get_time_mm_ss_ms(human_timer.elapse)
                    k = 'w_elapse_k'
                    if not self.is_user_white:
                        k = 'b_elapse_k'
                    window.Element(k).Update(elapse_str)
                    human_timer.elapse += 100

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

                    if not is_human_stm:
                        break

                    # Mode: Play, Stm: User, Run adviser engine
                    if button == 'Start::right_adviser_k':
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
                        with open(self.my_games, mode='a+') as f:
                            self.game.headers['Event'] = 'My Games'
                            f.write('{}\n\n'.format(self.game))
                        break

                    # Mode: Play, Stm: user
                    if button == 'Save to White Repertoire':
                        with open(self.repertoire_file['white'], mode='a+') as f:
                            self.game.headers['Event'] = 'White Repertoire'
                            f.write('{}\n\n'.format(self.game))
                        break

                    # Mode: Play, Stm: user
                    if button == 'Save to Black Repertoire':
                        with open(self.repertoire_file['black'], mode='a+') as f:
                            self.game.headers['Event'] = 'Black Repertoire'
                            f.write('{}\n\n'.format(self.game))
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

                    # Mode: Play, Stm: User
                    if button == 'Neutral' or is_search_stop_for_neutral:
                        is_exit_game = True
                        self.clear_elements(window)
                        break

                    # Mode: Play, stm: User
                    if isinstance(button, str) and '::help_' in button:
                        self.show_help_topic(button)
                        break

                    # Mode: Play, stm: User
                    if button == 'Go':
                        if is_human_stm:
                            is_human_stm = False
                        else:
                            is_human_stm = True
                        is_engine_ready = True
                        window.find_element('_gamestatus_').Update(
                                'Mode     Play, Engine is thinking ...')
                        break

                    # Mode: Play, stm: User
                    if button == 'Paste':
                        # Pasting fen is only allowed before the game starts.
                        if len(self.game.variations):
                            sg.popup('Press Game->New then paste your fen.',
                                     title='Mode Play')
                            continue
                        try:
                            self.get_fen()
                            self.set_new_game()
                            board = chess.Board(self.fen)
                        except Exception:
                            logging.exception('Error in parsing FEN from clipboard.')
                            continue

                        self.fen_to_psg_board(window)

                        is_human_stm = True if board.turn else False
                        is_engine_ready = True if is_human_stm else False

                        window.find_element('_gamestatus_').Update(
                                'Mode     Play, side: {}'.format(
                                        'white' if board.turn else 'black'))

                        self.game.headers['FEN'] = self.fen
                        break

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
                                prev_color = self.sq_dark_color \
                                    if (move_from[0] + move_from[1]) % 2 \
                                    else self.sq_light_color
                                window.find_element(key=move_from).Update(
                                    button_color=('white', prev_color))

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
                            button_square = window.find_element(key=(fr_row, fr_col))

                            # If move is cancelled, pressing same button twice
                            if move_to == move_from:
                                # Restore the color of the pressed board square
                                color = self.sq_dark_color if (to_row + to_col) % 2 else self.sq_light_color

                                # Restore the color of the fr square
                                button_square.Update(button_color=('white', color))
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

                            # If user move is a promote
                            if self.relative_row(to_sq, board.turn) == RANK_8 and \
                                    moved_piece == chess.PAWN:
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
                                color = self.sq_dark_color \
                                    if (move_from[0] + move_from[1]) % 2 else self.sq_light_color

                                # Restore the color of the fr square
                                button_square.Update(button_color=('white', color))
                                continue

                if (is_new_game or is_exit_game or is_exit_app or
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
                    window.find_element('_gamestatus_').Update(
                            'Mode     Play, Engine is thinking ...')

                    while True:
                        button, value = window.Read(timeout=100)

                        if button == sg.WIN_CLOSED:
                            logging.warning('User closes the window while the engine is thinking.')
                            search.stop()
                            sys.exit(0)  # the engine is run on daemon threads so it will quit as well

                        # Update elapse box in m:s format
                        elapse_str = self.get_time_mm_ss_ms(engine_timer.elapse)
                        k = 'b_elapse_k'
                        if not self.is_user_white:
                            k = 'w_elapse_k'
                        window.Element(k).Update(elapse_str)
                        engine_timer.elapse += 100

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

                        # Exit app while engine is thinking.
                        if button is None:
                            search.stop()
                            is_search_stop_for_exit = True

                        # Forced engine to move now and create a new game
                        if button == 'New::new_game_k':
                            search.stop()
                            is_search_stop_for_new_game = True

                        # Forced engine to move now
                        if button == 'Move Now':
                            search.stop()

                        # Mode: Play, Computer is thinking
                        if button == 'Neutral':
                            search.stop()
                            is_search_stop_for_neutral = True

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

                    search.join()
                    # Keep engine alive for reuse; retrieve instance
                    persistent_engine = search.get_engine()
                    is_book_from_gui = False

                # If engine failed to send a legal move
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
        # the user is exiting play mode (e.g. neutral, new game, resign).
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
        self.save_game()

        if board.is_game_over(claim_draw=True):
            sg.popup('Game is over.', title=BOX_TITLE,
                     icon=ico_path[platform]['pecg'])

        if is_exit_app:
            window.Close()
            sys.exit(0)

        self.clear_elements(window)

        return False if is_exit_game else is_new_game

    def save_game(self):
        """ Save game in append mode """
        with open(self.pecg_auto_save_game, mode='a+') as f:
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

    def get_review_game_text(self, game, index):
        """Return one-line summary of a game for review list."""
        headers = game.headers if hasattr(game, 'headers') else game['headers']
        white = headers.get('White', '?')
        black = headers.get('Black', '?')
        result = headers.get('Result', '*')
        event = headers.get('Event', '?')
        date = headers.get('Date', '?')
        return f'{index + 1:>3}. {white} vs {black} | {result} | {event} | {date}'

    def select_review_game(self, pgn_file=None, games=None):
        """Ask user to select a game from a pgn file."""
        if games is None:
            games = []

        selected_games = games
        selected_pgn = pgn_file or ''
        is_truncated = False

        # Auto-load games if a valid PGN file path is passed but no games are loaded yet
        if selected_pgn and not selected_games:
            if os.path.isfile(selected_pgn):
                try:
                    selected_games, is_truncated = self.load_pgn_games(selected_pgn)
                except Exception:
                    logging.exception(f'Failed to auto-load PGN games from {selected_pgn}')

        selection_list = [
            self.get_review_game_text(game, index)
            for index, game in enumerate(selected_games)
        ]

        layout = [
            [sg.Text('PGN', size=(4, 1)),
             sg.Input(default_text=selected_pgn, key='pgn_k', expand_x=True, enable_events=True),
             sg.FileBrowse()],
            [sg.Button('Display Games', expand_x=True)],
            [sg.Text('Status: Load a PGN, select a game, then press OK.',
                     key='status_k', relief='sunken', expand_x=True)],
            [sg.Listbox(selection_list, size=(74, 12), key='game_k',
                        expand_x=True)],
            [sg.Button('OK'), sg.Cancel()]
        ]

        w = sg.Window('Review/Load PGN', layout,
                      icon=ico_path[platform]['pecg'], finalize=True)

        # Update initial selection and status message if games are loaded
        if selected_games:
            w['game_k'].Update(selection_list, set_to_index=[0])
            if is_truncated:
                w['status_k'].Update(
                    f'Status: Showing first {len(selected_games)} games only. Select one and press OK.')
            else:
                w['status_k'].Update(
                    f'Status: Loaded {len(selected_games)} game(s). Select one and press OK.')

        selected_game = None

        while True:
            e, v = w.Read(timeout=50)
            if e is None or e == 'Cancel':
                break

            if e == 'Display Games' or e == 'pgn_k':
                new_pgn = v['pgn_k']
                if not new_pgn:
                    if e == 'Display Games':
                        w['status_k'].Update('Status: Please choose a PGN file.')
                    continue

                # For auto-loading via typing/browsing event, only proceed if it exists as a file
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
                    w['game_k'].Update([])
                    continue

                if not selected_games:
                    w['status_k'].Update('Status: No games found in PGN file.')
                    w['game_k'].Update([])
                    continue

                selection_list = [
                    self.get_review_game_text(game, index)
                    for index, game in enumerate(selected_games)
                ]
                w['game_k'].Update(selection_list, set_to_index=[0])
                if is_truncated:
                    w['status_k'].Update(
                        f'Status: Showing first {len(selected_games)} games only. Select one and press OK.')
                else:
                    w['status_k'].Update(
                        f'Status: Loaded {len(selected_games)} game(s). Select one and press OK.')
                continue

            if e == 'OK':
                try:
                    selected_text = v['game_k'][0]
                except IndexError:
                    w['status_k'].Update('Status: Please select a game.')
                    continue

                try:
                    selected_index = int(selected_text.split('.', 1)[0]) - 1
                except (IndexError, ValueError):
                    w['status_k'].Update('Status: Please select a valid game.')
                    continue
                if not 0 <= selected_index < len(selected_games):
                    w['status_k'].Update('Status: Please select a valid game.')
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
        """Prepare move list and board positions for review."""
        self.review_game = game
        self.review_game_index = game_index
        self.review_move_index = 0
        self.review_move_labels = ['Start position']
        self.review_boards = [game.board()]
        self.review_nodes = [game]
        self.review_analysis_lines = [''] * REVIEW_ANALYSIS_MULTIPV_LINES
        self.review_analysis_status = 'Analysis stopped'
        self.review_analysis_enabled = False
        self.review_analysis_stale = False
        self.review_threat_line = ''
        self.review_threat_status = 'Threat stopped'
        self.review_threat_enabled = False
        self.review_threat_stale = False

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

    def update_review_analysis_panel(self, window):
        """Refresh Review mode analysis widgets."""
        analysis_text = '\n'.join(
            line if line else ' ' for line in self.review_analysis_lines
        )
        window['review_analysis_status_k'].Update(self.review_analysis_status)
        window['review_analysis_k'].Update(analysis_text)

    def shorten_review_analysis_line(self, info_line):
        """Limit the Review mode PV display so it fits the analysis box."""
        try:
            prefix, pv_text = info_line.rsplit(' | ', 1)
        except ValueError:
            return info_line

        pv_moves = pv_text.split()
        limited_pv = ' '.join(pv_moves[:REVIEW_ANALYSIS_PV_MOVES])
        return '{} | {}'.format(prefix, limited_pv)

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
            self.review_analysis_lines = [''] * REVIEW_ANALYSIS_MULTIPV_LINES
            self.update_review_analysis_panel(window)
            return

        self.stop_review_analysis()
        self.review_analysis_enabled = True
        # Fresh search: its output is current, so poll must not discard it.
        self.review_analysis_stale = False
        self.review_analysis_lines = [''] * REVIEW_ANALYSIS_MULTIPV_LINES
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
            multipv=REVIEW_ANALYSIS_MULTIPV_LINES,
            option_overrides=self.get_role_options(
                'analysis', self.analysis_id_name)
        )
        search.get_board(self.review_boards[self.review_move_index].copy(stack=False))
        search.is_move_delay = False
        search.daemon = True
        search.start()
        self.review_analysis_search = search
        self.review_analysis_engine = None

    def refresh_review_analysis(self, window):
        """Restart analysis after the Review mode position changes."""
        if not self.review_analysis_enabled:
            self.review_analysis_lines = [''] * REVIEW_ANALYSIS_MULTIPV_LINES
            self.review_analysis_status = 'Analysis stopped'
            self.update_review_analysis_panel(window)
            return
        self.start_review_analysis(window)

    def reset_review_engines_for_new_game(self, window):
        """Stop and disable Review analysis/threat after loading a new game.

        A freshly loaded game starts with both panels cleanly 'stopped', so the
        next click on the Analysis/Threat button starts a new search. Loading
        used to auto-restart the searches, so if analysis was already on the
        first click — meant to start it — instead toggled the running search
        off, and only a second click showed output.
        """
        self.review_analysis_enabled = False
        self.review_threat_enabled = False
        self.review_analysis_stale = False
        self.review_threat_stale = False
        self.stop_review_analysis()
        self.stop_review_threat()
        self.review_analysis_lines = [''] * REVIEW_ANALYSIS_MULTIPV_LINES
        self.review_analysis_status = 'Analysis stopped'
        self.review_threat_line = ''
        self.review_threat_status = 'Threat stopped'
        self.update_review_analysis_panel(window)
        self.update_review_threat_panel(window)

    def confirm_auto_analysis(self, window):
        """Ask the user to pick an engine/time and confirm auto-analysis.

        Returns a dict with engine_id_name, engine_path_and_file and time_sec
        if the user confirms, otherwise False.
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

        default_time = self.auto_analysis_time_sec
        if not isinstance(default_time, int) or default_time < REVIEW_ANALYSIS_TIME_MIN:
            default_time = REVIEW_ANALYSIS_TIME_SEC

        def format_est(time_sec):
            approx = move_count * time_sec
            minutes, seconds = divmod(approx, 60)
            return '{:d}m {:d}s'.format(int(minutes), int(seconds))

        layout = [
            [sg.Text('Select engine and time per move for auto-analysis:')],
            [sg.Text('Engine:', size=(16, 1)),
             sg.Listbox(values=self.engine_id_name_list, size=(40, 6),
                        key='auto_engine_k',
                        default_values=[default_engine])],
            [sg.Text('Seconds per move:', size=(16, 1)),
             sg.Spin([t for t in range(REVIEW_ANALYSIS_TIME_MIN,
                                       REVIEW_ANALYSIS_TIME_MAX + 1)],
                     initial_value=default_time, size=(8, 1),
                     key='auto_time_k'),
             sg.Text('Estimated:', size=(10, 1)),
             sg.Text(format_est(default_time), size=(20, 1),
                     key='auto_est_k')],
            [sg.Text('Moves to analyze:', size=(16, 1)),
             sg.Text(str(move_count), size=(30, 1))],
            [sg.Text('The annotated game will be saved to:')],
            [sg.Text(AUTO_ANALYSIS_OUTPUT_FILE, size=(50, 1),
                     relief='sunken')],
            [sg.OK(), sg.Button('Configure'), sg.Cancel()],
        ]

        window.Hide()
        w = sg.Window('Auto-Analyze Game', layout,
                      icon=ico_path[platform]['pecg'])
        result = False
        while True:
            e, v = w.Read(timeout=10)
            if e == sg.TIMEOUT_KEY:
                continue
            if e is None or e == 'Cancel':
                break
            try:
                current_time = int(v['auto_time_k'])
                w['auto_est_k'].Update(format_est(current_time))
            except (TypeError, ValueError):
                pass
            if e == 'Configure':
                selected = v.get('auto_engine_k', [])
                eng = selected[0] if selected else None
                if eng is None:
                    sg.popup('Please select an engine to configure.',
                             title='Auto-Analyze',
                             icon=ico_path[platform]['pecg'])
                    continue
                w.Hide()
                self.configure_role_engine('auto_analysis', eng)
                w.UnHide()
                continue
            if e == 'OK':
                selected = v.get('auto_engine_k', [])
                engine_id_name = selected[0] if selected else None
                if engine_id_name is None:
                    sg.popup('Please select an engine.', title='Auto-Analyze',
                             icon=ico_path[platform]['pecg'])
                    continue
                try:
                    time_sec = int(v['auto_time_k'])
                except (TypeError, ValueError):
                    sg.popup('Invalid seconds per move.', title='Auto-Analyze',
                             icon=ico_path[platform]['pecg'])
                    continue
                time_sec = min(REVIEW_ANALYSIS_TIME_MAX,
                               max(REVIEW_ANALYSIS_TIME_MIN, time_sec))
                try:
                    eng_file, eng_path = self.get_engine_file(engine_id_name)
                except Exception:
                    logging.exception('Failed to resolve engine file.')
                    sg.popup('Failed to locate the selected engine.',
                             title='Auto-Analyze',
                             icon=ico_path[platform]['pecg'])
                    break
                self.auto_analysis_engine_id_name = engine_id_name
                self.auto_analysis_time_sec = time_sec
                self.save_settings()
                result = {
                    'engine_id_name': engine_id_name,
                    'engine_path_and_file': eng_path,
                    'time_sec': time_sec,
                }
                break
        w.Close()
        window.UnHide()
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
            config['time_sec'],
            self.auto_analysis_queue,
            self.auto_analysis_cancel,
            self.max_depth,
            option_overrides=self.get_role_options(
                'auto_analysis', config['engine_id_name'])
        )
        self.auto_analysis_thread.start()
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

            msg_str = str(msg)
            if 'multipv_info' in msg_str:
                # Skip stale analysis info: the search was stopped by navigation
                # and the engine is still draining old-position lines. A freshly
                # started search clears this flag, so its output is shown.
                if self.review_analysis_stale:
                    continue
                try:
                    line_no, info_line = msg_str.split(' | ', 1)
                    line_number = int(line_no.strip())
                    if not 1 <= line_number <= REVIEW_ANALYSIS_MULTIPV_LINES:
                        raise ValueError('Invalid MultiPV line number')
                    line_index = line_number - 1
                    info_line = info_line.rsplit(' multipv_info', 1)[0]
                    self.review_analysis_lines[line_index] = \
                        self.shorten_review_analysis_line(info_line)
                    updated = True
                except Exception:
                    logging.exception('Failed to parse Review mode analysis info.')
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
        """Refresh Review mode threat analysis widgets."""
        window['review_threat_status_k'].Update(self.review_threat_status)
        window['review_threat_k'].Update(
            self.review_threat_line if self.review_threat_line else ' ',
            text_color='red')

    def shorten_threat_line(self, info_line):
        """Limit the threat PV display to REVIEW_THREAT_PV_PLIES moves."""
        try:
            prefix, pv_text = info_line.rsplit(' | ', 1)
        except ValueError:
            return info_line

        pv_moves = pv_text.split()
        limited_pv = ' '.join(pv_moves[:REVIEW_THREAT_PV_PLIES])
        return '{} | {}'.format(prefix, limited_pv)

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
            self.review_threat_line = ''
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
            self.review_threat_line = ''
            self.update_review_threat_panel(window)
            logging.info('Threat analysis is unavailable at move index %d: king is in check.', self.review_move_index)
            return

        self.stop_review_threat()
        self.review_threat_line = ''
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
                'threat', self.threat_id_name)
        )
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
            self.review_threat_line = ''
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

            msg_str = str(msg)
            if 'info_all' in msg_str:
                # Skip stale threat info from the old position; a freshly started
                # search clears this flag so its output is shown (see
                # poll_review_analysis).
                if self.review_threat_stale:
                    continue
                info_line = msg_str.rsplit(' info_all', 1)[0]
                self.review_threat_line = self.shorten_threat_line(info_line)
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

        headers = self.review_game.headers
        header_text = '\n'.join([
            f"White: {headers.get('White', '?')}",
            f"Black: {headers.get('Black', '?')}",
            f"Event: {headers.get('Event', '?')}",
            f"Date: {headers.get('Date', '?')}    Result: {headers.get('Result', '*')}"
        ])

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

        self.set_board_from_board_state(
            window, self.review_boards[self.review_move_index])
        self.update_review_analysis_panel(window)
        self.update_review_threat_panel(window)

    def build_review_layout(self, is_user_white=True):
        """Create review mode layout with navigation controls."""
        sg.change_look_and_feel(self.gui_theme)
        sg.set_options(margins=(0, 3), border_width=1, font=FONT_BASE)

        board_layout = self.create_board(is_user_white)
        board_controls = [
            [sg.Text('Mode     Review', size=(36, 1), font=FONT_BASE,
                     key='_gamestatus_')],
            [sg.Text('PGN file', size=(8, 1), font=FONT_BASE),
             sg.Text('', size=(44, 1), font=FONT_SMALL,
                     key='review_pgn_k', relief='sunken')],
            [sg.TabGroup([
                [sg.Tab('Game details', [[sg.Multiline('', do_not_clear=True, autoscroll=False, size=(52, 4),
                                                       font=FONT_BASE, key='review_header_k',
                                                       disabled=True, expand_x=True, expand_y=True)]], font=FONT_BASE),
                 sg.Tab('Book moves', [[sg.Multiline('', do_not_clear=True, autoscroll=False, size=(52, 4),
                                                     font=FONT_BASE, key='review_book_k',
                                                     disabled=True, expand_x=True, expand_y=True)]], font=FONT_BASE)]
            ], font=FONT_BASE, key='review_tab_group_k', expand_x=True)],
            [sg.Text('Move list', size=(18, 1), font=FONT_BASE)],
            [sg.Multiline('', do_not_clear=True, autoscroll=False,
                          size=(52, REVIEW_MOVE_LIST_HEIGHT),
                          font=FONT_BASE, key='review_move_list_k',
                          disabled=True, expand_x=True, expand_y=True)],
            [sg.Text('Position 0/0', size=(20, 1), font=FONT_BASE,
                     key='review_nav_k', relief='sunken')],
            [sg.Text('Threat stopped', size=(55, 1), font=FONT_BASE,
                     key='review_threat_status_k', relief='sunken')],
            [sg.Multiline('', do_not_clear=True, autoscroll=False,
                          size=(52, REVIEW_THREAT_BOX_HEIGHT),
                          font=FONT_BASE, key='review_threat_k',
                          text_color='red', disabled=True, wrap_lines=False)],
            [sg.Text('Analysis stopped', size=(55, 1), font=FONT_BASE,
                     key='review_analysis_status_k', relief='sunken')],
            [sg.Multiline('', do_not_clear=True, autoscroll=False,
                          size=(52, REVIEW_ANALYSIS_BOX_HEIGHT),
                          font=FONT_BASE, key='review_analysis_k',
                          disabled=True, wrap_lines=False)],

        ]

        nav_buttons = sg.Column(
            [[sg.Button('First', size=(7, 1), font=FONT_BASE, pad=(1, 3)),
              sg.Button('Previous', size=(8, 1), font=FONT_BASE, pad=(1, 3)),
              sg.Button('Next', size=(7, 1), font=FONT_BASE, pad=(1, 3)),
              sg.Button('Last', size=(7, 1), font=FONT_BASE, pad=(1, 3))]],
            justification='left', pad=(0, 0))
        toggle_buttons = sg.Column(
            [[sg.Button('Analysis', key='review_toggle_analysis_k', size=(8, 1),
                        font=FONT_BASE, pad=(1, 3),
                        tooltip='Toggle engine analysis for the current position.'),
              sg.Button('Threat', key='review_toggle_threat_k', size=(7, 1),
                        font=FONT_BASE, pad=(1, 3),
                        tooltip='Toggle threat analysis: engine analyses what the '
                                'opponent threatens if the side to move were to pass.')]],
            justification='right', pad=(0, 0))

        # Pin the button bar to the board width: expand_x makes the bar fill the
        # board column and sg.Push() flush-rights Threat to the board's right
        # edge. compact_review_buttons() (run after finalize) trims each button's
        # Tk padding so all six fit inside the board width on Linux too, where the
        # default button padding is much larger than on Windows.
        button_bar = sg.Column(
            [[nav_buttons, sg.Push(), toggle_buttons]],
            expand_x=True, pad=(0, 0))

        board_column = [
            # pad=(0, 0) so the board column's width is exactly the board (no
            # extra side padding); the expand_x button_bar then matches the
            # board's left and right edges precisely.
            [sg.Column(board_layout, pad=(0, 0))],
            [button_bar]
        ]

        layout = [
            [sg.Menu(menu_def_review, tearoff=False, font=MENU_FONT)],
            [sg.Column(board_column, vertical_alignment='top'),
             sg.Column(board_controls, vertical_alignment='top', expand_y=True)]
        ]

        return layout

    def create_review_window(self, location=None):
        """Create a review window."""
        layout = self.build_review_layout(self.is_user_white)
        window = sg.Window(
            '{} {}'.format(APP_NAME, APP_VERSION),
            layout,
            default_button_element_size=(12, 1),
            auto_size_buttons=False,
            finalize=True,
            location=location,
            icon=ico_path[platform]['pecg']
        )
        self.configure_board_widgets(window)
        self.compact_review_buttons(window)
        self.apply_menu_font(window)
        self.bind_review_shortcuts(window)
        return window

    def bind_review_shortcuts(self, window):
        """Bind Alt+A and Alt+T to the Review window's toggle buttons.

        The bindings write the same event keys used by the Analysis and Threat
        buttons, so the existing event-loop handlers take over.
        """
        try:
            root = window.TKroot
            root.bind('<Alt-Key-a>',
                      lambda e: window.write_event_value(
                          'review_toggle_analysis_k', True))
            root.bind('<Alt-Key-t>',
                      lambda e: window.write_event_value(
                          'review_toggle_threat_k', True))
        except Exception:
            logging.exception('Failed to bind review window shortcuts.')

    def compact_review_buttons(self, window):
        """Shrink the under-board nav/toggle buttons' internal Tk padding.

        Classic Tk buttons default to padx='3m'/pady='1m' (~11 px per side on
        Linux/X11), so the six buttons span wider than the 480 px board and push
        the Threat button past the board's right edge. Windows uses tiny padding,
        which is why the overhang only showed on Linux. Force small, uniform
        padding so the whole button bar fits inside the board width everywhere.
        """
        for key in ('First', 'Previous', 'Next', 'Last',
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

        saved_orientation = self.is_user_white

        location = window.CurrentLocation()
        window.Hide()
        review_window = self.create_review_window(location=location)
        self.review_window = review_window
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

            if button == 'Neutral':
                self.cancel_auto_analysis(review_window)
                break

            if isinstance(button, str) and '::help_' in button:
                self.show_help_topic(button)
                continue

            if button == 'Load PGN::review_load_pgn_k':
                selected_game = self.select_review_game(
                    self.review_pgn_file, self.review_games)
                if selected_game is None:
                    continue

                self.review_pgn_file = selected_game['pgn_file']
                self.review_games = selected_game['games']
                self.prepare_review_game(
                    selected_game['game'], selected_game['game_index'])
                self.render_review_movelist(review_window)
                self.update_review_window(review_window)
                self.reset_review_engines_for_new_game(review_window)
                self.save_settings()
                continue

            if button == 'Select Game::review_select_game_k':
                selected_game = self.select_review_game(
                    self.review_pgn_file, self.review_games)
                if selected_game is None:
                    continue

                self.review_pgn_file = selected_game['pgn_file']
                self.review_games = selected_game['games']
                self.prepare_review_game(
                    selected_game['game'], selected_game['game_index'])
                self.render_review_movelist(review_window)
                self.update_review_window(review_window)
                self.reset_review_engines_for_new_game(review_window)
                self.save_settings()
                continue

            if button == 'Auto-Analyze Game::review_auto_analyze_k':
                self.start_auto_analysis(review_window)
                continue

            if button == 'Cancel Analysis::review_cancel_analysis_k':
                self.cancel_auto_analysis(review_window)
                continue

            if button == 'Flip':
                review_location = review_window.CurrentLocation()
                self.stop_review_analysis()
                self.stop_review_threat()
                review_window.Close()
                self.is_user_white = not self.is_user_white
                review_window = self.create_review_window(location=review_location)
                self.review_window = review_window
                self.render_review_movelist(review_window)
                # Restart via the debounce path so the engines (parked in the
                # stale lists by stop_review_* above) are reaped and reused
                # instead of cold-starting new processes for the flipped board.
                if self.review_analysis_enabled:
                    self.review_analysis_lines = [''] * REVIEW_ANALYSIS_MULTIPV_LINES
                    self.review_analysis_status = 'Waiting...'
                    self.review_analysis_stale = True
                if self.review_threat_enabled:
                    self.review_threat_line = ''
                    self.review_threat_status = 'Waiting...'
                    self.review_threat_stale = True
                if self.review_analysis_enabled or self.review_threat_enabled:
                    self.review_nav_last_time = time.time()
                self.update_review_window(review_window)
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
                    self.review_analysis_lines = [''] * REVIEW_ANALYSIS_MULTIPV_LINES
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
                    self.review_threat_line = ''
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
                if self.review_analysis_enabled or self.review_threat_enabled:
                    # Signal threads to stop without blocking.
                    # The actual join and restart happen in the debounce
                    # handler after the user stops pressing buttons.
                    if self.review_analysis_search is not None:
                        self.review_analysis_search.stop()
                    if self.review_threat_search is not None:
                        self.review_threat_search.stop()
                    # Mark current output stale so poll discards the old
                    # position's lines until a fresh search is started.
                    self.review_analysis_stale = True
                    self.review_threat_stale = True
                    self.review_nav_last_time = time.time()
                    self.review_analysis_lines = [''] * REVIEW_ANALYSIS_MULTIPV_LINES
                    self.review_analysis_status = 'Waiting...'
                    self.review_threat_line = ''
                    self.review_threat_status = 'Waiting...'
                    self.update_review_analysis_panel(review_window)
                    self.update_review_threat_panel(review_window)
                else:
                    self.refresh_review_analysis(review_window)
                    self.refresh_review_threat(review_window)

        self.close_review_analysis()
        self.close_review_threat()
        review_window.Close()
        self.review_window = None
        self.reset_review_run_state()
        self.is_user_white = saved_orientation
        window.UnHide()

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

    def create_board(self, is_user_white=True):
        """
        Returns board layout based on color of user. If user is white,
        the white pieces will be at the bottom, otherwise at the top.

        :param is_user_white: user has handling the white pieces
        :return: board layout
        """
        file_char_name = 'abcdefgh'
        self.psg_board = copy.deepcopy(initial_board)

        board_layout = []

        if is_user_white:
            # Save the board with black at the top.
            start = 0
            end = 8
            step = 1
        else:
            start = 7
            end = -1
            step = -1
            file_char_name = file_char_name[::-1]

        # Loop through the board and create buttons with images
        for i in range(start, end, step):
            # Row numbers at left of board is blank
            row = []
            for j in range(start, end, step):
                piece_image = images[self.psg_board[i][j]]
                row.append(self.render_square(piece_image, key=(i, j), location=(i, j)))
            board_layout.append(row)

        return board_layout

    def build_main_layout(self, is_user_white=True):
        """
        Creates all elements for the GUI, icluding the board layout.

        :param is_user_white: if user is white, the white pieces are
        oriented such that the white pieces are at the bottom.
        :return: GUI layout
        """
        sg.change_look_and_feel(self.gui_theme)
        sg.set_options(margins=(0, 3), border_width=1, font=FONT_BASE)

        # Define board
        board_layout = self.create_board(is_user_white)

        board_controls = [
            [sg.Text('Mode     Neutral', size=(36, 1), font=FONT_BASE, key='_gamestatus_')],
            [sg.Text('White', size=(7, 1), font=FONT_BASE),
             sg.Text('Human', font=FONT_BASE, key='_White_',
                     size=(24, 1), relief='sunken'),
             sg.Text('', font=FONT_BASE, key='w_base_time_k',
                     size=(11, 1), relief='sunken'),
             sg.Text('', font=FONT_BASE, key='w_elapse_k', size=(7, 1),
                     relief='sunken')
             ],
            [sg.Text('Black', size=(7, 1), font=FONT_BASE),
             sg.Text('Computer', font=FONT_BASE, key='_Black_',
                     size=(24, 1), relief='sunken'),
             sg.Text('', font=FONT_BASE, key='b_base_time_k',
                     size=(11, 1), relief='sunken'),
             sg.Text('', font=FONT_BASE, key='b_elapse_k', size=(7, 1),
                     relief='sunken')
             ],
            [sg.Text('Adviser', size=(7, 1), font=FONT_BASE, key='adviser_k',
                     right_click_menu=[
                        'Right',
                        ['Start::right_adviser_k', 'Stop::right_adviser_k']
                    ]),
             sg.Text('', font=FONT_BASE, key='advise_info_k', relief='sunken',
                     size=(46, 1))],

            [sg.Text('Move list', size=(16, 1), font=FONT_BASE)],
            [sg.Multiline('', do_not_clear=True, autoscroll=True, size=(52, 8),
                          font=FONT_BASE, key='_movelist_', disabled=True)],

            [sg.Text('Comment', size=(7, 1), font=FONT_BASE)],
            [sg.Multiline('', do_not_clear=True, autoscroll=True, size=(52, 3),
                          font=FONT_BASE, key='comment_k')],

            [sg.Text('BOOK 1, Comp games', size=(26, 1),
                     font=FONT_BASE,
                     right_click_menu=['Right', ['Show::right_book1_k', 'Hide::right_book1_k']]),
             sg.Text('BOOK 2, Human games',
                     font=FONT_BASE,
                     right_click_menu=['Right', ['Show::right_book2_k', 'Hide::right_book2_k']])],
            [sg.Multiline('', do_not_clear=True, autoscroll=False, size=(23, 4),
                           font=FONT_BASE, key='polyglot_book1_k', disabled=True),
             sg.Multiline('', do_not_clear=True, autoscroll=False, size=(25, 4),
                           font=FONT_BASE, key='polyglot_book2_k', disabled=True)],
            [sg.Text('Opponent Search Info', font=FONT_BASE, size=(30, 1),
                     right_click_menu=['Right',
                                       ['Show::right_search_info_k', 'Hide::right_search_info_k']])],
            [sg.Text('', key='search_info_all_k', size=(55, 1),
                     font=FONT_BASE, relief='sunken')],
        ]

        self.menu_elem = sg.Menu(menu_def_neutral, tearoff=False, font=MENU_FONT)

        board_column = [
            [sg.Column(board_layout, pad=(0, 0))]
        ]

        # White board layout, mode: Neutral
        layout = [
                [self.menu_elem],
                [sg.Column(board_column, vertical_alignment='top'),
                 sg.Column(board_controls, vertical_alignment='top', expand_y=True)]
        ]

        return layout

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

    def main_loop(self):
        """
        Build GUI, read user and engine config files and take user inputs.

        :return:
        """
        engine_id_name = None
        layout = self.build_main_layout(True)

        # Use white layout as default window
        window = sg.Window('{} {}'.format(APP_NAME, APP_VERSION),
                           layout, default_button_element_size=(12, 1),
                           auto_size_buttons=False,
                           finalize=True,
                           icon=ico_path[platform]['pecg'])

        # Read user config file, if missing create and new one
        self.check_user_config_file()

        # Load persisted Settings/Game values (checkboxes, review times).
        self.load_settings()

        # If engine config file (pecg_engines.json) is missing, then create it.
        self.check_engine_config_file()
        self.engine_id_name_list = self.get_engine_id_name_list()

        # Define default opponent engine, user can change this later.
        engine_id_name = self.get_default_engine_opponent()

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

        # Set up drag-and-drop bindings for board squares
        self.setup_board_drag_drop(window)
        self.redraw_board(window)

        # Match the Linux menubar font to Windows (no-op on Windows/macOS).
        self.apply_menu_font(window)

        # Mode: Neutral, main loop starts here
        while True:
            button, value = window.Read(timeout=50)

            # Mode: Neutral
            if button is None:
                logging.info('Quit app from main loop, X is pressed.')
                break

            # Mode: Neutral, Delete player
            if button == 'Delete Player::delete_player_k':
                win_title = 'Tools/Delete Player'
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

                window.Hide()
                w = sg.Window(win_title, layout,
                              icon=ico_path[platform]['pecg'])
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

                        t1 = time.perf_counter()
                        que = queue.Queue()
                        t = threading.Thread(
                            target=self.get_players,
                            args=(pgn, que,),
                            daemon=True
                        )
                        t.start()
                        msg = None
                        while True:
                            e1, v1 = w.Read(timeout=100)
                            w.Element('status_k').Update(
                                'Display Players: processing ...')
                            try:
                                msg = que.get_nowait()
                                elapse = int(time.perf_counter() - t1)
                                w.Element('status_k').Update(
                                    'Players are displayed. Done! in ' +
                                    str(elapse) + 's')
                                break
                            except Exception:
                                continue
                        t.join()
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

                        t1 = time.perf_counter()
                        que = queue.Queue()
                        t = threading.Thread(
                            target=self.delete_player,
                            args=(player_name, v['pgn_k'], que,),
                            daemon=True
                        )
                        t.start()
                        msg = None
                        while True:
                            e1, v1 = w.Read(timeout=100)
                            w.Element('status_k').Update(
                                'Status: Delete: processing ...')
                            try:
                                msg = que.get_nowait()
                                if msg == 'Done':
                                    elapse = int(time.perf_counter() - t1)
                                    w.Element('status_k').Update(
                                        player_name + ' was deleted. Done! '
                                        'in ' + str(elapse) + 's')
                                    break
                                else:
                                    w.Element('status_k').Update(
                                        msg + '/' + str(sum_games))
                            except Exception:
                                continue
                        t.join()

                        # Update player list in listbox
                        player_list.remove(player_name)
                        w.Element('player_k').Update(sorted(player_list))

                w.Close()
                window.UnHide()
                continue

            # Mode: Neutral, Set User time control
            if button == 'User::tc_k':
                win_title = 'Time/User'
                layout = [
                    [sg.T('Base time (minute)', size=(16, 1)),
                     sg.Input(self.human_base_time_ms/60/1000,
                              key='base_time_k', size=(8, 1))],
                    [sg.T('Increment (second)', size=(16, 1)),
                     sg.Input(self.human_inc_time_ms/1000, key='inc_time_k',
                              size=(8, 1))],
                    [sg.T('Period moves', size=(16, 1), visible=False),
                     sg.Input(self.human_period_moves, key='period_moves_k',
                              size=(8, 1), visible=False)],
                    [sg.Radio('Fischer', 'tc_radio', key='fischer_type_k',
                              default=True if self.human_tc_type == 'fischer' else False),
                     sg.Radio('Delay', 'tc_radio', key='delay_type_k',
                              default=True if self.human_tc_type == 'delay' else False)],
                    [sg.OK(), sg.Cancel()]
                ]

                window.Hide()
                w = sg.Window(win_title, layout,
                              icon=ico_path[platform]['pecg'])
                while True:
                    e, v = w.Read(timeout=10)
                    if e is None:
                        break
                    if e == 'Cancel':
                        break
                    if e == 'OK':
                        base_time_ms = int(1000 * 60 * float(v['base_time_k']))
                        inc_time_ms = int(1000 * float(v['inc_time_k']))
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
                window.UnHide()
                continue

            # Mode: Neutral, Set engine time control
            if button == 'Engine::tc_k':
                win_title = 'Time/Engine'
                layout = [
                    [sg.T('Base time (minute)', size=(16, 1)),
                     sg.Input(self.engine_base_time_ms / 60 / 1000,
                              key='base_time_k', size=(8, 1))],
                    [sg.T('Increment (second)', size=(16, 1)),
                     sg.Input(self.engine_inc_time_ms / 1000,
                              key='inc_time_k',
                              size=(8, 1))],
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

                window.Hide()
                w = sg.Window(win_title, layout,
                              icon=ico_path[platform]['pecg'])
                while True:
                    e, v = w.Read(timeout=10)
                    if e is None:
                        break
                    if e == 'Cancel':
                        break
                    if e == 'OK':
                        base_time_ms = int(
                            1000 * 60 * float(v['base_time_k']))
                        inc_time_ms = int(1000 * float(v['inc_time_k']))
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
                window.UnHide()
                continue

            # Mode: Neutral, manage player names
            if button == 'Set Name::user_name_k':
                win_title = 'User/Player'
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
                window.Hide()
                w = sg.Window(win_title, layout,
                              icon=ico_path[platform]['pecg'], finalize=True)
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
                window.UnHide()
                self.update_labels_and_game_tags(window, human=self.username)
                continue

            # Mode: Neutral
            if button == 'Install':
                button_title = 'Engine/Manage/' + button
                new_engine_path_file, new_engine_id_name = None, None

                install_layout = [
                        [sg.Text('Current configured engine names')],
                        [sg.Listbox(values=self.engine_id_name_list,
                                    size=(48, 10), disabled=True)],
                        [sg.Button('Add'), sg.Button('Cancel')]
                ]

                window.Hide()
                install_win = sg.Window(title=button_title,
                                        layout=install_layout,
                                        icon=ico_path[platform]['pecg'])

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

                        install_win.Hide()
                        add_win = sg.Window(button_title, add_layout)
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
                                if new_engine_path_file:
                                    que = queue.Queue()
                                    t = threading.Thread(
                                        target=self.get_engine_id_name,
                                        args=(new_engine_path_file, que,),
                                        daemon=True
                                    )
                                    t.start()
                                    is_update_list = False
                                    while True:
                                        try:
                                            msg = que.get_nowait()
                                            break
                                        except Exception:
                                            pass
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
                        install_win.UnHide()

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
                window.UnHide()

                # Define default engine opponent and adviser
                if engine_id_name is None:
                    engine_id_name = self.get_default_engine_opponent()
                if self.adviser_id_name is None:
                    self.set_default_adviser_engine()
                if self.analysis_id_name is None:
                    self.set_default_analysis_engine()

                self.update_labels_and_game_tags(window, human=self.username)

                continue

            # Mode: Neutral
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

                window.Hide()
                edit_win = sg.Window(
                    button_title,
                    layout=edit_layout,
                    icon=ico_path[platform]['pecg']
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

                        edit_win.Hide()
                        modify_win = sg.Window(button_title,
                                               layout=modify_layout,
                                               icon=ico_path[platform]['pecg'],
                                               resizable=True, finalize=True)
                        is_cancel_modify_win = False
                        while True:
                            e1, v1 = modify_win.Read(timeout=100)
                            if e1 is None or e1 == 'Cancel':
                                is_cancel_modify_win = True
                                break
                            if e1 == 'OK':
                                engine_id_name = v1['string_name_k']
                                ret_opt_name = [
                                    {n: val} for n, val in
                                    self.read_option_values(
                                        v1, opt_meta).items()]
                                break

                        edit_win.UnHide()
                        modify_win.Close()
                        break  # Get out of edit_win loop

                # Outside edit_win while loop

                # Save the new configured engine to pecg_engines.json file
                if not is_cancel_edit_win and not is_cancel_modify_win:
                    self.update_engine_to_config_file(
                        engine_path_file, engine_id_name,
                        orig_idname, ret_opt_name)
                    self.engine_id_name_list = self.get_engine_id_name_list()

                edit_win.Close()
                window.UnHide()
                continue

            # Mode: Neutral
            if button == 'Delete':
                button_title = 'Engine/Manage/' + button
                delete_layout = [
                    [sg.Text('Current configured engine names')],
                    [sg.Listbox(values=self.engine_id_name_list, size=(48, 10),
                                key='engine_id_name_k')],
                    [sg.Button('Delete'), sg.Cancel()]
                ]
                window.Hide()
                delete_win = sg.Window(
                    button_title,
                    layout=delete_layout,
                    icon=ico_path[platform]['pecg']
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

                delete_win.Close()
                window.UnHide()

                continue

            # Mode: Neutral, engine role managers (configure options + select).
            if button == 'Set Engine Opponent':
                self.manage_role_engine(window, 'opponent')
                continue

            if button == 'Set Engine Adviser':
                self.manage_role_engine(window, 'adviser')
                continue

            if button == 'Set Engine Analysis':
                self.manage_role_engine(window, 'analysis')
                continue

            if button == 'Set Engine Threat':
                self.manage_role_engine(window, 'threat')
                continue

            # Mode: Neutral
            if button == 'Set Depth':
                self.set_depth_limit()
                continue

            # Mode: Neutral, Allow user to change book settings
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
                         sg.Spin([t for t in range(1, 33, 1)],
                                 initial_value=self.max_book_ply,
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
                              icon=ico_path[platform]['pecg'])
                window.Hide()

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

                window.UnHide()
                w.Close()
                continue

            # Mode: Neutral, Settings menu
            if button == 'Game::settings_game_k':
                win_title = 'Settings/Game'
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
                     sg.Input(default_text=str(self.review_analysis_time_sec),
                              key='review_analysis_time_k', size=(6, 1))],
                    [sg.Text('Review threat time (sec)', size=(24, 1),
                             tooltip='Maximum time the Review threat engine\n' +
                                     'searches a position before stopping\n' +
                                     '({} to {}).'.format(
                                         REVIEW_ANALYSIS_TIME_MIN,
                                         REVIEW_ANALYSIS_TIME_MAX)),
                     sg.Input(default_text=str(self.review_threat_time_sec),
                              key='review_threat_time_k', size=(6, 1))],
                    [sg.OK(), sg.Cancel()],
                ]

                w = sg.Window(win_title, layout,
                              icon=ico_path[platform]['pecg'])
                window.Hide()

                while True:
                    e, v = w.Read(timeout=10)
                    if e is None or e == 'Cancel':
                        break
                    if e == 'OK':
                        self.is_save_time_left = v['save_time_left_k']
                        self.is_time_forfeit_enabled = v['time_forfeit_k']
                        self.review_analysis_time_sec = self._read_review_time(
                            v['review_analysis_time_k'],
                            self.review_analysis_time_sec)
                        self.review_threat_time_sec = self._read_review_time(
                            v['review_threat_time_k'],
                            self.review_threat_time_sec)
                        self.save_settings()
                        break

                window.UnHide()
                w.Close()
                continue

            # Mode: Neutral, Change theme
            if button in GUI_THEME:
                self.gui_theme = button
                window = self.create_new_window(window)
                continue

            # Mode: Neutral, Change board to gray
            if button == 'Gray::board_color_k':
                self.sq_light_color = '#D8D8D8'
                self.sq_dark_color = '#808080'
                self.move_sq_light_color = '#e0e0ad'
                self.move_sq_dark_color = '#999966'
                self.redraw_board(window)
                window = self.create_new_window(window)
                continue

            # Mode: Neutral, Change board to green
            if button == 'Green::board_color_k':
                self.sq_light_color = '#daf1e3'
                self.sq_dark_color = '#3a7859'
                self.move_sq_light_color = '#bae58f'
                self.move_sq_dark_color = '#6fbc55'
                self.redraw_board(window)
                window = self.create_new_window(window)
                continue

            # Mode: Neutral, Change board to blue
            if button == 'Blue::board_color_k':
                self.sq_light_color = '#b9d6e8'
                self.sq_dark_color = '#4790c0'
                self.move_sq_light_color = '#d2e4ba'
                self.move_sq_dark_color = '#91bc9c'
                self.redraw_board(window)
                window = self.create_new_window(window)
                continue

            # Mode: Neutral, Change board to brown, default
            if button == 'Brown::board_color_k':
                self.sq_light_color = '#F0D9B5'
                self.sq_dark_color = '#B58863'
                self.move_sq_light_color = '#E8E18E'
                self.move_sq_dark_color = '#B8AF4E'
                self.redraw_board(window)
                window = self.create_new_window(window)
                continue

            # Mode: Neutral
            if button == 'Flip':
                window.find_element('_gamestatus_').Update('Mode     Neutral')
                self.clear_elements(window)
                window = self.create_new_window(window, True)
                continue

            # Mode: Neutral
            if isinstance(button, str) and '::help_' in button:
                self.show_help_topic(button)
                continue

            # Mode: Neutral
            if button == 'Review':
                self.start_review_mode(window)
                continue

            # Mode: Neutral
            if button == 'Play':
                if engine_id_name is None:
                    logging.warning('Install engine first!')
                    sg.popup('Install engine first! in Engine/Manage/Install',
                             icon=ico_path[platform]['pecg'], title='Mode')
                    continue

                # Change menu from Neutral to Play
                self.menu_elem.Update(menu_def_play)
                self.apply_menu_font(window)
                self.psg_board = copy.deepcopy(initial_board)
                board = chess.Board()

                while True:
                    button, value = window.Read(timeout=100)

                    window.find_element('_gamestatus_').Update('Mode     Play')
                    window.find_element('_movelist_').Update(disabled=False)
                    window.find_element('_movelist_').Update('', disabled=True)

                    start_new_game = self.play_game(window, board)
                    window.find_element('_gamestatus_').Update('Mode     Neutral')

                    self.psg_board = copy.deepcopy(initial_board)
                    self.redraw_board(window)
                    board = chess.Board()
                    self.set_new_game()

                    if not start_new_game:
                        break

                # Restore Neutral menu
                self.menu_elem.Update(menu_def_neutral)
                self.apply_menu_font(window)
                self.psg_board = copy.deepcopy(initial_board)
                board = chess.Board()
                self.set_new_game()
                continue

        window.Close()


def main():
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

    pecg = EasyChessGui(theme, engine_config_file, user_config_file,
                        pecg_book, book_from_computer_games,
                        book_from_human_games, is_use_gui_book, is_random_book,
                        max_book_ply)

    pecg.main_loop()


if __name__ == "__main__":
    main()
