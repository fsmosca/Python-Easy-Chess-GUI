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
import platform as sys_plat


log_format = '%(asctime)s :: %(funcName)s :: line: %(lineno)d :: %(levelname)s :: %(message)s'
logging.basicConfig(
    filename='pecg_log.txt',
    filemode='w',
    level=logging.DEBUG,
    format=log_format
)


APP_NAME = 'Python Easy Chess GUI'
APP_VERSION = 'v1.19.0'
BOX_TITLE = f'{APP_NAME} {APP_VERSION}'


platform = sys.platform
sys_os = sys_plat.system()


ico_path = {
    'win32': {'pecg': 'Icon/pecg.ico', 'enemy': 'Icon/enemy.ico', 'adviser': 'Icon/adviser.ico'},
    'linux': {'pecg': 'Icon/pecg.png', 'enemy': 'Icon/enemy.png', 'adviser': 'Icon/adviser.png'},
    'darwin': {'pecg': 'Icon/pecg.png', 'enemy': 'Icon/enemy.png', 'adviser': 'Icon/adviser.png'}
}


MIN_DEPTH = 1
MAX_DEPTH = 1000
MANAGED_UCI_OPTIONS = ['ponder', 'uci_chess960', 'multipv', 'uci_analysemode', 'ownbook']
GUI_THEME = [
    'Green', 'GreenTan', 'LightGreen', 'BluePurple', 'Purple', 'BlueMono', 'GreenMono', 'BrownBlue',
    'BrightColors', 'NeutralBlue', 'Kayak', 'SandyBeach', 'TealMono', 'Topanga', 'Dark', 'Black', 'DarkAmber'
]

IMAGE_PATH = 'Images/60'  # path to the chess pieces


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


HELP_MSG = """The GUI has 2 modes, Play and Neutral. After startup
you are in Neutral mode. You can go to mode Play through Mode menu.

All games are auto-saved in pecg_auto_save_games.pgn.
Visit Game menu in Play mode to see other options to save the game.

It has to be noted you need to setup an engine to make the GUI works.
You can view which engines are ready for use via:
Engine->Set Engine Opponent.

(A) To setup an engine, you should be in Neutral mode.
1. Engine->Manage->Install, press the add button.
2. After engine setup, you can configure the engine options with:
  a. Engine->Manage-Edit
  b. Select the engine you want to edit and press Modify.

Before playing a game, you should select an engine opponent via
Engine->Set Engine Opponent.

You can also set an engine Adviser in the Engine menu.
During a game you can ask help from Adviser by right-clicking
the Adviser label and press show.

(B) To play a game
You should be in Play mode.
1. Mode->Play
2. Make move on the board

(C) To play as black
You should be in Neutral mode
1. Board->Flip
2. Mode->Play
3. Engine->Go
If you are already in Play mode, go back to
Neutral mode via Mode->Neutral

(D) To flip board
You should be in Neutral mode
1. Board->Flip

(E) To paste FEN
You should be in Play mode
1. Mode->Play
2. FEN->Paste

(F) To show engine search info after the move
1. Right-click on the Opponent Search Info and press Show

(G) To Show book 1 and 2
1. Right-click on Book 1 or 2 press Show

(H) To change board color
1. You should be in Neutral mode.
2. Board->Color.

(I) To change board theme
1. You should be in Neutral mode.
2. Board->Theme.
"""


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
        ['&Mode', ['Play']],
        ['Boar&d', ['Flip', 'Color', ['Brown::board_color_k',
                                      'Blue::board_color_k',
                                      'Green::board_color_k',
                                      'Gray::board_color_k'],
                    'Theme', GUI_THEME]],
        ['&Engine', ['Set Engine Adviser', 'Set Engine Opponent', 'Set Depth',
                     'Manage', ['Install', 'Edit', 'Delete']]],
        ['&Time', ['User::tc_k', 'Engine::tc_k']],
        ['&Book', ['Set Book::book_set_k']],
        ['&User', ['Set Name::user_name_k']],
        ['Tools', ['PGN', ['Delete Player::delete_player_k']]],
        ['&Settings', ['Game::settings_game_k']],
        ['&Help', ['GUI']],
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
        ['&Help', ['GUI']],
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
                 period_moves=0, is_stream_search_info=True):
        """
        Run engine as opponent or as adviser.

        :param eng_queue:
        :param engine_config_file: pecg_engines.json
        :param engine_path_and_file:
        :param engine_id_name:
        :param max_depth:
        """
        threading.Thread.__init__(self)
        self._kill = threading.Event()
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
        self.engine = None
        self.board = None
        self.analysis = is_stream_search_info
        self.is_nomove_number_in_variation = True
        self.base_ms = base_ms
        self.inc_ms = inc_ms
        self.tc_type = tc_type
        self.period_moves = period_moves
        self.is_ownbook = False
        self.is_move_delay = True

    def stop(self):
        """Interrupt engine search."""
        self._kill.set()

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
            for p in data:
                if p['name'] == self.engine_id_name:
                    for n in p['options']:

                        if n['name'].lower() == 'ownbook':
                            self.is_ownbook = True

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

    def run(self):
        """Run engine to get search info and bestmove.
         
        If there is error we still send bestmove None.
        """
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

        # Set search limits
        if self.tc_type == 'delay':
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

            with self.engine.analysis(self.board, limit) as analysis:
                for info in analysis:

                    if self._kill.wait(0.1):
                        break

                    try:
                        if 'depth' in info:
                            self.depth = int(info['depth'])

                        if 'score' in info:
                            self.score = int(info['score'].relative.score(mate_score=32000))/100

                        self.time = info['time'] if 'time' in info else time.perf_counter() - start_time

                        if 'pv' in info and not ('upperbound' in info or
                                                 'lowerbound' in info):
                            self.pv = info['pv'][0:self.pv_length]

                            if self.is_nomove_number_in_variation:
                                spv = self.short_variation_san()
                                self.pv = spv
                            else:
                                self.pv = self.board.variation_san(self.pv)

                            self.eng_queue.put('{} pv'.format(self.pv))
                            self.bm = info['pv'][0]

                        # score, depth, time, pv
                        if self.score is not None and \
                                self.pv is not None and self.depth is not None:
                            info_to_send = '{:+5.2f} | {} | {:0.1f}s | {} info_all'.format(
                                    self.score, self.depth, self.time, self.pv)
                            self.eng_queue.put('{}'.format(info_to_send))

                        # Send stop if movetime is exceeded
                        if not is_time_check and self.tc_type != 'fischer' \
                                and self.tc_type != 'delay' and \
                                time.perf_counter() - start_time >= \
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
                if time.perf_counter() - start_time >= self.move_delay_sec:
                    break
                logging.info('Delay sending of best move {}'.format(self.bm))
                time.sleep(1.0)

        # If bm is None, we will use engine.play()
        if self.bm is None:
            logging.info('bm is none, we will try engine,play().')
            try:
                result = self.engine.play(self.board, limit)
                self.bm = result.move
            except Exception:
                logging.exception('Failed to get engine bestmove.')
        self.eng_queue.put(f'bestmove {self.bm}')
        logging.info(f'bestmove {self.bm}')

    def quit_engine(self):
        """Quit engine."""
        logging.info('quit engine')
        try:
            self.engine.quit()
        except AttributeError:
            logging.info('AttributeError, self.engine is already None')
        except Exception:
            logging.exception('Failed to quit engine.')

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
        self.my_games = 'pecg_my_games.pgn'
        self.repertoire_file = {
            'white': 'pecg_white_repertoire.pgn',
            'black': 'pecg_black_repertoire.pgn'
        }
        self.init_game()
        self.fen = None
        self.psg_board = None
        self.menu_elem = None
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
            icon=ico_path[platform]['pecg']
        )

        # Initialize White and black boxes
        while True:
            button, value = w.Read(timeout=50)
            self.update_labels_and_game_tags(w, human=self.username)
            break

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

    def update_user_config_file(self, username):
        """
        Update user config file. If username does not exist, save it.
        :param username:
        :return:
        """
        with open(self.user_config_file, 'r') as json_file:
            data = json.load(json_file)

        # Add the new entry if it does not exist
        is_name = False
        for i in range(len(data)):
            if data[i]['username'] == username:
                is_name = True
                break

        if not is_name:
            data.append({'username': username})

            # Save
            with open(self.user_config_file, 'w') as h:
                json.dump(data, h, indent=4)

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
                sg.Popup(
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
        user_depth = sg.PopupGetText(
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
        is_search_stop_for_exit = False
        is_search_stop_for_new_game = False
        is_search_stop_for_neutral = False
        is_search_stop_for_resign = False
        is_search_stop_for_user_wins = False
        is_search_stop_for_user_draws = False
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

                    if button == 'GUI':
                        sg.PopupScrolled(HELP_MSG, title=BOX_TITLE)
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
                            is_stream_search_info=True
                        )
                        search.get_board(board)
                        search.daemon = True
                        search.start()

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
                                if 'pv' in msg:
                                    # Reformat msg, remove the word pv at the end
                                    msg_line = ' '.join(msg.split()[0:-1])
                                    window.Element('advise_info_k').Update(msg_line)
                            except Exception:
                                continue

                            if 'bestmove' in msg:
                                # bestmove can be None so we do try/except
                                try:
                                    # Shorten msg line to 3 ply moves
                                    msg_line = ' '.join(msg_line.split()[0:3])
                                    msg_line += ' - ' + self.adviser_id_name
                                    window.Element('advise_info_k').Update(msg_line)
                                except Exception:
                                    logging.exception('Adviser engine error')
                                    sg.Popup(
                                        f'Adviser engine {self.adviser_id_name} error.\n \
                                        It is better to change this engine.\n \
                                        Change to Neutral mode first.',
                                        icon=ico_path[platform]['pecg'],
                                        title=BOX_TITLE
                                    )
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
                        reply = sg.Popup('Do you really want to resign?',
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
                    if button == 'GUI':
                        sg.PopupScrolled(HELP_MSG, title=BOX_TITLE,)
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
                            sg.Popup('Press Game->New then paste your fen.',
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
                        is_user_resigns or is_user_wins or is_user_draws):
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
                        period_moves=board.fullmove_number
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
                    search.quit_engine()
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
        if is_user_resigns:
            self.game.headers['Result'] = '0-1' if self.is_user_white else '1-0'
            self.game.headers['Termination'] = '{} resigns'.format(
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
            sg.Popup('Game is over.', title=BOX_TITLE,
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
        sg.ChangeLookAndFeel(self.gui_theme)
        sg.SetOptions(margins=(0, 3), border_width=1)

        # Define board
        board_layout = self.create_board(is_user_white)

        board_controls = [
            [sg.Text('Mode     Neutral', size=(36, 1), font=('Consolas', 10), key='_gamestatus_')],
            [sg.Text('White', size=(7, 1), font=('Consolas', 10)),
             sg.Text('Human', font=('Consolas', 10), key='_White_',
                     size=(24, 1), relief='sunken'),
             sg.Text('', font=('Consolas', 10), key='w_base_time_k',
                     size=(11, 1), relief='sunken'),
             sg.Text('', font=('Consolas', 10), key='w_elapse_k', size=(7, 1),
                     relief='sunken')
             ],
            [sg.Text('Black', size=(7, 1), font=('Consolas', 10)),
             sg.Text('Computer', font=('Consolas', 10), key='_Black_',
                     size=(24, 1), relief='sunken'),
             sg.Text('', font=('Consolas', 10), key='b_base_time_k',
                     size=(11, 1), relief='sunken'),
             sg.Text('', font=('Consolas', 10), key='b_elapse_k', size=(7, 1),
                     relief='sunken')
             ],
            [sg.Text('Adviser', size=(7, 1), font=('Consolas', 10), key='adviser_k',
                     right_click_menu=[
                        'Right',
                        ['Start::right_adviser_k', 'Stop::right_adviser_k']
                    ]),
             sg.Text('', font=('Consolas', 10), key='advise_info_k', relief='sunken',
                     size=(46, 1))],

            [sg.Text('Move list', size=(16, 1), font=('Consolas', 10))],
            [sg.Multiline('', do_not_clear=True, autoscroll=True, size=(52, 8),
                          font=('Consolas', 10), key='_movelist_', disabled=True)],

            [sg.Text('Comment', size=(7, 1), font=('Consolas', 10))],
            [sg.Multiline('', do_not_clear=True, autoscroll=True, size=(52, 3),
                          font=('Consolas', 10), key='comment_k')],

            [sg.Text('BOOK 1, Comp games', size=(26, 1),
                     font=('Consolas', 10),
                     right_click_menu=['Right', ['Show::right_book1_k', 'Hide::right_book1_k']]),
             sg.Text('BOOK 2, Human games',
                     font=('Consolas', 10),
                     right_click_menu=['Right', ['Show::right_book2_k', 'Hide::right_book2_k']])],
            [sg.Multiline('', do_not_clear=True, autoscroll=False, size=(23, 4),
                          font=('Consolas', 10), key='polyglot_book1_k', disabled=True),
             sg.Multiline('', do_not_clear=True, autoscroll=False, size=(25, 4),
                          font=('Consolas', 10), key='polyglot_book2_k', disabled=True)],
            [sg.Text('Opponent Search Info', font=('Consolas', 10), size=(30, 1),
                     right_click_menu=['Right',
                                       ['Show::right_search_info_k', 'Hide::right_search_info_k']])],
            [sg.Text('', key='search_info_all_k', size=(55, 1),
                     font=('Consolas', 10), relief='sunken')],
        ]

        board_tab = [[sg.Column(board_layout)]]

        self.menu_elem = sg.Menu(menu_def_neutral, tearoff=False)

        # White board layout, mode: Neutral
        layout = [
                [self.menu_elem],
                [sg.Column(board_tab), sg.Column(board_controls)]
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
                           icon=ico_path[platform]['pecg'])

        # Read user config file, if missing create and new one
        self.check_user_config_file()

        # If engine config file (pecg_engines.json) is missing, then create it.
        self.check_engine_config_file()
        self.engine_id_name_list = self.get_engine_id_name_list()

        # Define default opponent engine, user can change this later.
        engine_id_name = self.get_default_engine_opponent()

        # Define default adviser engine, user can change this later.
        self.set_default_adviser_engine()

        self.init_game()

        # Initialize White and black boxes
        while True:
            button, value = window.Read(timeout=50)
            self.update_labels_and_game_tags(window, human=self.username)
            break

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
                    [sg.Button('Display Players', size=(48, 1))],
                    [sg.Text('Status:', size=(48, 1), key='status_k', relief='sunken')],
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
                            sg.Popup(
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
                            sg.Popup('Please locate your pgn file by '
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

            # Mode: Neutral, set username
            if button == 'Set Name::user_name_k':
                win_title = 'User/username'
                layout = [
                        [sg.Text('Current username: {}'.format(
                            self.username))],
                        [sg.T('Name', size=(4, 1)), sg.Input(
                                self.username, key='username_k', size=(32, 1))],
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
                        backup = self.username
                        username = self.username = v['username_k']
                        if username == '':
                            username = backup
                        self.update_user_config_file(username)
                        break
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
                                        sg.Popup(
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
                                    sg.Popup(
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
                                            sg.Popup(
                                                f'{new_engine_id_name} is existing. Please modify the name! \
                                                You can modify the config later thru Engine->Manage->Edit',
                                                title=button_title,
                                                icon=ico_path[platform]['pecg']
                                            )
                                            continue
                                        break
                                    else:
                                        sg.Popup(
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
                                sg.Popup(
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
                        option_layout, option_layout2 = [], []
                        button_title += '/' + e

                        try:
                            orig_idname = engine_id_name = v['engine_id_name_k'][0]
                        except Exception:
                            sg.Popup('Please select an engine to modify.',
                                     title='/Edit/Modify',
                                     icon=ico_path[platform]['pecg'])
                            continue

                        # Read engine config file
                        with open(self.engine_config_file, 'r') as json_file:
                            data = json.load(json_file)

                        # First option that can be set is the config name
                        option_layout.append(
                                [sg.Text('name', size=(4, 1)),
                                 sg.Input(engine_id_name, size=(38, 1),
                                          key='string_name_k')])
                        opt_name.append(['name', 'string_name_k'])

                        for p in data:
                            name = p['name']
                            path = p['workingDirectory']
                            file = p['command']
                            engine_path_file = Path(path, file)
                            option = p['options']

                            if name == engine_id_name:
                                num_opt = len(option)
                                opt_cnt = 0
                                for o in option:
                                    opt_cnt += 1
                                    name = o['name']
                                    value = o['value']
                                    type_ = o['type']

                                    if type_ == 'spin':
                                        min_ = o['min']
                                        max_ = o['max']

                                        key_name = type_ + '_' + name.lower() + '_k'
                                        opt_name.append([name, key_name])

                                        ttip = 'min {} max {}'.format(min_, max_)
                                        spin_layout = \
                                            [sg.Text(name, size=(16, 1)),
                                             sg.Input(value, size=(8, 1),
                                                      key=key_name,
                                                      tooltip=ttip)]
                                        if num_opt > 10 and opt_cnt > num_opt//2:
                                            option_layout2.append(spin_layout)
                                        else:
                                            option_layout.append(spin_layout)

                                    elif type_ == 'check':
                                        key_name = type_ + '_' + name.lower() + '_k'
                                        opt_name.append([name, key_name])

                                        check_layout = \
                                            [sg.Text(name, size=(16, 1)),
                                             sg.Checkbox('', key=key_name,
                                                         default=value)]
                                        if num_opt > 10 and opt_cnt > num_opt//2:
                                            option_layout2.append(check_layout)
                                        else:
                                            option_layout.append(check_layout)

                                    elif type_ == 'string':
                                        key_name = type_ + '_' + name + '_k'
                                        opt_name.append([name, key_name])

                                        # Use FolderBrowse()
                                        if 'syzygypath' in name.lower():
                                            sy_layout = \
                                                [sg.Text(name, size=(16, 1)),
                                                 sg.Input(value,
                                                          size=(12, 1),
                                                          key=key_name),
                                                 sg.FolderBrowse()]

                                            if num_opt > 10 and opt_cnt > num_opt//2:
                                                option_layout2.append(sy_layout)
                                            else:
                                                option_layout.append(sy_layout)

                                        # Use FileBrowse()
                                        elif 'weightsfile' in name.lower():
                                            weight_layout = \
                                                [sg.Text(name, size=(16, 1)),
                                                 sg.Input(value,
                                                          size=(12, 1),
                                                          key=key_name),
                                                 sg.FileBrowse()]

                                            if num_opt > 10 and opt_cnt > num_opt//2:
                                                option_layout2.append(
                                                    weight_layout)
                                            else:
                                                option_layout.append(
                                                    weight_layout)
                                        else:
                                            str_layout = \
                                                [sg.Text(name, size=(16, 1)),
                                                 sg.Input(value, size=(16, 1),
                                                          key=key_name)]

                                            if num_opt > 10 and opt_cnt > num_opt//2:
                                                option_layout2.append(
                                                    str_layout)
                                            else:
                                                option_layout.append(
                                                    str_layout)

                                    elif type_ == 'combo':
                                        key_name = type_ + '_' + name + '_k'
                                        opt_name.append([name, key_name])
                                        var = o['choices']
                                        combo_layout = [
                                            sg.Text(name, size=(16, 1)),
                                            sg.Combo(var, default_value=value,
                                                     size=(12, 1),
                                                     key=key_name)]
                                        if num_opt > 10 and opt_cnt > num_opt//2:
                                            option_layout2.append(combo_layout)
                                        else:
                                            option_layout.append(combo_layout)
                                break

                        option_layout.append([sg.OK(), sg.Cancel()])

                        if len(option_layout2) > 1:
                            tab1 = [[sg.Column(option_layout)]]
                            tab2 = [[sg.Column(option_layout2)]]
                            modify_layout = [[sg.Column(tab1), sg.Column(tab2)]]
                        else:
                            modify_layout = option_layout

                        edit_win.Hide()
                        modify_win = sg.Window(button_title,
                                               layout=modify_layout,
                                               icon=ico_path[platform]['pecg'])
                        is_cancel_modify_win = False
                        while True:
                            e1, v1 = modify_win.Read(timeout=100)
                            if e1 is None or e1 == 'Cancel':
                                is_cancel_modify_win = True
                                break
                            if e1 == 'OK':
                                engine_id_name = v1['string_name_k']
                                for o in opt_name:
                                    d = {o[0]: v1[o[1]]}
                                    ret_opt_name.append(d)
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
                            sg.Popup('Please select an engine to delete.',
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

            # Mode: Neutral, Allow user to change opponent engine settings
            if button == 'Set Engine Opponent':
                current_engine_file = self.opp_file
                current_engine_id_name = self.opp_id_name

                logging.info('Backup current engine list and file.')
                logging.info('Current engine file: {}'.format(
                    current_engine_file))

                layout = [
                        [sg.T('Current Opponent: {}'.format(self.opp_id_name), size=(40, 1))],
                        [sg.Listbox(values=self.engine_id_name_list, size=(48, 10), key='engine_id_k')],
                        [sg.OK(), sg.Cancel()]
                ]

                # Create new window and disable the main window
                w = sg.Window(BOX_TITLE + '/Select opponent', layout,
                              icon=ico_path[platform]['enemy'])
                window.Hide()

                while True:
                    e, v = w.Read(timeout=10)

                    if e is None or e == 'Cancel':
                        # Restore current engine list and file
                        logging.info('User cancels engine selection. ' +
                                     'We restore the current engine data.')
                        self.opp_file = current_engine_file
                        logging.info('Current engine data were restored.')
                        logging.info('current engine file: {}'.format(
                            self.opp_file))
                        break

                    if e == 'OK':
                        # We use try/except because user can press OK without
                        # selecting an engine
                        try:
                            engine_id_name = self.opp_id_name = v['engine_id_k'][0]
                            self.opp_file, self.opp_path_and_file = self.get_engine_file(
                                    engine_id_name)

                        except IndexError:
                            logging.info('User presses OK but did not select '
                                         'an engine.')
                        except Exception:
                            logging.exception('Failed to set engine.')
                        finally:
                            if current_engine_id_name != self.opp_id_name:
                                logging.info('User selected a new opponent {'
                                             '}.'.format(self.opp_id_name))
                        break

                window.UnHide()
                w.Close()

                # Update the player box in main window
                self.update_labels_and_game_tags(window, human=self.username)
                continue

            # Mode: Neutral, Set Adviser engine
            if button == 'Set Engine Adviser':
                current_adviser_engine_file = self.adviser_file
                current_adviser_path_and_file = self.adviser_path_and_file

                layout = [
                        [sg.T('Current Adviser: {}'.format(self.adviser_id_name),
                              size=(40, 1))],
                        [sg.Listbox(values=self.engine_id_name_list, size=(48, 10),
                                    key='adviser_id_name_k')],
                        [sg.T('Movetime (sec)', size=(12, 1)),
                         sg.Spin([t for t in range(1, 3600, 1)],
                                 initial_value=self.adviser_movetime_sec,
                                 size=(8, 1), key='adviser_movetime_k')],
                        [sg.OK(), sg.Cancel()]
                ]

                # Create new window and disable the main window
                w = sg.Window(BOX_TITLE + '/Select Adviser', layout,
                              icon=ico_path[platform]['adviser'])
                window.Hide()

                while True:
                    e, v = w.Read(timeout=10)

                    if e is None or e == 'Cancel':
                        self.adviser_file = current_adviser_engine_file
                        self.adviser_path_and_file = current_adviser_path_and_file
                        break

                    if e == 'OK':
                        movetime_sec = int(v['adviser_movetime_k'])
                        self.adviser_movetime_sec = min(3600, max(1, movetime_sec))

                        # We use try/except because user can press OK without selecting an engine
                        try:
                            adviser_eng_id_name = self.adviser_id_name = v['adviser_id_name_k'][0]
                            self.adviser_file, self.adviser_path_and_file = self.get_engine_file(
                                    adviser_eng_id_name)
                        except IndexError:
                            logging.info('User presses OK but did not select an engine')
                        except Exception:
                            logging.exception('Failed to set engine.')
                        break

                window.UnHide()
                w.Close()
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
            if button == 'GUI':
                sg.PopupScrolled(HELP_MSG, title='Help/GUI')
                continue

            # Mode: Neutral
            if button == 'Play':
                if engine_id_name is None:
                    logging.warning('Install engine first!')
                    sg.Popup('Install engine first! in Engine/Manage/Install',
                             icon=ico_path[platform]['pecg'], title='Mode')
                    continue

                # Change menu from Neutral to Play
                self.menu_elem.Update(menu_def_play)
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
                self.psg_board = copy.deepcopy(initial_board)
                board = chess.Board()
                self.set_new_game()
                continue

        window.Close()


def main():
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
