""" 
python_easy_chess_gui.py

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

import PySimpleGUI as sg
import os
import sys
import threading
import queue
import copy
import time
from datetime import datetime
import pyperclip
import chess
import chess.pgn
import chess.engine
import logging


logging.basicConfig(filename='pecg.log', filemode='w', level=logging.DEBUG,
                    format='%(asctime)s :: %(levelname)s :: %(message)s')


APP_NAME = 'Python Easy Chess GUI'
APP_VERSION = 'v0.28'
BOX_TITLE = APP_NAME + ' ' + APP_VERSION


MIN_TIME = 0.5  # sec
MAX_TIME = 300.0  # sec
MIN_DEPTH = 1
MAX_DEPTH = 128


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


# Absolute rank based on real chess board, white at the bottom, black at the top.
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


# Move color
DARK_SQ_MOVE_COLOR = '#B8AF4E'
LIGHT_SQ_MOVE_COLOR = '#E8E18E'


FLIP_MSG = """Flipping a board while status is Play mode is not possible at the moment.
If you really want to flip the board and start the game from startpos do the following:
1. Game->Exit Game
2. Board->Flip
3. Game->New Game
"""


HELP_MSG = """
// To play a game
You should be in Play mode.
1. Mode->Play
2. Make move on the board
If you are already in Play mode, Game->New Game

// To play as black
You should be in Neutral mode
1. Board->Flip
2. Mode->Play
3. Engine->Go
If you are already in Play mode, Mode->Neutral

// To flip board
You should be in Neutral mode
1. Board->Flip
  
// To paste FEN
You should be in Play mode
1. Mode->Play
2. FEN->Paste
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


images = {BISHOPB: bishopB, BISHOPW: bishopW, PAWNB: pawnB, PAWNW: pawnW,
          KNIGHTB: knightB, KNIGHTW: knightW,
          ROOKB: rookB, ROOKW: rookW, KINGB: kingB, KINGW: kingW,
          QUEENB: queenB, QUEENW: queenW, BLANK: blank}


# Promote piece from psg (pysimplegui) to pyc (python-chess)
promote_psg_to_pyc = {KNIGHTB: chess.KNIGHT, BISHOPB: chess.BISHOP,
                      ROOKB: chess.ROOK, QUEENB: chess.QUEEN,
                      KNIGHTW: chess.KNIGHT, BISHOPW: chess.BISHOP,
                      ROOKW: chess.ROOK, QUEENW: chess.QUEEN,}


def get_time_mm_ss_ms(time_ms):
    """ Returns time in min:sec:millisec given time in millisec """
    s, ms = divmod(int(time_ms), 1000)
    m, s = divmod(s, 60)
    
    return '{:02d}:{:02d}:{:03d}'.format(m, s, ms)


class RunEngine(threading.Thread):
    pv_length = 5
    move_delay_sec = 3.0
    
    def __init__(self, eng_queue, engine_path, max_depth=1, max_time=1, threads=1):
        threading.Thread.__init__(self)
        self.engine_path = engine_path
        self.threads = threads
        self.bm = None
        self.pv = None
        self.score = None
        self.depth = None
        self.time = None
        self.max_depth = max_depth
        self.max_time = max_time  # sec
        self.eng_queue = eng_queue
        self.engine = None
        self.board = None
        
    def get_board(self, board):
        """ Get board from user """
        self.board = board

    def run(self):
        # When converting .py to exe using pyinstaller use the following
        # self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path,
        #         creationflags=subprocess.CREATE_NO_WINDOW) 
        # This is only applicable for Python version >= 3.7
        
        self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        try:
            self.engine.configure({'Threads': self.threads})
        except:
            pass
        
        # Use wall clock time to determine max time
        start_thinking_time = time.time()
        is_time_check = False
        
        with self.engine.analysis(self.board) as analysis:
            for info in analysis:
                try:
                    if 'depth' in info:
                        self.depth = int(info['depth'])
                        self.eng_queue.put('{} depth'.format(self.depth))
                        
                    if 'score' in info:
                        self.score = int(info['score'].relative.score(mate_score=32000))/100
                        self.eng_queue.put('{:+0.2f} score'.format(self.score))
                        
                    self.time = time.time() - start_thinking_time
                    self.eng_queue.put('{} time'.format(self.time))
                        
                    if 'pv' in info:
                        self.pv = info['pv'][0:self.pv_length]
                        self.pv = self.board.variation_san(self.pv)
                        self.eng_queue.put('{} pv'.format(self.pv))
                        self.bm = info['pv'][0]
                        
                    if 'nps' in info:
                        info_line = info['nps']
                        self.eng_queue.put('{} nps'.format(info_line))                                          
                        
                    if 'nodes' in info:
                        info_line = 'Positions searched {}\n'.format(info['nodes'])
                        self.eng_queue.put(info_line)
                        
                    # If we use "go infinite" we stop the search by time and depth
                    if not is_time_check and \
                        time.time() - start_thinking_time >= self.max_time:
                        logging.info('Max time limit is reached.')
                        is_time_check = True
                        break
                        
                    if 'depth' in info:
                        if int(info['depth']) >= self.max_depth:
                            logging.info('Max depth limit is reached.')
                            break
                except:
                    raise
                
                time.sleep(0.1)
                
        # Apply engine move delay
        while True:
            if time.time() - start_thinking_time >= self.move_delay_sec:
                break
            logging.info('Delay sending of best move')
            time.sleep(0.25)

        self.eng_queue.put('bestmove {}' .format(self.bm))
        logging.info('bestmove {}'.format(self.bm))
        
    def quit_engine(self):
        """ Quit engine """
        self.engine.quit()
        logging.info('quit engine')


class EasyChessGui():
    queue = queue.Queue()
    is_user_white = True  # White is at the bottom in board layout

    def __init__(self, max_depth, max_time_sec, threads):
        self.max_depth = max_depth
        self.max_time = max_time_sec
        self.threads = threads
        self.engine_full_path_and_name = None    
        self.white_layout = None
        self.black_layout = None
        self.white_layout_play = None
        self.black_layout_play = None
        self.window = None
        self.pecg_game_fn = 'pecg_game.pgn'
        self.pgn_tag = {
                'Event': 'Human vs computer',
                'Date': datetime.today().strftime('%Y.%m.%d'),
                'White': 'Human',
                'Black': 'Computer',
        }
        self.fen = None
        self.psg_board = None
        
    def update_white_black_labels(self, human='Human', engine_id='engine id name'):
        """ Update player names """
        if self.is_user_white:
            self.window.FindElement('_White_').Update(human)
            self.window.FindElement('_Black_').Update(engine_id)
            self.pgn_tag['White'] = human
            self.pgn_tag['Black'] = engine_id
        else:
            self.window.FindElement('_White_').Update(engine_id)
            self.window.FindElement('_Black_').Update(human)
            self.pgn_tag['White'] = engine_id
            self.pgn_tag['Black'] = human
        
    def get_fen(self):
        """ Get fen from clipboard """
        self.fen = pyperclip.paste()
        
        # Remove empty char at the end of FEN
        if self.fen.endswith(' '):
            self.fen = self.fen[:-1]

    def fen_to_psg_board(self):
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
                pc = board.piece_at(s^56)
            except:
                pc = None
            
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
        
    def change_square_color(self, row, col):
        """ 
        Change the color of a square based on square row and col.
        """
        btn_sq = self.window.FindElement(key=(row, col))
        is_dark_square = True if (row + col) % 2 else False
        bd_sq_color = DARK_SQ_MOVE_COLOR if is_dark_square else LIGHT_SQ_MOVE_COLOR
        btn_sq.Update(button_color=('white', bd_sq_color))

    def relative_row(self, s, stm):
        """ 
        s:
            square
        stm:
            side to move
        Return:
            row
        
        Note:
            The board can be viewed, as white at the bottom and black at the
            top. If stm is white the row 0 is at the bottom. If stm is black
            row 0 is at the top.
        """
        return 7 - self.get_row(s) if stm else self.get_row(s)
    
    def get_row(self, s):
        """ 
        s:
            square
        Return:
            row
        
        Note:
            This row is based on PySimpleGUI square mapping that is 0 at the
            top and 7 at the bottom. 
            In contrast Python-chess square mapping is 0 at the bottom and 7
            at the top. chess.square_rank() is a method from Python-chess that
            returns row given square s.
        """
        return 7 - chess.square_rank(s)    
    
    def get_col(self, s):
        """ Returns col given square s """
        return chess.square_file(s)
        
    def redraw_board(self):
        """ Redraw the chess board at the begining of the game or after a move """
        for i in range(8):
            for j in range(8):
                color = '#B58863' if (i + j) % 2 else '#F0D9B5'
                piece_image = images[self.psg_board[i][j]]
                elem = self.window.FindElement(key=(i, j))
                elem.Update(button_color=('white', color),
                            image_filename=piece_image, )
        
    def render_square(self, image, key, location):
        """ Returns an RButton (Read Button) with image image """
        if (location[0] + location[1]) % 2:
            color = '#B58863'
        else:
            color = '#F0D9B5'
        return sg.RButton('', image_filename=image, size=(1, 1), 
                          button_color=('white', color), pad=(0, 0), key=key)
        
    def select_promotion_piece(self, stm):
        """ 
        Returns the promoted piece [KNIGHTW, KNIGHTB, ... QUEENW]
        stm:
            side to move
        """
        piece = None
        board_layout, row = [], []
        
        psg_promote_board = copy.deepcopy(white_init_promote_board) if stm \
                else copy.deepcopy(black_init_promote_board)

        # Loop through board and create buttons with images        
        for i in range(1):            
            for j in range(4):
                piece_image = images[psg_promote_board[i][j]]
                row.append(self.render_square(piece_image, key=(i, j), location=(i, j)))
    
            board_layout.append(row)
    
        promo_window = sg.Window('{} {}'.format(APP_NAME, APP_VERSION), board_layout,
                           default_button_element_size=(12, 1),
                           auto_size_buttons=False,
                           icon='')
        
        while True:
            button, value = promo_window.Read(timeout=0)
            if button is None:
                break
            if type(button) is tuple:
                move_from = button
                fr_row, fr_col = move_from
                piece = psg_promote_board[fr_row][fr_col]
                logging.info('promote piece: {}'.format(piece))
                break
            
        promo_window.Close()
        
        return piece
        
    def update_rook(self, move):
        """ 
        Update rook location on the board for a castle move.
        move:
            a move in uci move format
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
        self.redraw_board()        
    
    def update_ep(self, move, stm):
        """ 
        Update board if move is an ep capture. Remove the piece at 
        to-8 (stm is white) or to+8 (stm is black)
        move:
            is the ep move in python-chess format
        stm:
            is side to move        
        """
        to = move.to_square
        if stm:
            capture_sq = to - 8
        else:
            capture_sq = to + 8
    
        self.psg_board[self.get_row(capture_sq)][self.get_col(capture_sq)] = BLANK
        self.redraw_board()        
        
    def get_promo_piece(self, move, stm, human):
        """ 
        Returns:
            promotion piece based on python-chess module (pyc_promo) and
            based on PySimpleGUI (psg_promo)
        move:
            The promote move in python-chess format
        stm:
            The side to move
        human:
            This is true if the promotion move is from the user otherwise thi is False
            which is the move from the computer engine.
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
    
    def modify_depth_limit(self):
        """ Returns max depth based from user setting """
        user_depth = sg.PopupGetText('Current depth is {}\n\nInput depth [{} to {}]'.format(
                self.max_depth, MIN_DEPTH, MAX_DEPTH), title=BOX_TITLE)
        
        try:
            user_depth = int(user_depth)
        except:
            user_depth = self.max_depth

        self.max_depth = min(MAX_DEPTH, max(MIN_DEPTH, user_depth))
    
    def modify_time_limit(self):
        """ Update max time based on user input """
        user_movetime = sg.PopupGetText(
            'Current move time is {} sec\n\nInput move time [{} to {}] sec'.format(
            self.max_time, MIN_TIME, MAX_TIME), title=BOX_TITLE)
        
        try:
            user_movetime = int(user_movetime)
        except:
            user_movetime = self.max_time

        self.max_time = min(MAX_TIME, max(MIN_TIME, user_movetime))

    def get_engine_settings(self, engine_id_name):
        """ Display engine settings """
        sg.PopupOK('Depth = {}\nMovetime = {} sec\n\nEngine = {}\n'.format(self.max_depth,
                   self.max_time, engine_id_name), title=BOX_TITLE, keep_on_top=True)

    def play_game(self, engine_id_name, board):
        """ 
        Plays a game against an engine. Move legality is handled by python-chess.
        """ 
        self.window.FindElement('_movelist_').Update('')
        self.window.FindElement('_engineinfo_').Update('')
                
        is_human_stm = True if self.is_user_white else False
        
        move_state = 0
        move_from, move_to = None, None
        is_new_game, is_exit_game, is_exit_app = False, False, False
        
        # Do not play immediately when stm is computer
        is_engine_ready = True if is_human_stm else False
        
        # For saving game
        move_cnt = 0
        game = chess.pgn.Game()
        game.headers['Event'] = self.pgn_tag['Event']
        game.headers['Date'] = datetime.today().strftime('%Y.%m.%d')
        game.headers['White'] = self.pgn_tag['White']
        game.headers['Black'] = self.pgn_tag['Black']
        
        # Game loop
        while not board.is_game_over(claim_draw=True):
            moved_piece = None
            
            # If engine is to play first, allow the user to configure the engine
            # and exit this loop when user presses the Engine->Go button
            if not is_engine_ready:
                self.window.FindElement('_gamestatus_').Update('Mode: Play, press Engine->Go')
                while True:
                    button, value = self.window.Read(timeout=100)
                    
                    if button in (None, 'Exit'):
                        is_exit_app = True
                        break
                    
                    if button in (None, 'New Game'):
                        is_new_game = True
                        break
                    
                    if button in (None, 'Neutral'):
                        is_exit_game = True
                        break
                    
                    if button in (None, 'Flip'):
                        sg.PopupScrolled(FLIP_MSG, size=(80, 5),
                                         non_blocking=True, title = BOX_TITLE)
                        continue
                    
                    if button in (None, 'Set Depth'):
                        self.modify_depth_limit()
                    
                    if button in (None, 'Set Movetime'):
                        self.modify_time_limit()
                    
                    if button in (None, 'Get Settings'):
                        self.get_engine_settings(engine_id_name)
                        
                    if button in (None, 'About'):
                        sg.Popup(HELP_MSG, title=BOX_TITLE)
                        
                    if button in (None, 'Paste'):
                        try:
                            self.get_fen()                    
                            board = chess.Board(self.fen)
                        except:
                            logging.info('Error in parsing FEN from clipboard.')
                            continue
                            
                        self.fen_to_psg_board()
                        self.redraw_board()
                        
                        # If user is black and side to move based from pasted FEN is black
                        if not self.is_user_white and not board.turn:
                            is_human_stm = True
                            self.window.FindElement('_gamestatus_').Update('Mode: Play')

                        # Elif user is black and side to move based from pasted FEN is white
                        elif not self.is_user_white and board.turn:
                            is_human_stm = False
                            self.window.FindElement('_gamestatus_').Update('Mode: Play, press Engine->Go')

                        is_engine_ready = True if is_human_stm else False
                        
                        game.headers['FEN'] = self.fen
                        break
                    
                    if button in (None, 'Go'):
                        is_engine_ready = True
                        break
                    
                if is_exit_app or is_exit_game or is_new_game:
                    break
    
            # If side to move is human
            if is_human_stm:
                move_state = 0
                while True:
                    button, value = self.window.Read(timeout=100)
                    
                    if not is_human_stm:
                        break
                    
                    if button in (None, 'Exit'):
                        logging.info('Exit app')
                        is_exit_app = True
                        break
                    
                    if button in (None, 'New Game'):
                        is_new_game = True
                        break
                    
                    if button in (None, 'Save Game'):
                        logging.info('Saving game manually')
                        with open(self.pecg_game_fn, mode = 'a+') as f:
                            f.write('{}\n\n'.format(game))                        
                        break                    

                    if button in (None, 'Neutral'):
                        is_exit_game = True
                        break
                    
                    if button in (None, 'About'):
                        sg.Popup(HELP_MSG, title=BOX_TITLE)
                        break
                    
                    if button in (None, 'Flip'):
                        sg.PopupScrolled(FLIP_MSG, size=(80, 5),
                                         non_blocking=True, title = BOX_TITLE)
                        continue
                    
                    if button in (None, 'Go'):
                        if is_human_stm:
                            is_human_stm = False
                        else:
                            is_human_stm = True
                        is_engine_ready = True
                        self.window.FindElement('_gamestatus_').Update('Mode: Play, Engine is thinking ...')
                        break
                    
                    if button in (None, 'Get Settings'):
                        self.get_engine_settings(engine_id_name)
                        break
                    
                    if button in (None, 'Set Depth'):
                        self.modify_depth_limit()
                        break
                    
                    if button in (None, 'Set Movetime'):
                        self.modify_time_limit()
                        break
                    
                    if button in (None, 'Paste'):
                        try:
                            self.get_fen()                    
                            board = chess.Board(self.fen)
                        except:
                            logging.info('Error in parsing FEN from clipboard.')
                            continue
                            
                        self.fen_to_psg_board()
                        self.redraw_board()
                        
                        is_human_stm = True if board.turn else False
                        is_engine_ready = True if is_human_stm else False
                        
                        self.window.FindElement('_gamestatus_').Update(
                                'Mode: Play, side: {}'.format('white' if board.turn else 'black'))
                        
                        game.headers['FEN'] = self.fen
                        break
                    
                    if type(button) is tuple:
                        # If fr_sq button is pressed
                        if move_state == 0:
                            move_from = button
                            fr_row, fr_col = move_from
                            piece = self.psg_board[fr_row][fr_col]  # get the move-from piece
                            
                            # Change the color of the "fr" board square
                            self.change_square_color(fr_row, fr_col)
                            
                            move_state = 1
                            moved_piece = board.piece_type_at(chess.square(fr_col, 7-fr_row))  # Pawn=1
                        
                        # Else if to_sq button is pressed
                        elif move_state == 1:
                            is_promote = False
                            move_to = button
                            to_row, to_col = move_to
                            button_square = self.window.FindElement(key=(fr_row, fr_col))
                            
                            # If move is cancelled, pressing same button twice
                            if move_to == move_from:
                                # Restore the color of the pressed board square
                                color = '#B58863' if (to_row + to_col) % 2 else '#F0D9B5'
                                
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
                                pyc_promo, psg_promo = self.get_promo_piece(user_move, board.turn, True)
                                user_move = chess.Move(fr_sq, to_sq, promotion=pyc_promo)
                            else:
                                user_move = chess.Move(fr_sq, to_sq)
                            
                            # Check if user move is legal
                            if user_move in board.legal_moves:
                                # Convert user move to san move for display in movelist
                                san_move = board.san(user_move)
                                fmvn = board.fullmove_number
                                if board.turn:
                                    show_san_move = '{}. {} '.format(fmvn, san_move)                              
                                else:
                                    show_san_move = '{} '.format(san_move)                                
                                    
                                # Update rook location if this is a castle move
                                if board.is_castling(user_move):
                                    self.update_rook(str(user_move))
                                    
                                # Update board if e.p capture
                                elif board.is_en_passant(user_move):
                                    self.update_ep(user_move, board.turn)                                
                                    
                                # Empty the board from_square, applied to any types of move
                                self.psg_board[move_from[0]][move_from[1]] = BLANK
                                
                                # Update board to_square if move is a promotion
                                if is_promote:
                                    self.psg_board[to_row][to_col] = psg_promo
                                # Update the to_square if not a promote move
                                else:
                                    # Place piece in the move to_square
                                    self.psg_board[to_row][to_col] = piece
                                    
                                self.redraw_board()
                                self.window.FindElement('_movelist_').Update(show_san_move, append=True)
    
                                board.push(user_move)
                                move_cnt += 1
                                
                                if move_cnt == 1:
                                    node = game.add_variation(user_move)
                                else:
                                    node = node.add_variation(user_move)
                                
                                # Change the color of the "fr" and "to" board squares
                                self.change_square_color(fr_row, fr_col)
                                self.change_square_color(to_row, to_col)
    
                                is_human_stm ^= 1
                                
                                self.window.FindElement('_engineinfo_').Update('', append=False)
                                
                                # Human has done its move
                         
                            # Else if move is illegal
                            else:
                                move_state = 0
                                color = '#B58863' if (move_from[0] + move_from[1]) % 2 else '#F0D9B5'
                                
                                # Restore the color of the fr square
                                button_square.Update(button_color=('white', color))
                                continue
                    
                if is_new_game or is_exit_game or is_exit_app:
                    break

            # Else if side to move is not human
            elif not is_human_stm and is_engine_ready:             
                is_promote = False
                search = RunEngine(self.queue, self.engine_full_path_and_name,
                                   self.max_depth, self.max_time, self.threads)
                search.get_board(board)
                search.start() 
                self.window.FindElement('_gamestatus_').Update('Mode: Play, Engine is thinking ...')
                while True:
                    button, value = self.window.Read(timeout=200)
                    msg = self.queue.get()
                    msg_str = str(msg)
                    if not 'bestmove ' in msg_str:                        
                        if 'score' in msg_str:
                            score = float(' '.join(msg_str.split()[0:-1]).strip())
                            msg_line = '{:+0.2f}\n'.format(score)

                            # If score is good change color to green, if bad it is red
                            tcolor = 'green'
                            if score < 0.0:
                                tcolor = 'red'
                            elif score == 0.0:
                                tcolor = 'black'

                            self.window.FindElement('info_score_k').Update(msg_line, text_color=tcolor)
                            
                        if 'pv' in msg_str:
                            pv = ' '.join(msg_str.split()[0:-1]).strip()
                            msg_line = '{}\n'.format(pv)
                            self.window.FindElement('info_pv_k').Update(msg_line)

                        if 'depth' in msg_str:
                            depth = int(' '.join(msg_str.split()[0:-1]).strip())
                            msg_line = 'Depth: {}\n'.format(depth)
                            self.window.FindElement('info_depth_k').Update(msg_line)

                        if 'time' in msg_str:
                            tsec = float(' '.join(msg_str.split()[0:-1]).strip())
                            msg_line = 'Time: {}\n'.format(get_time_mm_ss_ms(tsec*1000))
                            self.window.FindElement('info_time_k').Update(msg_line)
                            
                        if 'nps' in msg_str:
                            nps = int(' '.join(msg_str.split()[0:-1]).strip())
                            
                            # Add suffix K if nps is 1 Million or more
                            if nps >= 1000000:
                                msg_line = 'Nps: {:0.0f}K\n'.format(nps/1000)
                            else:
                                msg_line = 'Nps: {}\n'.format(nps)

                            self.window.FindElement('info_nps_k').Update(msg_line)
                    else:
                        best_move = chess.Move.from_uci(msg.split()[1])
                        break
                search.join()
                search.quit_engine()

                move_str = str(best_move)
                fr_col = ord(move_str[0]) - ord('a')
                fr_row = 8 - int(move_str[1])
                to_col = ord(move_str[2]) - ord('a')
                to_row = 8 - int(move_str[3])
                
                # Convert user move to san move for display in movelist
                san_move = board.san(best_move)
                fmvn = board.fullmove_number
                if board.turn:
                    show_san_move = '{}. {} '.format(fmvn, san_move)
                else:
                    show_san_move = '{} '.format(san_move)
                self.window.FindElement('_movelist_').Update(show_san_move, append=True)
    
                piece = self.psg_board[fr_row][fr_col]
                self.psg_board[fr_row][fr_col] = BLANK            
                
                # Update rook location if this is a castle move
                if board.is_castling(best_move):
                    self.update_rook(move_str)
                    
                # Update board if e.p capture
                elif board.is_en_passant(best_move):
                    self.update_ep(best_move, board.turn)
                    
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
                    
                self.redraw_board()
    
                board.push(best_move)                
                move_cnt += 1
                                
                if move_cnt == 1:
                    node = game.add_variation(best_move)
                else:
                    node = node.add_variation(best_move)
                
                # Change the color of the "fr" and "to" board squares
                self.change_square_color(fr_row, fr_col)
                self.change_square_color(to_row, to_col)
                
                is_human_stm ^= 1
                
                self.window.FindElement('_gamestatus_').Update('Mode: Play')                
                # Engine has done its move
            
        # Auto-save game
        logging.info('Saving game automatically')
        game.headers['Result'] = board.result(claim_draw = True)          
        with open(self.pecg_game_fn, mode = 'a+') as f:
            f.write('{}\n\n'.format(game)) 
            
        if is_exit_app:
            sys.exit(0)
            
        # Exit game over loop        
        if is_exit_game:
            # Build another board
            return False
        
        if not is_new_game:
            result = board.result(claim_draw=True)
            sg.Popup('Game over!\n\nResult is {}\nThank you for playing'.format(result), title=BOX_TITLE)
        
        return is_new_game

    def get_engine_id_name(self, enginefn):
        """ Start engine """
        eng_filename = './Engines/' + enginefn
        self.engine_full_path_and_name = eng_filename
        if eng_filename is None:
            logging.info('Failed to load engine')
            sys.exit(0)
        engine = chess.engine.SimpleEngine.popen_uci(eng_filename)
        engine_id_name = engine.id['name']
        engine.quit()
        
        return engine_id_name
    
    def get_engines(self):
        """ Returns a list of engines located in Engines dir """
        engine_list = []
        engine_path = './Engines/'
        files = os.listdir(engine_path)
        for file in files:
            if not file.endswith('.gz') and not file.endswith('.dll'):
                engine_list.append(file)

        return engine_list
        
    def init_user_option(self):
        """ Allows user to select engine opponent.
            Returns engine filename selected.
        """
        engine_list = self.get_engines()
        
        layout = [
            [sg.Text('Engine opponent', size=(16, 1), font=('Consolas', 10)), 
             sg.Drop(engine_list, size=(34, 1), font=('Consolas', 10), key='_enginefn_')],
            [sg.Button('OK', size=(6, 1), font=('Consolas', 10), key='_ok_')],
        ]
        
        init_window = sg.Window('{} {}'.format(APP_NAME, APP_VERSION), layout,
                           default_button_element_size=(12, 1),
                           auto_size_buttons=False,
                           icon='')
    
        enginefn = None
        while True:        
            button, value = init_window.Read(timeout=0) 
            
            if button is None:
                logging.info('User pressed x')
                sys.exit(0)
            
            enginefn = value['_enginefn_']

            if button == '_ok_':
                break
        
        init_window.Close()
        
        return enginefn

    def create_board(self):
        """
        Returns board layouts both white and black point of view.
        """
        white_board_layout, black_board_layout = [], []
        
        # Save the board with black at the top        
        start = 0
        end = 8
        step = 1
        file_char_name = 'abcdefgh'
        
        if not self.is_user_white:
            start = 7
            end = -1
            step = -1
            file_char_name = file_char_name[::-1]
        
        # Loop through the board and create buttons with images
        for i in range(start, end, step):
            # Row numbers at left of board
            row = [sg.T(str(8 - i) + '  ', font='Any 11')]
            
            for j in range(start, end, step):
                piece_image = images[self.psg_board[i][j]]
                row.append(self.render_square(piece_image, key=(i, j), location=(i, j)))
    
            white_board_layout.append(row)
            
        # add the labels across bottom of board
        white_board_layout.append([sg.T('     ')] + [sg.T('{}'.format(a), pad=((23, 27), 0),
                            font='Any 11') for a in file_char_name])
        
        # Save the board with white at the top
        file_char_name = 'abcdefgh'
        
        start = 7
        end = -1
        step = -1
        file_char_name = file_char_name[::-1]

        if not self.is_user_white:
            start = 0
            end = 8
            step = 1
            file_char_name = file_char_name[::-1]
            
        # Loop through the board and create buttons with images
        for i in range(start, end, step):
            # Row numbers at left of board
            row = [sg.T(str(8 - i) + '  ', font='Any 11')]
            
            for j in range(start, end, step):
                piece_image = images[self.psg_board[i][j]]
                row.append(self.render_square(piece_image, key=(i, j), location=(i, j)))
    
            black_board_layout.append(row)
            
        # add the labels across bottom of board
        black_board_layout.append([sg.T('     ')] + [sg.T('{}'.format(a), pad=((23, 27), 0),
                            font='Any 11') for a in file_char_name])
            
        return white_board_layout, black_board_layout
        
    def build_main_layout(self):
        """
        Build the main part of GUI, board is oriented with white at the bottom.
        """

        # (1) Main menu, mode: Neutral
        menu_def = [['&File', ['!Save Game', 'E&xit']],
                    ['&Mode', ['!Neutral', 'Play', '!Analysis']],
                    ['!&Game', ['&New Game',]],
                    ['&Board', ['Flip']],
                    ['!FEN', ['Paste']],
                    ['&Engine', ['Go', 'Set Depth', 'Set Movetime', 'Get Settings']],
                    ['&Help', ['About']],
                    ]
        
        # (2) Play menu, mode: Play
        menu_def_play = [
                ['&File', ['Save Game', 'E&xit']],
                ['&Mode', ['Neutral', '!Play', '!Analysis']],
                ['&Game', ['&New Game',]],
                ['!&Board', ['Flip']],
                ['FEN', ['Paste']],
                ['&Engine', ['Go', 'Set Depth', 'Set Movetime', 'Get Settings']],
                ['&Help', ['About']],
        ]
        
        sg.ChangeLookAndFeel('Reddit')
        self.psg_board = copy.deepcopy(initial_board)
        
        # Define board
        white_board_layout, black_board_layout = self.create_board()
        bc = '#d3dae4'
    
        board_controls = [
            [sg.Text('Mode: Neutral', size=(36, 1), font=('Consolas', 10), key='_gamestatus_')],
            [sg.Text('White', size=(5, 1), font=('Consolas', 10)), sg.InputText('',
                    font=('Consolas', 10), key='_White_', size=(35, 1))],
            [sg.Text('Black', size=(5, 1), font=('Consolas', 10)), sg.InputText('',
                    font=('Consolas', 10), key='_Black_', size=(35, 1))],
            [sg.Text('MOVE LIST', font=('Consolas', 10))],            
            [sg.Multiline([], do_not_clear=True, autoscroll=True, size=(40, 8),
                    font=('Consolas', 10), key='_movelist_')],

            [sg.Text('ENGINE SEARCH INFO', font=('Consolas', 10))],
            [sg.Text('', key='info_score_k', size=(8, 1), background_color = bc),
             sg.Text('', key='info_pv_k', size=(27, 1), background_color = bc)],
             
            [sg.Text('', key='info_depth_k', size=(8, 1), background_color = bc),
             sg.Text('', key='info_time_k', size=(12, 1), background_color = bc),
             sg.Text('', key='info_nps_k', size=(13, 1), background_color = bc)],
              
            [sg.Multiline([], do_not_clear=True, autoscroll=True, size=(40, 10),
                    font=('Consolas', 10), key='_engineinfo_', visible = False)],            
        ]
    
        white_board_tab = [[sg.Column(white_board_layout)]]
        black_board_tab = [[sg.Column(black_board_layout)]]
    
        # White board layout, mode: Neutral
        white_layout = [[sg.Menu(menu_def, tearoff=False)],
                  [sg.TabGroup([[sg.Tab('Board', white_board_tab)]], title_color='red'),
                   sg.Column(board_controls)],
                  ]
                  
        # Black board layout, mode: Neutral
        black_layout = [[sg.Menu(menu_def, tearoff=False)],
                  [sg.TabGroup([[sg.Tab('Board', black_board_tab)]], title_color='red'),
                   sg.Column(board_controls)],
                  ]
                  
        # White board layout, mode: Play
        white_layout_play = [[sg.Menu(menu_def_play, tearoff=False)],
                  [sg.TabGroup([[sg.Tab('Board', white_board_tab)]], title_color='red'),
                   sg.Column(board_controls)],
                  ]
                  
        # Black board layout, mode: Play
        black_layout_play = [[sg.Menu(menu_def_play, tearoff=False)],
                  [sg.TabGroup([[sg.Tab('Board', black_board_tab)]], title_color='red'),
                   sg.Column(board_controls)],
                  ]
                  
        # Use white layout as default window    
        self.window = sg.Window('{} {}'.format(APP_NAME, APP_VERSION), white_layout,
                           default_button_element_size=(12, 1),
                           auto_size_buttons=False,
                           icon='')
        
        self.white_layout = white_layout
        self.black_layout = black_layout
        
        self.white_layout_play = white_layout_play
        self.black_layout_play = black_layout_play
    
    def build_gui(self):
        """ 
        Builds the main GUI, this includes board orientation and engine selection.
        """
        enginefn = self.init_user_option()
    
        self.build_main_layout()
        
        # Start engine and get its id name
        engine_id_name = self.get_engine_id_name(enginefn)

        self.update_white_black_labels(human='Human', engine_id=engine_id_name)
            
        return engine_id_name
    
    def main_loop(self):
        """ 
        This is where we build our GUI and read user inputs.
        """
        engine_id_name = self.build_gui()
        
        while True:
            button, value = self.window.Read(timeout=100)
            
            # Menu->File->Exit
            if button in (None, 'Exit'):
                break
            
            # Engine settings
            if button in (None, 'Set Depth'):
                self.modify_depth_limit()
                continue
            
            if button in (None, 'Set Movetime'):
                self.modify_time_limit()
                continue
            
            if button in (None, 'Get Settings'):
                self.get_engine_settings(engine_id_name)
                continue
                
            if button in (None, 'Flip'):
                # Clear Text and Multiline elements
                self.window.FindElement('_gamestatus_').Update('Mode: Neutral')
                self.window.FindElement('_movelist_').Update('')
#                self.window.FindElement('_engineinfosummary_').Update('')
                self.window.FindElement('_engineinfo_').Update('')                
                
                window1 = sg.Window('{} {}'.format(APP_NAME, APP_VERSION),
                    self.black_layout if self.is_user_white else self.white_layout,
                    default_button_element_size=(12, 1),
                    auto_size_buttons=False,
                    icon='')
                self.is_user_white = not self.is_user_white
                
                self.update_white_black_labels(human='Human', engine_id=engine_id_name)
                
                self.window.Close()
                self.psg_board = copy.deepcopy(initial_board)
                board = chess.Board()
                self.window = window1
                continue
            
            # Menu->Help->Help
            if button in (None, 'About'):
                sg.Popup(HELP_MSG, title=BOX_TITLE)
                continue
            
            if button in (None, 'Play'):
                window1 = sg.Window('{} {}'.format(APP_NAME, APP_VERSION),
                    self.white_layout_play if self.is_user_white else self.black_layout_play,
                    default_button_element_size=(12, 1),
                    auto_size_buttons=False,
                    icon='')
                
                self.window.Close()
                self.psg_board = copy.deepcopy(initial_board)
                board = chess.Board()
                self.window = window1
                
                while True:
                    button, value = self.window.Read(timeout=100)
                    
                    self.window.FindElement('_gamestatus_').Update('Mode: Play')
                    self.window.FindElement('_movelist_').Update('')
                    
                    start_new_game = self.play_game(engine_id_name, board)
                    self.window.FindElement('_gamestatus_').Update('Mode: Neutral')
                    
                    self.psg_board = copy.deepcopy(initial_board)
                    self.redraw_board()
                    board = chess.Board()
                    
                    if not start_new_game:
                        break
                    
                window1 = sg.Window('{} {}'.format(APP_NAME, APP_VERSION),
                    self.white_layout if self.is_user_white else self.black_layout,
                    default_button_element_size=(12, 1),
                    auto_size_buttons=False,
                    icon='')
                
                # Restore main layout
                self.window.Close()
                self.psg_board = copy.deepcopy(initial_board)
                board = chess.Board()
                self.window = window1
                continue
            
        self.window.Close()


def main():
    max_depth = 128
    max_time_sec = 5.0
    threads = 1
    pecg = EasyChessGui(max_depth, max_time_sec, threads)
    pecg.main_loop()


if __name__ == "__main__":
    main()
