"""
gtp_connection.py
Module for playing games of Go using GoTextProtocol

Cmput 455 sample code
Written by Cmput 455 TA and Martin Mueller.
Parts of this code were originally based on the gtp module
in the Deep-Go project by Isaac Henrion and Amos Storkey
at the University of Edinburgh.
"""
import re
import time
import traceback
from sys import stderr, stdin, stdout
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
from board import GoBoard
from board_base import (BLACK, BORDER, EMPTY, GO_COLOR, GO_POINT, MAXSIZE,
                        WHITE, coord_to_point, is_black_white, opponent)
from board_util import GoBoardUtil
from engine import GoEngine


class GtpConnection:
    def __init__(self, go_engine: GoEngine, board: GoBoard, debug_mode: bool = False, max_seconds: int = 0) -> None:
        """
        Manage a GTP connection for a Go-playing engine

        Parameters
        ----------
        go_engine:
            a program that can reply to a set of GTP commandsbelow
        board:
            Represents the current board state.
        """
        self._debug_mode: bool = debug_mode
        self.go_engine = go_engine
        self.board: GoBoard = board
        self.max_seconds = max_seconds
        self.commands: Dict[str, Callable[[List[str]], None]] = {
            "protocol_version": self.protocol_version_cmd,
            "quit": self.quit_cmd,
            "name": self.name_cmd,
            "boardsize": self.boardsize_cmd,
            "showboard": self.showboard_cmd,
            "clear_board": self.clear_board_cmd,
            "komi": self.komi_cmd,
            "version": self.version_cmd,
            "known_command": self.known_command_cmd,
            "genmove": self.genmove_cmd,
            "list_commands": self.list_commands_cmd,
            "play": self.play_cmd,
            "legal_moves": self.legal_moves_cmd,
            "gogui-rules_legal_moves": self.gogui_rules_legal_moves_cmd,
            "gogui-rules_final_result": self.gogui_rules_final_result_cmd,
            "solve": self.solve_cmd,
            "timelimit": self.timelimit_cmd
        }

        # argmap is used for argument checking
        # values: (required number of arguments,
        #          error message on argnum failure)
        self.argmap: Dict[str, Tuple[int, str]] = {
            "boardsize": (1, "Usage: boardsize INT"),
            "komi": (1, "Usage: komi FLOAT"),
            "known_command": (1, "Usage: known_command CMD_NAME"),
            "genmove": (1, "Usage: genmove {w,b}"),
            "play": (2, "Usage: play {b,w} MOVE"),
            "legal_moves": (1, "Usage: legal_moves {w,b}"),
        }

    def write(self, data: str) -> None:
        stdout.write(data)

    def flush(self) -> None:
        stdout.flush()

    def start_connection(self) -> None:
        """
        Start a GTP connection.
        This function continuously monitors standard input for commands.
        """
        line = stdin.readline()
        while line:
            self.get_cmd(line)
            line = stdin.readline()

    def get_cmd(self, command: str) -> None:
        """
        Parse command string and execute it
        """
        if len(command.strip(" \r\t")) == 0:
            return
        if command[0] == "#":
            return
        # Strip leading numbers from regression tests
        if command[0].isdigit():
            command = re.sub("^\d+", "", command).lstrip()
        elements: List[str] = command.split()
        if not elements:
            return
        command_name: str = elements[0]
        args: List[str] = elements[1:]
        if self.has_arg_error(command_name, len(args)):
            return
        if command_name in self.commands:
            try:
                self.commands[command_name](args)
            except Exception as e:
                self.debug_msg("Error executing command {}\n".format(str(e)))
                self.debug_msg("Stack Trace:\n{}\n".format(traceback.format_exc()))
                raise e
        else:
            self.debug_msg("Unknown command: {}\n".format(command_name))
            self.error("Unknown command")
            stdout.flush()

    def has_arg_error(self, cmd: str, argnum: int) -> bool:
        """
        Verify the number of arguments of cmd.
        argnum is the number of parsed arguments
        """
        if cmd in self.argmap and self.argmap[cmd][0] != argnum:
            self.error(self.argmap[cmd][1])
            return True
        return False

    def debug_msg(self, msg: str) -> None:
        """ Write msg to the debug stream """
        if self._debug_mode:
            stderr.write(msg)
            stderr.flush()

    def error(self, error_msg: str) -> None:
        """ Send error msg to stdout """
        stdout.write("? {}\n\n".format(error_msg))
        stdout.flush()

    def respond(self, response: str = "") -> None:
        """ Send response to stdout """
        stdout.write("= {}\n\n".format(response))
        stdout.flush()

    def reset(self, size: int) -> None:
        """
        Reset the board to empty board of given size
        """
        self.board.reset(size)

    def board2d(self) -> str:
        return str(GoBoardUtil.get_twoD_board(self.board))

    def protocol_version_cmd(self, args: List[str]) -> None:
        """ Return the GTP protocol version being used (always 2) """
        self.respond("2")

    def quit_cmd(self, args: List[str]) -> None:
        """ Quit game and exit the GTP interface """
        self.respond()
        exit()

    def name_cmd(self, args: List[str]) -> None:
        """ Return the name of the Go engine """
        self.respond(self.go_engine.name)

    def version_cmd(self, args: List[str]) -> None:
        """ Return the version of the  Go engine """
        self.respond(str(self.go_engine.version))

    def clear_board_cmd(self, args: List[str]) -> None:
        """ clear the board """
        self.reset(self.board.size)
        self.respond()

    def boardsize_cmd(self, args: List[str]) -> None:
        """
        Reset the game with new boardsize args[0]
        """
        self.reset(int(args[0]))
        self.respond()

    def showboard_cmd(self, args: List[str]) -> None:
        self.respond("\n" + self.board2d())

    def komi_cmd(self, args: List[str]) -> None:
        """
        Set the engine's komi to args[0]
        """
        self.go_engine.komi = float(args[0])
        self.respond()

    def known_command_cmd(self, args: List[str]) -> None:
        """
        Check if command args[0] is known to the GTP interface
        """
        if args[0] in self.commands:
            self.respond("true")
        else:
            self.respond("false")

    def list_commands_cmd(self, args: List[str]) -> None:
        """ list all supported GTP commands """
        self.respond(" ".join(list(self.commands.keys())))
        
        
        
    def legal_moves_cmd(self, args: List[str]) -> None:
        """
        List legal moves for color args[0] in {'b','w'}
        """
        board_color: str = args[0].lower()
        color: GO_COLOR = color_to_int(board_color)
        moves: List[GO_POINT] = GoBoardUtil.generate_legal_moves(self.board, color)
        gtp_moves: List[str] = []
        for move in moves:
            coords: Tuple[int, int] = point_to_coord(move, self.board.size)
            gtp_moves.append(format_point(coords))
        sorted_moves = " ".join(sorted(gtp_moves))
        self.respond(sorted_moves)
        
        
        
    """
    ==========================================================================
    Assignment 2 - game-specific commands start here
    ==========================================================================
    """
    """
    ==========================================================================
    Assignment 2 - commands we already implemented for you
    ==========================================================================
    """
        
        

    def gogui_analyze_cmd(self, args):
        """ We already implemented this function for Assignment 2 """
        self.respond("pstring/Legal Moves For ToPlay/gogui-rules_legal_moves\n"
                     "pstring/Side to Play/gogui-rules_side_to_move\n"
                     "pstring/Final Result/gogui-rules_final_result\n"
                     "pstring/Board Size/gogui-rules_board_size\n"
                     "pstring/Rules GameID/gogui-rules_game_id\n"
                     "pstring/Show Board/gogui-rules_board\n"
                     )

    def gogui_rules_game_id_cmd(self, args):
        """ We already implemented this function for Assignment 2 """
        self.respond("NoGo")

    def gogui_rules_board_size_cmd(self, args):
        """ We already implemented this function for Assignment 2 """
        self.respond(str(self.board.size))

    def gogui_rules_side_to_move_cmd(self, args):
        """ We already implemented this function for Assignment 2 """
        color = "black" if self.board.current_player == BLACK else "white"
        self.respond(color)

    def gogui_rules_board_cmd(self, args):
        """ We already implemented this function for Assignment 2 """
        size = self.board.size
        str = ''
        for row in range(size-1, -1, -1):
            start = self.board.row_start(row + 1)
            for i in range(size):
                #str += '.'
                point = self.board.board[start + i]
                if point == BLACK:
                    str += 'X'
                elif point == WHITE:
                    str += 'O'
                elif point == EMPTY:
                    str += '.'
                else:
                    assert False
            str += '\n'
        self.respond(str)
        
        
    
    def gogui_rules_legal_moves_cmd(self, args):
        # get all the legal moves
        legal_moves = GoBoardUtil.generate_legal_moves(self.board, self.board.current_player)
        coords = [point_to_coord(move, self.board.size) for move in legal_moves]
        # convert to point strings
        point_strs  = [ chr(ord('a') + col - 1) + str(row) for row, col in coords]
        point_strs.sort()
        point_strs = ' '.join(point_strs).upper()
        self.respond(point_strs)
        return
        


    """
    ==========================================================================
    Assignment 2 - game-specific commands you have to implement or modify
    ==========================================================================
    """
    def gogui_rules_final_result_cmd(self, args):
        """ Implement this method correctly """
        legal_moves = GoBoardUtil.generate_legal_moves(self.board, self.board.current_player)
        if len(legal_moves) > 0:
            self.respond('unknown')
        elif self.board.current_player == BLACK:
            self.respond('')
        else:
            self.respond('')
            

    def play_cmd(self, args: List[str]) -> None:
        """
        play a move args[1] for given color args[0] in {'b','w'}
        """
        # change this method to use your solver
        try:
            board_color = args[0].lower()
            board_move = args[1]
            color = color_to_int(board_color)
            
            coord = move_to_coord(args[1], self.board.size)
            if coord:
                move = coord_to_point(coord[0], coord[1], self.board.size)
            else:
                self.error(
                    "Error executing move {} converted from {}".format(move, args[1])
                )
                return
            if not self.board.is_empty(move) or not self.board.is_legal(move, color):
                self.respond('illegal move')
                return
            else:
                self.board.play_move(move, color)
                self.board.current_player = opponent(color)
                self.debug_msg(
                    "Move: {}\nBoard:\n{}\n".format(board_move, self.board2d())
                )
            self.respond()
        except Exception as e:
            self.respond("Error: {}".format(str(e)))
            
    

    def genmove_cmd(self, args: List[str]) -> None:
        """
        generate a move for color args[0] in {'b','w'}
        If the game is not over yet, call the solve() command.
        If solve() returns False, play a random move     
        """
        start_time = time.process_time()
        board_color = args[0].lower()
        color = color_to_int(board_color)
        empty_points = self.board.get_empty_points()
        empty_points_set = set(empty_points)
        move = self.get_outcome(color, empty_points_set, start_time)
        winner = self.board.get_tt_entry()
        if winner == color:
            move_coord = point_to_coord(move, self.board.size)
            move_as_string = format_point(move_coord)
            self.respond("[" + int_to_color(winner)[0] + " " + move_as_string + "]")
            return
        
        move = self.go_engine.get_move(self.board, color)
        if move is None:
            self.respond('[resign]')
            return
            
        move_coord = point_to_coord(move, self.board.size)
        move_as_string = format_point(move_coord)
        if self.board.is_legal(move, color):
            self.board.play_move(move, color)
            self.board.current_player = opponent(color)
            self.respond(move_as_string)
        else:
            self.respond("Illegal move: {}".format(move_as_string))
    

    def get_all_outcomes(self, color, empty_points: set, start_time) -> dict:
        """
        Attempts to solve a go board
        @return: a winning move for the board state, if one exists for the current color; else None
        @params:
        board - the current state of the board
        color - corresponds to the player who's turn it is
        """
        opponent_color = 3-color
        print(time.process_time() - start_time)
        if time.process_time() - start_time > self.max_seconds:
            return
        #legal_moves = GoBoardUtil.prioritize_legal_moves(self.board, legal_moves, color)
        winning_moves = []
        for move in empty_points:
            if not self.board.is_legal(move, color):
                continue
            self.board.play_move(move, color)

            winning_color = self.board.get_tt_entry()

            # if move results in win or loss
            if winning_color != None:
                self.board.undo_move(move)
                if winning_color == color:
                    winning_moves.append(move)
                    self.board.set_tt_entry(color)
                # else move was win for opponent(color)
                continue

            # else outcome not in tt
            empty_points_copy = empty_points.copy()
            empty_points_copy.remove(move)
            self.get_all_outcomes(opponent_color, empty_points_copy, start_time)

            winner = self.board.get_tt_entry()
            if not winner:
                self.board.undo_move(move)
                return

            # if move was a winning move for current player
            if winner == color:
                winning_moves.append(move)
                self.board.undo_move(move)
                # set board state as a win for the current player
                self.board.set_tt_entry(color)
                #return move

            self.board.undo_move(move)
        # if no legal_moves are all legal_moves are losing
        if winning_moves:
            return winning_moves
        self.board.set_tt_entry(opponent_color)

    
    def get_outcome(self, color, empty_points: set, start_time):
        """
        Attempts to solve a go board
        @return: a winning move for the board state, if one exists for the current color; else None
        @params:
        board - the current state of the board
        color - corresponds to the player who's turn it is
        """
        opponent_color = 3-color
        print(time.process_time() - start_time)
        if time.process_time() - start_time > self.max_seconds: #TODO: put this after recursive call?
            return
        for move in empty_points:
            if not self.board.is_legal(move, color):
                continue
            self.board.play_move(move, color)

            winning_color = self.board.get_tt_entry()
            # if move results in win or loss
            if winning_color != None:
                self.board.undo_move(move)
                if winning_color == color:
                    # set color as winner of current board state
                    self.board.set_tt_entry(color)
                    return move
                # else move was win for opponent(color)
                continue

            empty_points_copy = empty_points.copy()
            empty_points_copy.remove(move)
            # else outcome not in tt
            self.get_outcome(opponent_color, empty_points_copy, start_time)

            winner = self.board.get_tt_entry()
            if not winner:
                self.board.undo_move(move)
                return

            if self.board.get_tt_entry() == color: # this tt_entry now exists
                self.board.undo_move(move)
                # set board state as a win for the current player
                self.board.set_tt_entry(color)
                return move

            self.board.undo_move(move)
        # if no legal_moves or all legal_moves are losing
        self.board.set_tt_entry(opponent_color)
            
            
    def solve_cmd(self, args: List[str]) -> None:
        """
        Attempts to compute the winner of the current position,
        assuming perfect play by both, within the current time limit.
        GTP response is in the following format:
        = winner [move]
        winner is "b", "w", or "unknown"
        - winner is "unknown" if the board cannot be solved within the current time limit
        - If winner ("b" or "w") is the current player, then move should include a winning move.
        - If the winner {"b" or "w"} is not the current player, then no move should be included. 
        """
        start_time = time.process_time()
        empty_points = self.board.get_empty_points()
        empty_points_set = set(empty_points)
        move = self.get_outcome(self.board.current_player, empty_points_set, start_time)
        #winning_moves = self.get_all_outcomes(self.board.current_player, empty_points_set, start_time)
        winner = self.board.get_tt_entry()
        # if timeout
        if not winner:
            self.respond("[unknown]")
            return
        # else it was in time
        if winner == self.board.current_player:
            # for i in range(len(winning_moves)):
            #     move = winning_moves[i]
            move_coord = point_to_coord(move, self.board.size)
            move_as_string = format_point(move_coord)
            #winning_moves[i] = move_as_string
            self.respond("[" + int_to_color(winner)[0] + " " + move_as_string + "]")
        else:
            self.respond("[" + int_to_color(winner)[0] + "]")

    def timelimit_cmd(self, args: List[str]) -> None:
        """
        Sets the time limit
        """
        self.max_seconds = int(args[0])
        self.respond()
        return

    """
    ==========================================================================
    Assignment 2 - game-specific commands end here
    ==========================================================================
    """

def point_to_coord(point: GO_POINT, boardsize: int) -> Tuple[int, int]:
    """
    Transform point given as board array index
    to (row, col) coordinate representation.
    """
    NS = boardsize + 1
    return divmod(point, NS)


def format_point(move: Tuple[int, int]) -> str:
    """
    Return move coordinates as a string such as 'A1'
    """
    assert MAXSIZE <= 25
    column_letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    row, col = move
    return column_letters[col - 1] + str(row)


def move_to_coord(point_str: str, board_size: int) -> Tuple[int, int]:
    """
    Convert a string point_str representing a point, as specified by GTP,
    to a pair of coordinates (row, col) in range 1 .. board_size.
    
    """
    s = point_str.lower()
    col_c = s[0]
    col = ord(col_c) - ord("a")
    if col_c < "i":
        col += 1
    row = int(s[1:])
        
    return row, col

def color_to_int(c: str) -> int:
    """convert character to the appropriate integer code"""
    color_to_int = {"b": BLACK, "w": WHITE, "e": EMPTY, "BORDER": BORDER}
    return color_to_int[c]


def int_to_color(i: int) -> str:
    """convert integer code to the appropriate color"""
    int_to_color = {BLACK: "black", WHITE: "white", EMPTY: "e", BORDER: "BORDER"}
    return int_to_color[i]
