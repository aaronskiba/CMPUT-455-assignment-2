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

"""
The GoBoard class implements a board and basic functions to play
moves, check the end of the game, and count the acore at the end.
The class also contains basic utility functions for writing a Go player.
For many more utility functions, see the GoBoardUtil class in board_util.py.

The board is stored as a one-dimensional array of GO_POINT in self.board.
See GoBoardUtil.coord_to_point for explanations of the array encoding.
"""
class GoBoard(object):

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
        for key in self.board_to_keys():
            self.tt[key] = color


    def get_tt_entry(self):
        """
        If stored in the transposition table, return the outcome (1 or 2) for the current board state, else return None.
        """
        return self.tt.get(self.get_board_value(self.get_twoD_board()))


    def get_board_value(self, board):
        # do math to board state such that the board state becomes a dict key
        arr = np.array(board)
        flat_arr = arr.flatten()

        return int(''.join(str(i) for i in flat_arr))


    #def board_to_max_key(self):
    def board_to_keys(self):
        
        #TODO: get_twoD_board already flips the board
        twoD_board = self.get_twoD_board()
        flipped_twoD_board = np.flipud(twoD_board)

        v1 = self.get_board_value(twoD_board)
        v2 = self.get_board_value(flipped_twoD_board)
        keys = [v1,v2]

        for board in [twoD_board,flipped_twoD_board]:
            for _ in range(3): # only three unique rotations possible
                board = np.rot90(board)
            v = self.get_board_value(board)
            keys.append(v)
        return keys


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


    # def is_legal_original(self, point: GO_POINT, color: GO_COLOR) -> bool:
    #     """
    #     Play a move of color on point
    #     Returns whether move was legal
    #     """
        
    #     assert is_black_white(color)
        
    #     if self.board[point] != EMPTY:
    #         return False
            
    #     opp_color = opponent(color)
    #     in_enemy_eye = self._is_surrounded(point, opp_color) # True if all surrounding stones are either BORDER or opponent(color)
    #     self.board[point] = color
    #     neighbors = self._neighbors(point)
        
    #     #check for capturing
    #     for nb in neighbors:
    #         # only check neighboring stones of opponent(color)
    #         if self.board[nb] == opp_color:
    #             captured = self._detect_and_process_capture(nb) # True if opponent(color) block has zero liberties
    #             if captured:
    #             #undo capturing move
    #                 self.board[point] = EMPTY
    #                 return False
                    
                    
    #     #check for suicide
    #     block = self._block_of(point)
    #     if not self._has_liberty(block):  
    #         # undo suicide move
    #         self.board[point] = EMPTY
    #         return False
        
    #     #self.current_player = opponent(color)
    #     # undo legal move
    #     self.board[point] = EMPTY
    #     return True


    def is_legal(self, point: GO_POINT, color: GO_COLOR) -> bool:
        """
        Check whether it is legal for color to play on point
        This method tries to play the move on a temporary copy of the board.
        This prevents the board from being modified by the move
        """

        self.board[point] = color

        empty_neighbors = set()
        same_neighbors = set()
        opponent_neighbors = set()

        for nb in self._neighbors(point):
            if self.get_color(nb) == color:
                same_neighbors.add(nb)
            elif self.get_color(nb) == opponent(color):
                opponent_neighbors.add(nb)
            elif self.get_color(nb) == EMPTY:
                empty_neighbors.add(nb)

        # if stone has zero liberties
        if not empty_neighbors:
            # if stone is surrounded by opponent stones
            if not same_neighbors:
                # move is either suicide or capture
                self.board[point] = EMPTY
                return False

            # else point is surrounded and has at least one neighbor that is own color
            # determine if block for own color has any liberties
            visited = set()
            for nb in same_neighbors:
                if nb not in visited:
                    is_liberty, visited = self.depth_first_liberty_search_simple(visited, nb, color)
                    # if we have found a liberty for the block
                    if is_liberty:
                        break # same_neighbors are part of same block and thus, they share this liberty
            # if entire block has no liberties
            if not is_liberty:
                self.board[point] = EMPTY
                return False

        if opponent_neighbors:
            # Check each neighboring opponent stone for capture
            liberty_set = set()
            for nb in opponent_neighbors: # opponent neighbors may belong to same or different block(s)
                # if nb belongs to a block that was already found to have a liberty
                if nb in liberty_set:
                    continue
                # see if block of nb has at least one liberty 
                is_liberty, visited = self.depth_first_liberty_search(set(), liberty_set, nb, opponent(color))
                if not is_liberty:
                    self.board[point] = EMPTY
                    return False
                # else a liberty was found for the block of this neighbor
                # Hence, all stones in visited belong to a block with at least one liberty
                liberty_set.update(visited)

        self.board[point] = EMPTY
        return True

    def depth_first_liberty_search_simple(self, visited: set, stone, color) -> bool:
        """
        Search stone and its associated block for at least one liberty using dfs.
        @return: True if at least one liberty exists, else False.
        """
        
        visited.add(stone)
        # neighbors = self._neighbors(stone)  #TODO: start by searching for EMPTY?
        # if EMPTY in neighbors:
        #     return True, visited
        for nb in self._neighbors(stone):
            if nb not in visited: # ignore previously visited stones
                if self.get_color(nb) == EMPTY:
                    return True, visited
                if self.get_color(nb) == color:
                    # see if this stone has at least one liberty
                    is_liberty, visited = self.depth_first_liberty_search_simple(visited, nb, color)
                    if is_liberty:
                        return True, visited
        return False, visited
        

    def depth_first_liberty_search(self, visited: set, liberty_set: set, stone, color) -> bool:
        """
        Search stone and its associated block for at least one liberty using dfs.
        @return: True if at least one liberty exists, else False.
        """
        if stone not in visited:
            visited.add(stone)
            for nb in self._neighbors(stone):
                if self.get_color(nb) == EMPTY:
                    return True, visited
                if self.get_color(nb) == color: # if nb is part of block
                    if nb in liberty_set:
                        return True, visited
                    # see if this stone has at least one liberty
                    is_liberty, visited = self.depth_first_liberty_search(visited, liberty_set, nb, color)
                    if is_liberty:
                        return True, visited
        return False, visited

           
    def get_empty_points(self) -> np.ndarray:
        """
        Return:
            The empty points on the board
        """
        return where1d(self.board == EMPTY)

    def is_empty(self, point) -> bool:
        """Return: where or not the specified point is empty"""
        return self.board[point] == EMPTY

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

    def get_twoD_board(self) -> np.ndarray:
        """
        Return: numpy array
        a two dimensional numpy array with the goboard.
        Shows stones and empty points as encoded in board_base.py.
        Result is not padded with BORDER points.
        Rows 1..size of goboard are copied into rows 0..size - 1 of board2d
        Then the board is flipped up-down to be consistent with the
        coordinate system in GoGui (row 1 at the bottom).
        """
        size: int = self.size
        board2d: np.ndarray[GO_POINT] = np.zeros((size, size), dtype=GO_POINT)
        for row in range(size):
            # get start square for this row
            start: int = self.row_start(row + 1)
            # set row elements of board2d as all specified elements in go_board.board
            board2d[row, :] = self.board[start : start + size]
        board2d = np.flipud(board2d)
        return board2d
