"""
board.py
board.py
Cmput 455 sample code
Written by Cmput 455 TA and Martin Mueller

Implements a basic Go board with functions to:
- initialize to a given board size
- check if a move is legal
- play a move

The board uses a 1-dimensional representation with padding
"""

import numpy as np
from typing import List, Tuple

from board_base import (
    board_array_size,
    coord_to_point,
    is_black_white,
    is_black_white_empty,
    opponent,
    where1d,
    BLACK,
    WHITE,
    EMPTY,
    BORDER,
    MAXSIZE,
    NO_POINT,
    GO_COLOR,
    GO_POINT,
)
from board_util import GoBoardUtil


"""
The GoBoard class implements a board and basic functions to play
moves, check the end of the game, and count the acore at the end.
The class also contains basic utility functions for writing a Go player.
For many more utility functions, see the GoBoardUtil class in board_util.py.

The board is stored as a one-dimensional array of GO_POINT in self.board.
See GoBoardUtil.coord_to_point for explanations of the array encoding.
"""
class GoBoard(object):

    LIBERTY_FOUND = False

    def __init__(self, size: int, tt: dict = {}):
        """
        Creates a Go board of given size
        """
        # assert 2 <= size <= MAXSIZE
        self.reset(size)
        self.tt = tt

    def set_tt_entry(self, color):
        """
        Adds a transposition table entry, based on the key and value provided
        """
        self.tt[self.board_to_key()] = color


    def get_tt_entry(self):
        """
        If stored in the transposition table, return the outcome (1 or 2) for the current board state, else return None.
        """

        return self.tt.get(self.board_to_key())


    def get_board_value(self):
        # do math to board state such that the board state becomes a dict key
        return


    def board_to_max_key(self):
        
        #TODO: get_twoD_board already flips the board
        twoD_board = GoBoardUtil.get_twoD_board(self.board)
        flipped_twoD_board = np.flipud(twoD_board)

        v1 = self.get_board_value(twoD_board)
        v2 = self.get_board_value(flipped_twoD_board)
        max = max(v1,v2)

        for board in [twoD_board,flipped_twoD_board]:
            for _ in range(3): # only three unique rotations possible
                board = np.rot90(board)
            v = self.get_board_value(board)
            max = np.max(max,v)
        return max
            

    def board_to_key(self):
        arr = where1d(self.board != BORDER)
        for i in range(len(arr)):
            arr[i] = self.get_color(arr[i])

        return int(''.join(str(i) for i in arr))


    def reset(self, size: int) -> None:
        """
        Creates a start state, an empty board with given size.
        """
        self.size: int = size
        self.NS: int = size + 1 # index for a board point above/below a current point (e.g. size=3, point=5 is directly above point=1 (1+3+1=5))
        self.WE: int = 1 # index for points to immediate left/right
        self.current_player: GO_COLOR = BLACK
        self.maxpoint: int = board_array_size(size)
        self.board: np.ndarray[GO_POINT] = np.full(self.maxpoint, BORDER, dtype=GO_POINT)
        self._initialize_empty_points(self.board)
        
        
    def copy(self) -> 'GoBoard':
        b = GoBoard(self.size)
        # assert b.NS == self.NS
        # assert b.WE == self.WE
        b.current_player = self.current_player
        # assert b.maxpoint == self.maxpoint
        b.board = np.copy(self.board)
        return b

        
    def get_color(self, point: GO_POINT) -> GO_COLOR:
        return self.board[point]

    def pt(self, row: int, col: int) -> GO_POINT:
        return coord_to_point(row, col, self.size)


    def is_legal_original(self, point: GO_POINT, color: GO_COLOR) -> bool:
        """
        Play a move of color on point
        Returns whether move was legal
        """
        
        assert is_black_white(color)
        
        if self.board[point] != EMPTY:
            return False
            
        opp_color = opponent(color)
        in_enemy_eye = self._is_surrounded(point, opp_color) # True if all surrounding stones are either BORDER or opponent(color)
        self.board[point] = color
        neighbors = self._neighbors(point)
        
        #check for capturing
        for nb in neighbors:
            # only check neighboring stones of opponent(color)
            if self.board[nb] == opp_color:
                captured = self._detect_and_process_capture(nb) # True if opponent(color) block has zero liberties
                if captured:
                #undo capturing move
                    self.board[point] = EMPTY
                    return False
                    
                    
        #check for suicide
        block = self._block_of(point)
        if not self._has_liberty(block):  
            # undo suicide move
            self.board[point] = EMPTY
            return False
        
        #self.current_player = opponent(color)
        # undo legal move
        self.board[point] = EMPTY
        return True


    def is_legal(self, point: GO_POINT, color: GO_COLOR) -> bool:
        """
        Check whether it is legal for color to play on point
        This method tries to play the move on a temporary copy of the board.
        This prevents the board from being modified by the move
        """

        assert(not self.LIBERTY_FOUND)

        # if point is occupied
        if self.board[point] != EMPTY:
            return False

        self.board[point] = color

        neighbors = self._neighbors(point)

        empty_neighbors = []
        same_neighbors = []
        enemy_neighbors = []

        for nb in neighbors:
            if self.get_color(nb) == color:
                same_neighbors.append(nb)
            elif self.get_color(nb) == opponent(color):
                enemy_neighbors.append(nb)
            elif self.get_color(nb) == EMPTY:
                empty_neighbors.append(nb)

        # if stone has zero liberties
        if not empty_neighbors:
            # if stone is surrounded by opponent stones
            if not same_neighbors:
                # move is either suicide or capture (false eye)
                self.board[point] = EMPTY
                return False

            # else point is surrounded and has at least one neighbor that is own color
            # determine if block for own color has any liberties
            self.depth_first_liberty_search([], point, color)

            # if no liberties
            if not self.LIBERTY_FOUND:
                self.board[point] = EMPTY
                return False
            # else a liberty was found
            self.LIBERTY_FOUND = False # reset for capture checking

        if enemy_neighbors:
            # Check each neighboring opponent stone for capture
            for nb in enemy_neighbors: # TODO: couldn't we have an appended list here as well for visited?
                # see if block associated with neighboring enemy stone still has any liberties. 
                self.depth_first_liberty_search([], nb, opponent(color))
                if not self.LIBERTY_FOUND:
                    self.board[point] = EMPTY
                    return False
                # else a liberty was found
                self.LIBERTY_FOUND = False

        # else move is legal
        self.LIBERTY_FOUND = False
        self.board[point] = EMPTY
        return True
        

    def depth_first_liberty_search(self, visited: list, stone, color) -> bool:
        """
        Search stone and its associated block for at least one liberty using dfs.
        @return: True if at least one liberty exists, else False.
        """
        if self.LIBERTY_FOUND: # end dfs
            return

        if stone not in visited:
            visited.append(stone)
            for nb in self._neighbors(stone):
                if self.get_color(nb) == EMPTY:
                    self.LIBERTY_FOUND = True # our liberty is found
                    return
                if self.get_color(nb) == color: # if nb is part of block
                    self.depth_first_liberty_search(visited, nb, color)

           
    def get_empty_points(self) -> np.ndarray:
        """
        Return:
            The empty points on the board
        """
        return where1d(self.board == EMPTY)

    def row_start(self, row: int) -> int:
        # assert row >= 1
        # assert row <= self.size
        return row * self.NS + 1
        
        
    def _initialize_empty_points(self, board_array: np.ndarray) -> None:
        """
        Fills points on the board with EMPTY
        Argument
        ---------
        board: numpy array, filled with BORDER
        """
        for row in range(1, self.size + 1):
            start: int = self.row_start(row)
            board_array[start : start + self.size] = EMPTY


    def is_eye(self, point: GO_POINT, color: GO_COLOR) -> bool:
        """
        Check if point is a simple eye for color
        """
        if not self._is_surrounded(point, color):
            return False
        # Eye-like shape. Check diagonals to detect false eye
        opp_color = opponent(color)
        false_count = 0
        at_edge = 0
        for d in self._diag_neighbors(point):
            if self.board[d] == BORDER:
                at_edge = 1
            elif self.board[d] == opp_color:
                false_count += 1
        return false_count <= 1 - at_edge  # 0 at edge, 1 in center
        
        
    def _is_surrounded(self, point: GO_POINT, color: GO_COLOR) -> bool:
        """
        check whether empty point is surrounded by stones of color
        (or BORDER) neighbors
        """
        for nb in self._neighbors(point):
            nb_color = self.board[nb]
            if nb_color != BORDER and nb_color != color:
                return False
        return True

    def _has_liberty(self, block: np.ndarray) -> bool:
        """
        Check if the given block has any liberty.
        block is a numpy boolean array
        """
        for stone in where1d(block):
            if self.find_neighbor_of_color(stone, EMPTY):
                return True
        return False
        
        
    def _block_of(self, stone: GO_POINT) -> np.ndarray:
        """
        Find the block of given stone
        Returns a board of boolean markers which are set for
        all the points in the block 
        """
        color: GO_COLOR = self.get_color(stone)
        # assert is_black_white(color)
        return self.connected_component(stone)

    def connected_component(self, point: GO_POINT) -> np.ndarray:
        """
        Find the connected component of the given point.
        """
        marker = np.full(self.maxpoint, False, dtype=np.bool_)
        pointstack = [point]
        color: GO_COLOR = self.get_color(point)
        # assert is_black_white_empty(color)
        marker[point] = True
        while pointstack:
            p = pointstack.pop()
            neighbors = self.neighbors_of_color(p, color)
            for nb in neighbors:
                if not marker[nb]:
                    marker[nb] = True
                    pointstack.append(nb)
        return marker
        
        
    def _detect_and_process_capture(self, nb_point: GO_POINT) -> GO_POINT:
        """
        Check whether opponent block on nb_point is captured.
        If yes, remove the stones.
        Returns the stone if only a single stone was captured,
        and returns NO_POINT otherwise.
        """
        opp_block = self._block_of(nb_point)
        return not self._has_liberty(opp_block)


    def undo_move(self, point: GO_POINT):
        self.board[point] = EMPTY


    def play_move(self, point: GO_POINT, color: GO_COLOR):
        """
        Play a move of color on point
        Returns whether move was legal
        """
        self.board[point] = color
        #self.current_player = opponent(color)


    def neighbors_of_color(self, point: GO_POINT, color: GO_COLOR) -> List:
        """ List of neighbors of point of given color """
        nbc: List[GO_POINT] = []
        for nb in self._neighbors(point):
            if self.get_color(nb) == color:
                nbc.append(nb)
        return nbc


    def _neighbors(self, point: GO_POINT) -> List:
        """ List of all four neighbors of the point """
        return [point - 1, point + 1, point - self.NS, point + self.NS]

    def _diag_neighbors(self, point: GO_POINT) -> List:
        """ List of all four diagonal neighbors of point """
        return [point - self.NS - 1,
                point - self.NS + 1,
                point + self.NS - 1,
                point + self.NS + 1]

    def last_board_moves(self) -> List:
        """
        Get the list of last_move and second last move.
        Only include moves on the board (not NO_POINT, not PASS).
        """
        board_moves: List[GO_POINT] = []
        return board_moves
