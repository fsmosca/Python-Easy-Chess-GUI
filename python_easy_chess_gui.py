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
import chess
import chess.pgn
import copy
import chess.uci


APP_NAME = 'Python Easy Chess GUI'
APP_VERSION = 'v0.1.0'


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


# Absolute rank based on real chess board, white at bottom, black at top
# This is also the rank mapping used by python-chess modules
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


images = {BISHOPB: bishopB, BISHOPW: bishopW, PAWNB: pawnB, PAWNW: pawnW,
          KNIGHTB: knightB, KNIGHTW: knightW,
          ROOKB: rookB, ROOKW: rookW, KINGB: kingB, KINGW: kingW,
          QUEENB: queenB, QUEENW: queenW, BLANK: blank}


def open_pgn_file(filename):
    """ Read pgn file and parse moves in the game.
        Not used at the moment .
    """
    pass
    # pgn = open(filename)
    # first_game = chess.pgn.read_game(pgn)
    # moves = [move for move in first_game.main_line()]
    # return moves


def relative_row(s, c):
    """ 
    Returns row based on square s and color c
    The board will be viewed as white is at the bottom and black is at the top.
    If c is white the first row is at the bottom.
    If c is black the first row is at the top.
    Note rank 1 in real board is row 0 in this program.
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
    Returns promotion piece based on python-chess module and also
    returns promotion piece based on PySimpleGUI for psg board update
    move is the promote move in python-chess format
    stm is side to move
    """    
    # If this move is from a user, we will show a popup box where can
    # select which piece to promote, can be q, r, b or n
    if human:
        promote_pc = sg.PopupGetText('Input [q, r, b, n] or [Q, R, B, N]', 'Promotion')
    
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
        pyc_promo = move.promotion
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
            piece_image = images[board[i][j]]
            elem = window.FindElement(key=(i, j))
            elem.Update(button_color=('white', color),
                        image_filename=piece_image, )


def PlayGame():
    """ Load chess engine and use can play a game.
        This also creates a chessboard. Move legality is handled
        by python-chess
    """
    menu_def = [['&File', ['&Open PGN File', 'E&xit']],
                ['&Help', '&About...'], ]

    # sg.SetOptions(margins=(0,0))
    sg.ChangeLookAndFeel('GreenTan')
    # create initial board setup
    psg_board = copy.deepcopy(initial_board)
    # the main board display layout
    board_layout = [[sg.T('     ')] + [sg.T('{}'.format(a), pad=((23, 27), 0),
                    font='Any 13') for a in 'abcdefgh']]
    # loop though board and create buttons with images
    for i in range(8):
        row = [sg.T(str(8 - i) + '   ', font='Any 13')]
        for j in range(8):
            piece_image = images[psg_board[i][j]]
            row.append(render_square(piece_image, key=(i, j), location=(i, j)))
        row.append(sg.T(str(8 - i) + '   ', font='Any 13'))
        board_layout.append(row)
    # add the labels across bottom of board
    board_layout.append([sg.T('     ')] + [sg.T('{}'.format(a), pad=((23, 27), 0),
                        font='Any 13') for a in 'abcdefgh'])

    board_controls = [[sg.RButton('New Game', key='New Game'), sg.RButton('Draw')],
                      [sg.RButton('Resign Game'), sg.RButton('Set FEN')],
                      [sg.RButton('Player Odds'), sg.RButton('Training')],
                      
                      [sg.Text('User will play as white')], 
                      
                      [sg.Text('Engine'), sg.InputText('', key='_engineid_', size=(22, 1))],
                      
                      [sg.Text('Max depth limit', size=(18, 1)), 
                       sg.Drop([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                               size=(4, 1),
                               key='_level_')],
                      
                      [sg.Text('Move List')],
                      [sg.Multiline([], do_not_clear=True, autoscroll=True,
                                    size=(15, 10), key='_movelist_')],
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

    filename = sg.PopupGetFile('\n'.join(('To begin, set location of AI exe file',
        'If you have not done so already, download a sample engine like',
        'Stockfish at: https://stockfishchess.org/download/')),
         file_types=(('Chess AI Engine EXE File', '*.exe'),))
    if filename is None:
        window.Close()
        sg.Popup('Engine filename is missing, program will exit')
        sys.exit()
    engine = chess.uci.popen_engine(filename)
    engine.uci()
    engineid = engine.name
    info_handler = chess.uci.InfoHandler()
    engine.info_handlers.append(info_handler)

    board = chess.Board()
    move_count = 1
    move_state = move_from = move_to = 0
    exit_is_pressed = False
    level = 2
    
    window.FindElement('_engineid_').Update(' '.join(engineid.split()[0:2]))
    
    # ---===--- Loop taking in user input --- #
    while not board.is_game_over():
        moved_piece = None

        if board.turn == chess.WHITE:
            engine.position(board)

            # human_player(board)
            move_state = 0
            while True:
                button, value = window.Read()
                level = value['_level_']
                
                if button in (None, 'Exit'):
                    exit_is_pressed = True
                    break
                if button == 'New Game':
                    psg_board = copy.deepcopy(initial_board)
                    redraw_board(window, psg_board)
                    board = chess.Board()
                    move_state = move_from = move_to = 0
                    move_count = 1
                    window.FindElement('_movelist_').Update('')
                    break
                
                if type(button) is tuple:
                    if move_state == 0:
                        move_from = button
                        row, col = move_from
                        piece = psg_board[row][col]  # get the move-from piece
                        button_square = window.FindElement(key=(row, col))
                        button_square.Update(button_color=('white', 'red'))
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
                            if board.turn:
                                show_san_move = '{}. {} '.format(board.fullmove_number, san_move)
                            else:
                                show_san_move = '{}\n'.format(san_move)                                
                                
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
                            break                        
                        else:
                            print('Illegal move')
                            move_state = 0
                            color = '#B58863' if (move_from[0] + move_from[1]) % 2 else '#F0D9B5'
                            button_square.Update(button_color=('white', color))
                            continue
                
            if exit_is_pressed:
                break

        # Else if Black to move
        else:
            is_promote = False
            engine.position(board)
            best_move = engine.go(searchmoves=board.legal_moves, depth=level, movetime=(level * 100)).bestmove
            move_str = str(best_move)
            from_col = ord(move_str[0]) - ord('a')
            from_row = 8 - int(move_str[1])
            to_col = ord(move_str[2]) - ord('a')
            to_row = 8 - int(move_str[3])
            
            # Convert user move to san move for display in movelist
            san_move = board.san(best_move)
            if not board.turn:
                show_san_move = '{}\n'.format(san_move)
            else:
                show_san_move = '{}. {} '.format(board.fullmove_number, san_move)
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
            
    engine.quit()
    
    if exit_is_pressed:
        sg.Popup('Program will exit')
    else:
        sg.Popup('Game over!', 'Thank you for playing')

    window.Close()
    print('window is closed')


def main():
    PlayGame()


if __name__ == "__main__":
    main()
