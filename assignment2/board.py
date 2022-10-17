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

from typing import List, Tuple

import numpy as np
from board_base import (BLACK, BORDER, EMPTY, GO_COLOR, GO_POINT, MAXSIZE,
                        NO_POINT, WHITE, board_array_size, coord_to_point,
                        is_black_white, is_black_white_empty, opponent,
                        where1d)

"""
The GoBoard class implements a board and basic functions to play
moves, check the end of the game, and count the acore at the end.
The class also contains basic utility functions for writing a Go player.
For many more utility functions, see the GoBoardUtil class in board_util.py.

The board is stored as a one-dimensional array of GO_POINT in self.board.
See GoBoardUtil.coord_to_point for explanations of the array encoding.
"""
class GoBoard(object):
    def __init__(self, size: int):
        """
        Creates a Go board of given size
        """
        assert 2 <= size <= MAXSIZE
        self.reset(size)

    def reset(self, size: int) -> None:
        """
        Creates a start state, an empty board with given size.
        """
        self.size: int = size
        self.NS: int = size + 1
        self.WE: int = 1
        self.current_player: GO_COLOR = BLACK
        self.maxpoint: int = board_array_size(size)
        self.board: np.ndarray[GO_POINT] = np.full(self.maxpoint, BORDER, dtype=GO_POINT)
        self._initialize_empty_points(self.board)
        self.non_border_neighbors: dict = self._initialize_non_border_neighbors_dict()
        self.non_border_points: list = list(self.non_border_neighbors.keys())
        self.tt_sub_arrays = self._initialize_tt_sub_arrays()
        self.tt = {}
        
        
    def copy(self) -> 'GoBoard':
        b = GoBoard(self.size)
        assert b.NS == self.NS
        assert b.WE == self.WE
        b.current_player = self.current_player
        assert b.maxpoint == self.maxpoint
        b.board = np.copy(self.board)
        return b
    

    def _initialize_tt_sub_arrays(self):
        arr1=[]
        arr2=[]
        for i in range(self.size):
            arr1.append(self.non_border_points[i*self.size:(i+1)*self.size])
            arr2.append(self.non_border_points[i::self.size])
        return [arr1,arr2]
    
    def get_tt_entry(self):
        """
        If stored in the transposition table, return the winner for the current board state, else return None.
        """    
        key = ""
        for point in self.non_border_points:
            key+=str(self.board[point])
        return self.tt.get(key)
    
    def set_tt_entry(self,color):
        """
        Generates and stores 8 versions (original + 3 rotations + mirror + 3
        mirror rotations) of the current board state in transposition table
        """
        key1=""
        key2=""
        key3=""
        key4=""
        for i in range(self.size):
            temp1=self.board[self.tt_sub_arrays[0][i]]
            temp1 =''.join(str(i) for i in temp1)
            temp2=self.board[self.tt_sub_arrays[1][i]]
            temp2=''.join(str(i) for i in temp2)
            key1+=temp1
            key2+=temp1[::-1]
            key3+=temp2
            key4+=temp2[::-1]

        self.tt[key1]=color
        self.tt[key2]=color
        self.tt[key3]=color
        self.tt[key4]=color
        self.tt[key1[::-1]]=color
        self.tt[key2[::-1]]=color
        self.tt[key3[::-1]]=color
        self.tt[key4[::-1]]=color

        
    def get_color(self, point: GO_POINT) -> GO_COLOR:
        return self.board[point]

    def pt(self, row: int, col: int) -> GO_POINT:
        return coord_to_point(row, col, self.size)
    
    def is_legal_new(self, point: GO_POINT, color: GO_COLOR) -> bool:
        """
        Check whether it is legal for color to play on point
        This method tries to play the move on a temporary copy of the board.
        This prevents the board from being modified by the move
        """
        
        opponent_color = 3-color
        self.board[point] = color

        # sort neighbors of point
        empty_neighbors = []
        current_player_neighbors = []
        opponent_neighbors = []
        for nb in self.non_border_neighbors[point]:
            if self.board[nb] == color:
                current_player_neighbors.append(nb)
            elif self.board[nb] == opponent_color:
                opponent_neighbors.append(nb)
            else: #self.board[nb] == EMPTY
                empty_neighbors.append(nb)

        # if stone has zero liberties
        if not empty_neighbors:
            # if stone is surrounded by opponent stones
            if not current_player_neighbors:
                # move is either suicide or capture
                self.board[point] = EMPTY
                return False
   
            # else point is surrounded and has >=1 neighbor that is own color
            # determine if block for own color has any liberties
            visited = set()
            liberty_found = False # flag for identifying if block including point has at least one liberty
            while current_player_neighbors and not liberty_found:
                p1 = current_player_neighbors.pop()
                visited.add(p1)
                for nb in self.non_border_neighbors[p1]:
                    if nb in visited:
                        continue
                    if self.board[nb] == EMPTY:
                        liberty_found = True
                        break
                    if self.board[nb] == color:
                        current_player_neighbors.append(nb)

            if not liberty_found:
                self.board[point] = EMPTY
                return False
          
        if opponent_neighbors:
            # for suicide, we only had to check for at least one liberty within the block containing point.
            # for capture, we have to check for at least one liberty FOR EACH opponent_neighbor
                # NOTE: Some opponent neighbors may belong to the same block
            liberty_set = set()
            for p2 in opponent_neighbors: # opponent neighbors may belong to same or different block(s)
                # if nb belongs to a block that was already found to have a liberty
                if p2 in liberty_set:
                    liberty_found = True
                    continue
                # else we need to determine if the block containing this point has a liberty
                liberty_found = False
                stack = [p2]
                visited = set()
                while stack and not liberty_found:
                    p2 = stack.pop()
                    visited.add(p2)
                    for nb in self.non_border_neighbors[p2]:
                        if nb in visited:
                            continue
                        if self.board[nb] == EMPTY:
                            liberty_found = True
                            liberty_set.update(set(visited)) # visited has at least one liberty (Thus, neighboring points of same color have a liberty too)
                            break
                        if self.board[nb] == opponent_color:
                            if nb in liberty_set:
                                liberty_found = True
                                break
                            # else determine if block including non-visited opponent stone has a liberty
                            stack.append(nb)

                if not liberty_found: # True if block containing p2 has no liberties
                    self.board[point] = EMPTY
                    return False
        # else move is legal
        self.board[point] = EMPTY
        return True

        
    def is_legal(self, point: GO_POINT, color: GO_COLOR) -> bool:
        """
        Check whether it is legal for color to play on point
        This method tries to play the move on a temporary copy of the board.
        This prevents the board from being modified by the move
        """
        board_copy: GoBoard = self.copy()
        can_play_move = board_copy.play_move(point, color)
        return can_play_move

        
           
    def get_empty_points(self) -> np.ndarray:
        """
        Return:
            The empty points on the board
        """
        return where1d(self.board == EMPTY)

    def row_start(self, row: int) -> int:
        assert row >= 1
        assert row <= self.size
        return row * self.NS + 1
    
    def _initialize_non_border_neighbors_dict(self):
        """
        Creates and returns a dict whose keys are non-BORDER points
        and values are a list of non-BORDER neighbors for each key/point
        ---------
        board: numpy array, filled with BORDER
        """
        dict = {}
        for point in range(self.maxpoint):
            # only get non-border points
            if self.board[point] != EMPTY:
                continue
            arr = []
            neighbors = self._neighbors(point)
            for nb in neighbors:
                # only add non-border neighbors
                if self.board[nb] == EMPTY:
                    arr.append(nb)
                dict[point] = arr
        return dict
        
        
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
            empty_nbs = self.neighbors_of_color(stone, EMPTY)
            if empty_nbs:
                return True
        return False
        
        
    def _block_of(self, stone: GO_POINT) -> np.ndarray:
        """
        Find the block of given stone
        Returns a board of boolean markers which are set for
        all the points in the block 
        """
        color: GO_COLOR = self.get_color(stone)
        assert is_black_white(color)
        return self.connected_component(stone)

    def connected_component(self, point: GO_POINT) -> np.ndarray:
        """
        Find the connected component of the given point.
        """
        marker = np.full(self.maxpoint, False, dtype=np.bool_)
        pointstack = [point]
        color: GO_COLOR = self.get_color(point)
        assert is_black_white_empty(color)
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
    
    def play_move_new(self, point: GO_POINT, color: GO_COLOR) -> bool:
        """
        Play a move of color on point
        """
        self.board[point] = color

    def play_move(self, point: GO_POINT, color: GO_COLOR) -> bool:
        """
        Play a move of color on point
        Returns whether move was legal
        """
        
        assert is_black_white(color)
        
        if self.board[point] != EMPTY:
            return False
            
        opp_color = opponent(color)
        in_enemy_eye = self._is_surrounded(point, opp_color)
        self.board[point] = color
        neighbors = self._neighbors(point)
        
        #check for capturing
        for nb in neighbors:
            if self.board[nb] == opp_color:
                captured = self._detect_and_process_capture(nb)
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
        
        self.current_player = opponent(color)
        return True
    

    def undo_move(self, point: GO_POINT):
        self.board[point] = EMPTY

        
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
