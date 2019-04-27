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
import time
import chess
import chess.pgn
import copy
import chess.engine


APP_NAME = 'Python Easy Chess GUI'
APP_VERSION = 'v0.3.2'
BOX_TITLE = APP_NAME + ' ' + APP_VERSION


MIN_TIME = 0.5  # sec
MAX_TIME = 60


CHESS_PATH = 'Images/60'  # path to the chess pieces


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


# Move color
DARK_SQ_MOVE_COLOR = '#e9db89'
LIGHT_SQ_MOVE_COLOR = '#f9f086'


# Images/60
blank = os.path.join(CHESS_PATH, 'blank.png')
bishopB = os.path.join(CHESS_PATH, 'bB.png')
bishopW = os.path.join(CHESS_PATH, 'wB.png')
pawnB = os.path.join(CHESS_PATH, 'bP.png')
pawnW = os.path.join(CHESS_PATH, 'wP.png')
knightB = os.path.join(CHESS_PATH, 'bN.png')
knightW = os.path.join(CHESS_PATH, 'wN.png')
rookB = os.path.join(CHESS_PATH, 'bR.png')
rookW = os.path.join(CHESS_PATH, 'wR.png')
queenB = os.path.join(CHESS_PATH, 'bQ.png')
queenW = os.path.join(CHESS_PATH, 'wQ.png')
kingB = os.path.join(CHESS_PATH, 'bK.png')
kingW = os.path.join(CHESS_PATH, 'wK.png')


images = {BISHOPB: bishopB, BISHOPW: bishopW, PAWNB: pawnB, PAWNW: pawnW,
          KNIGHTB: knightB, KNIGHTW: knightW,
          ROOKB: rookB, ROOKW: rookW, KINGB: kingB, KINGW: kingW,
          QUEENB: queenB, QUEENW: queenW, BLANK: blank}


def change_square_color(window, row, col):
    """ 
    Change the color of a square based on square row and col.
    """
    btn_sq = window.FindElement(key=(row, col))
    is_dark_square = True if (row + col) % 2 else False
    bd_sq_color = DARK_SQ_MOVE_COLOR if is_dark_square else LIGHT_SQ_MOVE_COLOR
    btn_sq.Update(button_color=('white', bd_sq_color))


def relative_row(s, c):
    """ 
    Returns row based on square s and color c.
    The board can be viewed, as white is at the bottom and black is at the top.
    If c is white the first row is at the bottom.
    If c is black the first row is at the top.
    """
    return 7 - get_row(s) if c else get_row(s)


def get_row(s):
    """ Returns row given square s """
    return 7 - chess.square_rank(s)


def get_col(s):
    """ Returns col given square s """
    return chess.square_file(s)


def redraw_board(window, board):
    """ Redraw GUI board """
    for i in range(8):
        for j in range(8):
            color = '#B58863' if (i + j) % 2 else '#F0D9B5'
            piece_image = images[board[i][j]]
            elem = window.FindElement(key=(i, j))
            elem.Update(button_color=('white', color),
                        image_filename=piece_image, )


def update_rook(window, psg_board, picked_move):
    """ Update rook location on the board for castle move """
    if picked_move == 'e1g1':
        fr = chess.H1
        to = chess.F1
        pc = ROOKW
    elif picked_move == 'e1c1':
        fr = chess.A1
        to = chess.D1
        pc = ROOKW
    elif picked_move == 'e8g8':
        fr = chess.H8
        to = chess.F8
        pc = ROOKB
    elif picked_move == 'e8c8':
        fr = chess.A8
        to = chess.D8
        pc = ROOKB

    psg_board[get_row(fr)][get_col(fr)] = BLANK
    psg_board[get_row(to)][get_col(to)] = pc
    redraw_board(window, psg_board) 
    

def update_ep(window, psg_board, move, stm):
    """ 
    Update board if move is an ep capture.
    move is the ep move in python-chess format
    stm is side to move
    * Remove the piece at to-8 (stm is white), to+8 (stm is black)
    """
    to = move.to_square
    if stm:
        capture_sq = to - 8
    else:
        capture_sq = to + 8

    psg_board[get_row(capture_sq)][get_col(capture_sq)] = BLANK
    redraw_board(window, psg_board)
    
    
def get_promo_piece(window, psg_board, move, stm, human):
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
    # If this move is from a user, we will show a popup box where the user can
    # select which piece to promote, can be q, r, b or n
    if human:
        promote_pc = sg.PopupGetText('Promotion\n\nInput [q, r, b, n] or [Q, R, B, N]', title=BOX_TITLE, keep_on_top=True)
    
        # If user selects the cancel button we set the promote piece to queen
        if promote_pc is None:
            promote_pc = 'q'
            
        if stm:
            if 'q' in promote_pc.lower():
                psg_promo = QUEENW
                pyc_promo = chess.QUEEN
            elif 'r' in promote_pc.lower():
                psg_promo = ROOKW
                pyc_promo = chess.ROOK
            elif 'b' in promote_pc.lower():
                psg_promo = BISHOPW
                pyc_promo = chess.BISHOP
            elif 'n' in promote_pc.lower():
                psg_promo = KNIGHTW
                pyc_promo = chess.KNIGHT
        else:
            if 'q' in promote_pc.lower():
                psg_promo = QUEENB
                pyc_promo = chess.QUEEN
            elif 'r' in promote_pc.lower():
                psg_promo = ROOKB
                pyc_promo = chess.ROOK
            elif 'b' in promote_pc.lower():
                psg_promo = BISHOPB
                pyc_promo = chess.BISHOP
            elif 'n' in promote_pc.lower():
                psg_promo = KNIGHTB
                pyc_promo = chess.KNIGHT
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


def get_engines():
    """ Returns a list of engines located in Engines dir """
    engine_list = []
    engine_path = './Engines/'
    files = os.listdir(engine_path)
    for file in files:
        engine_list.append(file)
        
    return engine_list


def render_square(image, key, location):
    """ Render square """
    if (location[0] + location[1]) % 2:
        color = '#B58863'
    else:
        color = '#F0D9B5'
    return sg.RButton('', image_filename=image, size=(1, 1), 
                      button_color=('white', color), pad=(0, 0), key=key)


def create_board(psg_board, is_user_white):
    """
    Returns board layout for main layout. The board is oriented depending on
    the value of is_user_white.
    """
    # the main board display layout
    board_layout = []
    
    start = 0
    end = 8
    step = 1
    file_char_name = 'abcdefgh'
    
    if not is_user_white:
        start = 7
        end = -1
        step = -1
        file_char_name = file_char_name[::-1]
    
    # loop though board and create buttons with images
    for i in range(start, end, step):
        # Row numbers at left of board
        row = [sg.T(str(8 - i) + '  ', font='Any 11')]
        
        for j in range(start, end, step):
            piece_image = images[psg_board[i][j]]
            row.append(render_square(piece_image, key=(i, j), location=(i, j)))

        board_layout.append(row)
        
    # add the labels across bottom of board
    board_layout.append([sg.T('     ')] + [sg.T('{}'.format(a), pad=((23, 27), 0),
                        font='Any 11') for a in file_char_name])
        
    return board_layout


def start_engine(enginefn):
    """ Start engine """
    eng_filename = './Engines/' + enginefn
    if eng_filename is None:
        print('Failed to load engine')
        sys.exit()
    engine = chess.engine.SimpleEngine.popen_uci(eng_filename)
    engine_id_name = engine.id['name']
    
    return engine, engine_id_name
    
    
def build_main_layout(is_user_white):
    """
    Build the main part of GUI, board is oriented based on the color of the side to move first.
    is_user_white:
        It this is True, the board is oriented such that the white pieces
        are in the bottom. Otherwise the board will be oriented such that
        the black pieces are at the bottom.
    """
     
    menu_def = [['&File', ['E&xit']],
                ['&Game', ['&New Game', 'Exit Game']],
                ['&Engine', ['Go', 'Depth', 'Movetime', 'Settings']],
                ['&Help', ['Play']],
                ]
    
    sg.ChangeLookAndFeel('Reddit')
    psg_board = copy.deepcopy(initial_board)
    
    # Define board
    board_layout = create_board(psg_board, is_user_white)

    board_controls = [
        [sg.Text('Game status: Waiting ...', size=(36, 1), font=('Consolas', 10), key='_gamestatus_')],
        [sg.Text('White', size=(6, 1), font=('Consolas', 10)), sg.InputText('', font=('Consolas', 10), key='_White_', size=(34, 1))],
        [sg.Text('Black', size=(6, 1), font=('Consolas', 10)), sg.InputText('', font=('Consolas', 10), key='_Black_', size=(34, 1))],
        [sg.Text('MOVE LIST', font=('Consolas', 10))],            
        [sg.Multiline([], do_not_clear=True, autoscroll=True, size=(40, 8), font=('Consolas', 10), key='_movelist_')],
        [sg.Text('ENGINE SEARCH INFO', font=('Consolas', 10))],
        [sg.Multiline([], do_not_clear=True, autoscroll=True, size=(40, 4), font=('Consolas', 10), key='_engineinfo_')],
        
    ]

    board_tab = [[sg.Column(board_layout)]]

    # the main window layout
    layout = [[sg.Menu(menu_def, tearoff=False)],
              [sg.TabGroup([[sg.Tab('Board', board_tab)]], title_color='red'),
               sg.Column(board_controls)],
              ]

    window = sg.Window('{} {}'.format(APP_NAME, APP_VERSION), layout,
                       default_button_element_size=(12, 1),
                       auto_size_buttons=False,
                       icon='')
    
    return window, psg_board


def init_user_option():
    """ Shows user options for user color and engine opponent """
    engine_list = get_engines()
    
    layout = [
        [sg.Radio('I play with white color', 'first_color', size=(24, 1), font=('Consolas', 10), default=True, key = '_white_'), 
         sg.Radio('I play with black color', 'first_color', size=(24, 1), font=('Consolas', 10), key = '_black_')],
        [sg.Text('Engine opponent', size=(16, 1), font=('Consolas', 10)), sg.Drop(engine_list, size=(34, 1), font=('Consolas', 10), key='_enginefn_')],
        [sg.Button('OK', size=(6, 1), font=('Consolas', 10), key='_ok_')],
    ]
    
    init_window = sg.Window('{} {}'.format(APP_NAME, APP_VERSION), layout,
                       default_button_element_size=(12, 1),
                       auto_size_buttons=False,
                       icon='')

    enginefn = None
    while True:        
        button, value = init_window.Read()        
        enginefn = value['_enginefn_']
        is_player_white = value['_white_']
        if button == '_ok_':
            break
            
    init_window.Close()
    
    return enginefn, True if is_player_white else False


def play_game(window, psg_board, engine, engine_id_name, is_user_white):
    """ 
    Plays a game against an engine. Move legality is handled by python-chess.
    """ 
    window.FindElement('_movelist_').Update('')
    window.FindElement('_engineinfo_').Update('')
            
    is_human_stm = True if is_user_white else False
    
    psg_board = copy.deepcopy(initial_board)
    redraw_board(window, psg_board)

    board = chess.Board()
    move_state = 0
    move_from, move_to = None, None
    level = 1
    move_time = 1  # sec
    is_new_game, is_exit_game = False, False
    
    # Do not play immediately when stm is computer
    is_engine_ready = True if is_human_stm else False
    
    # Game loop
    while not board.is_game_over(claim_draw=True):
        moved_piece = None
        
        # If engine is to play first, allow the user to configure the engine
        # and exit this loop when user presses the Engine->Go button
        if not is_engine_ready:
            while True:
                button, value = window.Read(timeout=10)
                
                if button in (None, 'Exit'):
                    engine.quit()
                    sys.exit()
                
                if button in (None, 'Depth'):
                    backup_level = level
                    user_depth = sg.PopupGetText('Current depth is {}\n\nInput depth[1 to 8]'.format(backup_level), title=BOX_TITLE)
                    if user_depth is None:
                        user_depth = backup_level
                    level = int(user_depth)
                    level = min(8, max(1, level))
                    print('depth is set to', level)
                
                if button in (None, 'Movetime'):
                    backup_movetime = move_time
                    user_movetime = sg.PopupGetText('Current move time is {}s\n\nInput move time [1 to 5]'.format(backup_movetime), title=BOX_TITLE)
                    if user_movetime is None:
                        user_movetime = backup_movetime  # sec
                    move_time = int(user_movetime)
                    move_time = min(MAX_TIME, max(MIN_TIME, move_time))
                    print('move_time is set to', move_time)
                
                if button in (None, 'Settings'):
                    sg.PopupOK('Depth={}\nMovetime={}\nengine={}\n'.format(level, move_time, engine_id_name), title=BOX_TITLE, keep_on_top=True)
                    
                if button in (None, 'Play'):
                    sg.Popup('* To play a game, press Game->New Game\n* When playing as black, press Engine->Go to start the engine', title=BOX_TITLE)
                
                if button in (None, 'Go'):
                    is_engine_ready = True
                    break

        # If side to move is human
        if is_human_stm:
            move_state = 0
            while True:
                button, value = window.Read(timeout=10)
                
                if not is_human_stm:
                    break
                
                if button in (None, 'Exit'):
                    engine.quit()
                    sys.exit()
                
                if button in (None, 'New Game'):
                    is_new_game = True
                    break
                
                if button in (None, 'Exit Game'):
                    is_exit_game = True
                    break
                
                if button in (None, 'Play'):
                    sg.Popup('* To play a game, press Game->New Game\n* When playing as black, press Engine->Go to start the engine', title=BOX_TITLE)
                    break
                
                if button in (None, 'Go'):
                    if is_human_stm:
                        is_human_stm = False
                    else:
                        is_human_stm = True
                    is_engine_ready = True
                    window.FindElement('_gamestatus_').Update('Game status: Engine is thinking ...')
                    break
                
                if button in (None, 'Settings'):
                    sg.PopupOK('Depth={}\nMovetime={}\nengine={}\n'.format(level, move_time, engine_id_name), title=BOX_TITLE, keep_on_top=True)
                    break
                
                if button in (None, 'Depth'):
                    backup_level = level
                    user_depth = sg.PopupGetText('Current depth is {}\n\nInput depth[1 to 8]'.format(backup_level), title=BOX_TITLE)
                    if user_depth is None:
                        user_depth = backup_level
                    level = int(user_depth)
                    level = min(8, max(1, level))
                    print('depth is set to', level)
                    break
                
                if button in (None, 'Movetime'):
                    backup_movetime = move_time
                    user_movetime = sg.PopupGetText('Current move time is {}s\n\nInput move time [1 to 5]'.format(backup_movetime), title=BOX_TITLE)
                    if user_movetime is None:
                        user_movetime = backup_movetime  # sec
                    move_time = int(user_movetime)
                    move_time = min(MAX_TIME, max(MIN_TIME, move_time))
                    print('move_time is set to', move_time)
                    break
                
                if type(button) is tuple:
                    # If fr_sq button is pressed
                    if move_state == 0:
                        move_from = button
                        fr_row, fr_col = move_from
                        piece = psg_board[fr_row][fr_col]  # get the move-from piece
                        
                        # Change the color of the "fr" board square
                        change_square_color(window, fr_row, fr_col)
                        
                        move_state = 1
                        moved_piece = board.piece_type_at(chess.square(fr_col, 7-fr_row))  # Pawn=1
                    
                    # Else if to_sq button is pressed
                    elif move_state == 1:
                        is_promote = False
                        move_to = button
                        to_row, to_col = move_to
                        button_square = window.FindElement(key=(fr_row, fr_col))
                        
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
                        if relative_row(to_sq, board.turn) == RANK_8 and moved_piece == chess.PAWN:
                            is_promote = True
                            pyc_promo, psg_promo = get_promo_piece(window, psg_board, user_move, board.turn, True)
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
                                update_rook(window, psg_board, str(user_move))
                                
                            # Update board if e.p capture
                            elif board.is_en_passant(user_move):
                                update_ep(window, psg_board, user_move, board.turn)                                
                                
                            # Empty the board from_square, applied to any types of move
                            psg_board[move_from[0]][move_from[1]] = BLANK
                            
                            # Update board to_square if move is a promotion
                            if is_promote:
                                psg_board[to_row][to_col] = psg_promo
                            # Update the to_square if not a promote move
                            else:
                                # Place piece in the move to_square
                                psg_board[to_row][to_col] = piece
                                
                            redraw_board(window, psg_board)
                            window.FindElement('_movelist_').Update(show_san_move, append=True)

                            board.push(user_move)
                            
                            # Change the color of the "fr" and "to" board squares
                            change_square_color(window, fr_row, fr_col)
                            change_square_color(window, to_row, to_col)

                            is_human_stm ^= 1
                            
                            window.FindElement('_engineinfo_').Update('', append=False)
                            window.FindElement('_gamestatus_').Update('Game status: Engine is thinking ...')
                            
                            # Human has done its move
                     
                        # Else if move is illegal
                        else:
                            move_state = 0
                            color = '#B58863' if (move_from[0] + move_from[1]) % 2 else '#F0D9B5'
                            
                            # Restore the color of the fr square
                            button_square.Update(button_color=('white', color))
                            continue
                
            if is_new_game or is_exit_game:
                break

        # Else if side to move is not human
        elif not is_human_stm:
            is_promote = False
            is_play = False
            
            if is_play:
                result = engine.play(board, chess.engine.Limit(depth=level, time=move_time), info=chess.engine.INFO_ALL)
                best_move = result.move
                engine_score_info = result.info['score'].relative.score(mate_score=32000) / 100
                engine_depth_info = result.info['depth']
                engine_pv_info = board.variation_san(result.info['pv'])
                engine_info = str(engine_score_info) + '/' + str(engine_depth_info) + ' ' + engine_pv_info
                window.FindElement('_engineinfo_').Update(engine_info, append=False)
            else:
                best_move = None
                with engine.analysis(board, chess.engine.Limit(depth=level, time=move_time), info=chess.engine.INFO_ALL) as analysis:
                    for info in analysis:
                        time.sleep(0.1)
                        if 'pv' in info and 'score' in info and 'depth' in info and 'time' in info:
                            best_move = info['pv'][0]
                            best_score = info['score'].relative.score(mate_score=32000) / 100
                            best_depth = info['depth']
                            best_time = info['time']
                            best_pv = info['pv'][0:5]
                            
                            best_pv = board.variation_san(best_pv)
                            
                            engine_info = '{:+0.02f}/{:02d} {}\n'.format(best_score, best_depth, best_pv)
                            window.FindElement('_engineinfo_').Update(engine_info, append=True)
                            
                            if best_time >= move_time:
                                break
                            if best_depth >= level:
                                break
        
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
            window.FindElement('_movelist_').Update(show_san_move, append=True)

            piece = psg_board[fr_row][fr_col]
            psg_board[fr_row][fr_col] = BLANK            
            
            # Update rook location if this is a castle move
            if board.is_castling(best_move):
                update_rook(window, psg_board, move_str)
                
            # Update board if e.p capture
            elif board.is_en_passant(best_move):
                update_ep(window, psg_board, best_move, board.turn)
                
            # Update board if move is a promotion
            elif best_move.promotion is not None:
                is_promote = True
                _, psg_promo = get_promo_piece(window, psg_board, best_move, board.turn, False)
                
            # Update board to_square if move is a promotion
            if is_promote:
                psg_board[to_row][to_col] = psg_promo
            # Update the to_square if not a promote move
            else:
                # Place piece in the move to_square
                psg_board[to_row][to_col] = piece
                
            redraw_board(window, psg_board)

            board.push(best_move)
            
            # Change the color of the "fr" and "to" board squares
            change_square_color(window, fr_row, fr_col)
            change_square_color(window, to_row, to_col)
            
            is_human_stm ^= 1
            
            window.FindElement('_gamestatus_').Update('Game status: Playing ...')
            
            # Engine has done its move
            
    # Exit game over loop
    
    if is_exit_game:
        return False
    
    if not is_new_game:
        result = board.result(claim_draw=True)
        sg.Popup('Game over!\n\nResult is {}\nThank you for playing'.format(result), title=BOX_TITLE)
    
    return is_new_game
            
            
def build_gui():
    """ 
    Builds the main GUI, this includes board orientation and engine initialization.
    """
    enginefn, is_user_white = init_user_option()

    window, psg_board = build_main_layout(is_user_white)
    
    # Start engine and get its id name
    engine, engine_id_name = start_engine(enginefn)
    
    # Update White/Black label values
    if is_user_white:
        window.FindElement('_White_').Update('Human')
        window.FindElement('_Black_').Update(engine_id_name)
    else:
        window.FindElement('_White_').Update(engine_id_name)
        window.FindElement('_Black_').Update('Human')
        
    return window, psg_board, engine, engine_id_name, is_user_white


def main_loop():
    """ 
    This is where we build our GUI and read user inputs. When user presses Exit we also quit the engine.
    """
    window, psg_board, engine, engine_id_name, is_user_white = build_gui()
    
    while True:
        button, value = window.Read(timeout=10)
        if button in (None, 'Exit'):
            break
        if button in (None, 'Play'):
            sg.Popup('* To play a game, press Game->New Game\n* When playing as black, press Engine->Go to start the engine', title=BOX_TITLE)
            continue
        if button in (None, 'New Game'):
            while True:
                window.FindElement('_gamestatus_').Update('Game status: Playing ...')
                start_new_game = play_game(window, psg_board, engine, engine_id_name, is_user_white)
                window.FindElement('_gamestatus_').Update('Game status: Waiting ...')
                if not start_new_game:
                    break
            continue
        
    engine.quit()
    window.Close()


def main():
    main_loop()


if __name__ == "__main__":
    main()
