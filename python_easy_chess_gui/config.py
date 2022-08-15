import os
import platform as sys_plat
import sys
import chess

from python_easy_chess_gui import (
    ROOT_PATH,
)


APP_NAME = "Python Easy Chess GUI"
APP_VERSION = "v1.15"
BOX_TITLE = "{} {}".format(APP_NAME, APP_VERSION)
MIN_DEPTH = 1
MAX_DEPTH = 1000
MANAGED_UCI_OPTIONS = [
    "ponder",
    "uci_chess960",
    "multipv",
    "uci_analysemode",
    "ownbook",
]
GUI_THEME = [
    "Green",
    "GreenTan",
    "LightGreen",
    "BluePurple",
    "Purple",
    "BlueMono",
    "GreenMono",
    "BrownBlue",
    "BrightColors",
    "NeutralBlue",
    "Kayak",
    "SandyBeach",
    "TealMono",
    "Topanga",
    "Dark",
    "Black",
    "DarkAmber",
]
IMAGE_PATH = ROOT_PATH / "Images/60"  # path to the chess pieces

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

HELP_MSG = """(A) To play a game
You should be in Play mode.
1. Mode->Play
2. Make move on the board

(B) To play as black
You should be in Neutral mode
1. Board->Flip
2. Mode->Play
3. Engine->Go
If you are already in Play mode, go back to
Neutral mode via Mode->Neutral

(C) To flip board
You should be in Neutral mode
1. Board->Flip

(D) To paste FEN
You should be in Play mode
1. Mode->Play
2. FEN->Paste

(E) To show engine search info after the move
1. Right-click on the Opponent Search Info and press Show

(F) To Show book 1 and 2
1. Right-click on Book 1 or 2 press Show
"""

INIT_PGN_TAG = {
    "Event": "Human vs computer",
    "White": "Human",
    "Black": "Computer",
}
log_format = (
    "%(asctime)s :: %(funcName)s :: line: %(lineno)d :: %("
    "levelname)s :: %(message)s"
)
sys_os = sys_plat.system()
platform = sys.platform

blank = IMAGE_PATH / "blank.png"
bishopB = IMAGE_PATH / "bB.png"
bishopW = IMAGE_PATH / "wB.png"
pawnB = IMAGE_PATH / "bP.png"
pawnW = IMAGE_PATH / "wP.png"
knightB = IMAGE_PATH / "bN.png"
knightW = IMAGE_PATH / "wN.png"
rookB = IMAGE_PATH / "bR.png"
rookW = IMAGE_PATH / "wR.png"
queenB = IMAGE_PATH / "bQ.png"
queenW = IMAGE_PATH / "wQ.png"
kingB = IMAGE_PATH / "bK.png"
kingW = IMAGE_PATH / "wK.png"

BOOK_PATH = ROOT_PATH / "Book"
ICON_PATH = ROOT_PATH / "Icon"
ico_path = {
    "win32": {
        "pecg": ICON_PATH / "pecg.ico",
        "enemy": ICON_PATH / "enemy.ico",
        "adviser": ICON_PATH / "adviser.ico",
    },
    "linux": {
        "pecg": ICON_PATH / "pecg.png",
        "enemy": ICON_PATH / "enemy.png",
        "adviser": ICON_PATH / "adviser.png",
    },
    "darwin": {
        "pecg": ICON_PATH / "pecg.png",
        "enemy": ICON_PATH / "enemy.png",
        "adviser": ICON_PATH / "adviser.png",
    },
}

ENGINE_PATH = ROOT_PATH / "Engines"
images = {
    BISHOPB: bishopB,
    BISHOPW: bishopW,
    PAWNB: pawnB,
    PAWNW: pawnW,
    KNIGHTB: knightB,
    KNIGHTW: knightW,
    ROOKB: rookB,
    ROOKW: rookW,
    KINGB: kingB,
    KINGW: kingW,
    QUEENB: queenB,
    QUEENW: queenW,
    BLANK: blank,
}

# Promote piece from psg (pysimplegui) to pyc (python-chess)
promote_psg_to_pyc = {
    KNIGHTB: chess.KNIGHT,
    BISHOPB: chess.BISHOP,
    ROOKB: chess.ROOK,
    QUEENB: chess.QUEEN,
    KNIGHTW: chess.KNIGHT,
    BISHOPW: chess.BISHOP,
    ROOKW: chess.ROOK,
    QUEENW: chess.QUEEN,
}
initial_board = [
    [ROOKB, KNIGHTB, BISHOPB, QUEENB, KINGB, BISHOPB, KNIGHTB, ROOKB],
    *[
        [_piece] * 8
        for _piece in (
            PAWNB,
            BLANK,
            BLANK,
            BLANK,
            BLANK,
            PAWNW,
        )
    ],
    [ROOKW, KNIGHTW, BISHOPW, QUEENW, KINGW, BISHOPW, KNIGHTW, ROOKW],
]
white_init_promote_board = [[QUEENW, ROOKW, BISHOPW, KNIGHTW]]
black_init_promote_board = [[QUEENB, ROOKB, BISHOPB, KNIGHTB]]

# (1) Mode: Neutral
menu_def_neutral = [
    ["&Mode", ["Play"]],
    [
        "Boar&d",
        [
            "Flip",
            "Color",
            [
                "Brown::board_color_k",
                "Blue::board_color_k",
                "Green::board_color_k",
                "Gray::board_color_k",
            ],
            "Theme",
            GUI_THEME,
        ],
    ],
    [
        "&Engine",
        [
            "Set Engine Adviser",
            "Set Engine Opponent",
            "Set Depth",
            "Manage",
            ["Install", "Edit", "Delete"],
        ],
    ],
    ["&Time", ["User::tc_k", "Engine::tc_k"]],
    ["&Book", ["Set Book::book_set_k"]],
    ["&User", ["Set Name::user_name_k"]],
    ["Tools", ["PGN", ["Delete Player::delete_player_k"]]],
    ["&Settings", ["Game::settings_game_k"]],
    ["&Help", ["About"]],
]

# (2) Mode: Play, info: hide
menu_def_play = [
    ["&Mode", ["Neutral"]],
    [
        "&Game",
        [
            "&New::new_game_k",
            "Save to My Games::save_game_k",
            "Save to White Repertoire",
            "Save to Black Repertoire",
            "Resign::resign_game_k",
            "User Wins::user_wins_k",
            "User Draws::user_draws_k",
        ],
    ],
    ["FEN", ["Paste"]],
    ["&Engine", ["Go", "Move Now"]],
    ["&Help", ["About"]],
]
