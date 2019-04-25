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
APP_VERSION = 'v0.3.0'
BOX_TITLE = APP_NAME + ' ' + APP_VERSION


CHESS_PATH = 'Images'  # path to the chess pieces


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


blank = os.path.join(CHESS_PATH, 'blank.png')
bishopB = os.path.join(CHESS_PATH, 'nbishopb.png')
bishopW = os.path.join(CHESS_PATH, 'nbishopw.png')
pawnB = os.path.join(CHESS_PATH, 'npawnb.png')
pawnW = os.path.join(CHESS_PATH, 'npawnw.png')
knightB = os.path.join(CHESS_PATH, 'nknightb.png')
knightW = os.path.join(CHESS_PATH, 'nknightw.png')
rookB = os.path.join(CHESS_PATH, 'nrookb.png')
rookW = os.path.join(CHESS_PATH, 'nrookw.png')
queenB = os.path.join(CHESS_PATH, 'nqueenb.png')
queenW = os.path.join(CHESS_PATH, 'nqueenw.png')
kingB = os.path.join(CHESS_PATH, 'nkingb.png')
kingW = os.path.join(CHESS_PATH, 'nkingw.png')

# 2d piece images
blank2 = os.path.join(CHESS_PATH, 'blank.png')
bishopB2 = os.path.join(CHESS_PATH, 'bishopb.png')
bishopW2 = os.path.join(CHESS_PATH, 'bishopw.png')
pawnB2 = os.path.join(CHESS_PATH, 'pawnb.png')
pawnW2 = os.path.join(CHESS_PATH, 'pawnw.png')
knightB2 = os.path.join(CHESS_PATH, 'knightb.png')
knightW2 = os.path.join(CHESS_PATH, 'knightw.png')
rookB2 = os.path.join(CHESS_PATH, 'rookb.png')
rookW2 = os.path.join(CHESS_PATH, 'rookw.png')
queenB2 = os.path.join(CHESS_PATH, 'queenb.png')
queenW2 = os.path.join(CHESS_PATH, 'queenw.png')
kingB2 = os.path.join(CHESS_PATH, 'kingb.png')
kingW2 = os.path.join(CHESS_PATH, 'kingw.png')


images = {BISHOPB: bishopB, BISHOPW: bishopW, PAWNB: pawnB, PAWNW: pawnW,
          KNIGHTB: knightB, KNIGHTW: knightW,
          ROOKB: rookB, ROOKW: rookW, KINGB: kingB, KINGW: kingW,
          QUEENB: queenB, QUEENW: queenW, BLANK: blank}

images2 = {BISHOPB: bishopB2, BISHOPW: bishopW2, PAWNB: pawnB2, PAWNW: pawnW2,
          KNIGHTB: knightB2, KNIGHTW: knightW2,
          ROOKB: rookB2, ROOKW: rookW2, KINGB: kingB2, KINGW: kingW2,
          QUEENB: queenB2, QUEENW: queenW2, BLANK: blank2}


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


def start_engine(enginefn):
    """ Start engine """
    eng_filename = './Engines/' + enginefn
    if eng_filename is None:
        print('Failed to load engine')
        sys.exit()
    engine = chess.engine.SimpleEngine.popen_uci(eng_filename)
    engine_id_name = engine.id['name']
    
    return engine, engine_id_name


def init_layout():    
    # List all files in Engines dir
    engine_list = []
    engine_path = './Engines/'
    files = os.listdir(engine_path)
    for file in files:
        engine_list.append(file)
        
    layout = [
        [sg.Radio('I play with white color', 'first_color', size=(24, 1), font=('Consolas', 10), default=True, key = '_white_'), 
         sg.Radio('I play with black color', 'first_color', size=(24, 1), font=('Consolas', 10), key = '_black_')],
        [sg.Text('Engine opponent', size=(16, 1), font=('Consolas', 10)), sg.Drop(engine_list, size=(34, 1), font=('Consolas', 10), key='_enginefn_')],
        [sg.Button('OK', size=(6, 1), font=('Consolas', 10), key='_ok_')],
    ]
    
    init_window = sg.Window('{} {}'.format(APP_NAME, APP_VERSION), layout,
                       default_button_element_size=(12, 1),
                       auto_size_buttons=False,
                       icon='kingb.ico')

    enginefn = None
    while True:        
        button, value = init_window.Read()        
        enginefn = value['_enginefn_']
        is_player_white = value['_white_']
        if button == '_ok_':
            break
            
    init_window.Close()
    
    return enginefn, True if is_player_white else False
    
    
def create_board(is_user_white):
    """
    Build the main GUI, board is oriented based on side to move first.
    is_user_white:
        It this is True, the board is oriented such that the white pieces
        are in the bottom. Otherwise the board will be oriented such that
        the black pieces are at the bottom.
    """
     
    menu_def = [['&File', ['E&xit']],
                ['&Game', ['&New Game']],
                ['&Engine', ['Go', 'Depth', 'Movetime', 'Settings']]
                ]
    
    sg.ChangeLookAndFeel('#B0BEC5')  # Light dark
    psg_board = copy.deepcopy(initial_board)
    
    # the main board display layout
    board_layout = []
    
    start = 0
    end = 8
    step = 1
    file_names = 'abcdefgh'
    
    if not is_user_white:
        start = 7
        end = -1
        step = -1
        file_names = file_names[::-1]
    
    # loop though board and create buttons with images
    for i in range(start, end, step):
        # Row numbers at left of board
        row = [sg.T(str(8 - i) + '  ', font='Any 13')]
        
        for j in range(start, end, step):
            piece_image = images2[psg_board[i][j]]
            row.append(render_square(piece_image, key=(i, j), location=(i, j)))

        board_layout.append(row)
    
    # add the labels across bottom of board
    board_layout.append([sg.T('     ')] + [sg.T('{}'.format(a), pad=((23, 27), 0),
                        font='Any 13') for a in file_names])

    board_controls = [
        [sg.Text('White', size=(6, 1), font=('Consolas', 10)), sg.InputText('', font=('Consolas', 10), key='_White_', size=(34, 1))],            
        [sg.Text('Black', size=(6, 1), font=('Consolas', 10)), sg.InputText('', font=('Consolas', 10), key='_Black_', size=(34, 1))],
        [sg.Text('Move List', font=('Consolas', 10))],            
        [sg.Multiline([], do_not_clear=True, autoscroll=True, size=(40, 4), font=('Consolas', 10), key='_movelist_')],
        [sg.Text('Engine analysis info', font=('Consolas', 10))],
        [sg.Multiline([], do_not_clear=True, autoscroll=True, size=(40, 12), font=('Consolas', 10), key='_engineinfo_')],        
    ]
    
    # layouts for the tabs
    controls_layout = [[sg.Text('Performance Parameters', font='_ 20')],
                       [sg.T('Put stuff like AI engine tuning parms on this tab')]]

    statistics_layout = [[sg.Text('Statistics', font=('_ 20'))],
                         [sg.T('Game statistics go here?')]]

    board_tab = [[sg.Column(board_layout)]]

    # the main window layout
    layout = [[sg.Menu(menu_def, tearoff=False)],
              [sg.TabGroup([[sg.Tab('Board', board_tab),
                             sg.Tab('Controls', controls_layout),
                             sg.Tab('Statistics', statistics_layout)]], title_color='red'),
               sg.Column(board_controls)],
              ]

    window = sg.Window('{} {}'.format(APP_NAME, APP_VERSION), layout,
                       default_button_element_size=(12, 1),
                       auto_size_buttons=False,
                       icon='kingb.ico')
    
    return window, psg_board   


def render_square(image, key, location):
    """ Render square """
    if (location[0] + location[1]) % 2:
        color = '#B58863'
    else:
        color = '#F0D9B5'
    return sg.RButton('', image_filename=image, size=(1, 1), 
                      button_color=('white', color), pad=(0, 0), key=key)


def redraw_board(window, board):
    """ Redraw GUI board """
    for i in range(8):
        for j in range(8):
            color = '#B58863' if (i + j) % 2 else '#F0D9B5'
            piece_image = images2[board[i][j]]
            elem = window.FindElement(key=(i, j))
            elem.Update(button_color=('white', color),
                        image_filename=piece_image, )


def PlayGame():
    """ 
    Plays a game against an engine. Move legality is handled by python-chess.
    """ 
    enginefn, is_user_white = init_layout()
    
    # Build GUI layout
    window, psg_board = create_board(is_user_white)
    
    # Start engine and get its id name
    engine, engine_id_name = start_engine(enginefn)
    
    if is_user_white:
        window.FindElement('_White_').Update('Human')
        window.FindElement('_Black_').Update(engine_id_name)
    else:
        window.FindElement('_White_').Update(engine_id_name)
        window.FindElement('_Black_').Update('Human')
    
    is_human_stm = True if is_user_white else False

    board = chess.Board()
    move_count = 1
    move_state = move_from = move_to = 0
    exit_is_pressed = False
    level = 8
    move_time = 1  # sec
    
    # Do not play immediately when stm is computer
    is_engine_ready = True if is_human_stm else False
    
    # ---===--- Loop taking in user input --- #
    while not board.is_game_over():
        moved_piece = None
        
        # If engine is to play first, allow the user to configure the engine
        # and exit this loop when user presses the Engine->Go button
        if not is_engine_ready:
            while True:
                button, value = window.Read(timeout=10)
                
                if button in (None, 'Exit'):
                    engine.quit()
                    sys.exit()
                    break
                
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
                    move_time = min(5, max(1, move_time))
                    print('move_time is set to', move_time)
                
                if button in (None, 'Settings'):
                    sg.PopupOK('Depth={}\nMovetime={}\nengine={}\n'.format(level, move_time, engine_id_name), title=BOX_TITLE, keep_on_top=True)
                
                if button in (None, 'Go'):
                    is_engine_ready = True
                    break

        # If human moves frist
        if is_human_stm:
            move_state = 0
            while True:
                button, value = window.Read(timeout=10)
                
                if not is_human_stm and move_state == 2:
                    break
                
                if button in (None, 'Exit'):
                    exit_is_pressed = True
                    break
                
                if button in (None, 'Go'):
                    if is_human_stm:
                        is_human_stm = False
                    else:
                        is_human_stm = True
                    is_engine_ready = True
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
                    move_time = min(5, max(1, move_time))
                    print('move_time is set to', move_time)
                    break
                
                if button in (None, 'New Game'):
                    psg_board = copy.deepcopy(initial_board)
                    redraw_board(window, psg_board)
                    board = chess.Board()
                    move_state = move_from = move_to = 0
                    move_count = 1
                    window.FindElement('_movelist_').Update('')
                    window.FindElement('_engineinfo_').Update('')
                    break
                
                if type(button) is tuple:
                    if move_state == 0:
                        move_from = button
                        row, col = move_from
                        piece = psg_board[row][col]  # get the move-from piece
                        button_square = window.FindElement(key=(row, col))
                        button_square.Update(button_color=('white', 'lightskyblue'))
                        move_state = 1
                        moved_piece = board.piece_type_at(chess.square(col, 7-row))  # Pawn=1
                    elif move_state == 1:
                        is_promote = False
                        move_to = button
                        row, col = move_to
                        if move_to == move_from:  # cancelled move
                            color = '#B58863' if (row + col) % 2 else '#F0D9B5'
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
                        to_sq = chess.square(col, 7-row)

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
                                psg_board[row][col] = psg_promo
                            # Update the to_square if not a promote move
                            else:
                                # Place piece in the move to_square
                                psg_board[row][col] = piece
                                
                            redraw_board(window, psg_board)
                            move_count += 1
                            window.FindElement('_movelist_').Update(show_san_move, append=True)

                            board.push(user_move)
                            
                            button_square = window.FindElement(key=(row, col))
                            button_square.Update(button_color=('white', 'lightskyblue'))
            
                            move_state = 2
                            is_human_stm ^= 1
                            
                            window.FindElement('_engineinfo_').Update('', append=False)
                            
                            # Human has done its move
                     
                        else:
                            print('Illegal move')
                            move_state = 0
                            color = '#B58863' if (move_from[0] + move_from[1]) % 2 else '#F0D9B5'
                            button_square.Update(button_color=('white', color))
                            continue
                
            if exit_is_pressed:
                break

        # Else if not is human stm
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
                with engine.analysis(board) as analysis:
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
            from_col = ord(move_str[0]) - ord('a')
            from_row = 8 - int(move_str[1])
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

            piece = psg_board[from_row][from_col]
            psg_board[from_row][from_col] = BLANK            
            
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
            move_count += 1
            
            button_square = window.FindElement(key=(to_row, to_col))
            button_square.Update(button_color=('white', 'lightskyblue'))
            is_human_stm ^= 1
            
            # Engine has done its move
            
    # Exit game over loop
            
    engine.quit()
    
    if exit_is_pressed:
        pass
    else:
        sg.Popup('Game over!\n\nThank you for playing', title=BOX_TITLE)

    window.Close()
    print('window is closed')


def main():
    PlayGame()


if __name__ == "__main__":
    main()
