import json
import logging
import subprocess
import threading
import time
from pathlib import Path

import chess
import chess.engine

from python_easy_chess_gui.config import (
    MAX_DEPTH,
    sys_os,
)


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
        """ Interrupt engine search """
        self._kill.set()

    def get_board(self, board):
        """ Get the current board position """
        self.board = board

    def configure_engine(self):
        """ Read the engine config file pecg_engines.json and set the engine to
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
                                logging.info('Set {} to {}'.format(
                                    n['name'], user_value))
                            except Exception:
                                logging.exception('{Failed to configure '
                                                  'engine}')

    def run(self):
        """
        Run engine to get search info and bestmove. If there is error we
        still send bestmove None.

        :return: bestmove thru que
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
                            self.score = int(info['score'].relative.score(
                                mate_score=32000))/100

                        self.time = info['time'] if 'time' in info \
                                else time.perf_counter() - start_time

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
            result = self.engine.play(self.board, limit,info=chess.engine.INFO_ALL)
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
        self.eng_queue.put('bestmove {}' .format(self.bm))
        logging.info('bestmove {}'.format(self.bm))

    def quit_engine(self):
        """ Quit engine """
        logging.info('quit engine')
        try:
            self.engine.quit()
        except AttributeError:
            logging.info('AttributeError, self.engine is already None')
        except Exception:
            logging.exception('Failed to quit engine.')

    def short_variation_san(self):
        """ Returns variation in san but without move numbers """
        if self.pv is None:
            return None

        short_san_pv = []
        tmp_board = self.board.copy()
        for pc_move in self.pv:
            san_move = tmp_board.san(pc_move)
            short_san_pv.append(san_move)
            tmp_board.push(pc_move)

        return ' '.join(short_san_pv)
