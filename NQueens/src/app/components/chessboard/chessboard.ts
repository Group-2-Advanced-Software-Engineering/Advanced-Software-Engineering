import { Component } from '@angular/core';
import { CdkDragDrop } from '@angular/cdk/drag-drop';
import { NqueenService } from '../../services/nqueen.service';

@Component({
  selector: 'app-chessboard',
  templateUrl: './chessboard.html',
  styleUrls: ['./chessboard.scss'],
  standalone: false,
})
export class Chessboard {
  nqueensInput = 0;
  inputValue = 1;
  currentBoard: number[][] = [];
  connectedDropLists: string[] = [];
  conflictCells = new Set<string>();
  feedback = '';
  allSolutions: number[][][] = [];
  solutionIndex = 0;
  firstMoveMade: boolean = false;

  constructor(private nqueenService: NqueenService) {}

  createEmptyBoard(): void {
    if (this.inputValue < 1) {
      this.feedback = 'Enter a valid board size';
      return;
    }

    this.currentBoard = Array.from({ length: this.nqueensInput }, () =>
      Array(this.nqueensInput).fill(0)
    );
    for (let r = 0; r < this.nqueensInput; r++) {
      this.currentBoard[r][0] = 1;
    }

    this.connectedDropLists = [];
    for (let r = 0; r < this.nqueensInput; r++) {
      for (let c = 0; c < this.nqueensInput; c++) {
        this.connectedDropLists.push(`cell-${r}-${c}`);
      }
    }

    this.feedback = this.inputValue > 1 ? 'Drag queens to try solving' : '';
    this.conflictCells.clear();
    this.allSolutions = [];
    this.solutionIndex = 0;
  }

  startBoard() {
    if (this.inputValue > 12) {
      this.feedback = 'Maximum allowed board size is 12';
      this.currentBoard = [];
      this.allSolutions = [];
      this.conflictCells.clear();
      this.solutionIndex = 0;
      return;
    }
    this.commitInput();
    this.createEmptyBoard();
  }

  showSolutions() {
    this.commitInput();
    this.showAllSolutions();
  }

  private commitInput() {
    if (this.inputValue > 12) {
      this.feedback = 'Maximum allowed board size is 12';
      return;
    }
    if (this.inputValue < 1) {
      this.inputValue = 1;
    }
    this.nqueensInput = this.inputValue;
  }

  onDrop(event: CdkDragDrop<any>) {
    const from = event.item.data;
    const to = event.container.data;
    if (!from || !to || (from.row === to.row && from.col === to.col)) return;
    this.currentBoard[from.row][from.col] = 0;
    this.currentBoard[to.row][to.col] = 1;
    this.firstMoveMade = true;
    this.detectConflicts();
  }

  detectConflicts(): void {
    this.conflictCells.clear();
    const queens: [number, number][] = [];

    for (let r = 0; r < this.nqueensInput; r++) {
      for (let c = 0; c < this.nqueensInput; c++) {
        if (this.currentBoard[r][c] === 1) queens.push([r, c]);
      }
    }

    for (let i = 0; i < queens.length; i++) {
      for (let j = i + 1; j < queens.length; j++) {
        const [r1, c1] = queens[i];
        const [r2, c2] = queens[j];
        if (r1 === r2 || c1 === c2 || Math.abs(r1 - r2) === Math.abs(c1 - c2)) {
          this.conflictCells.add(`${r1}-${c1}`);
          this.conflictCells.add(`${r2}-${c2}`);
        }
      }
    }

    this.feedback = this.conflictCells.size > 0 ? 'Conflict detected' : 'All queens are safe';
  }

  showAllSolutions() {
    this.commitInput();

    this.currentBoard = [];
    this.allSolutions = [];
    this.conflictCells.clear();
    this.solutionIndex = 0;

    if (this.inputValue > 12) {
      this.feedback = 'Maximum allowed board size is 12';
      return;
    }

    const rawSolutions = this.nqueenService.getQueens(this.nqueensInput);

    if (!rawSolutions || rawSolutions.length === 0) {
      this.feedback = `No solutions for board size ${this.nqueensInput}`;
      return;
    }

    this.allSolutions = rawSolutions.map((rowArray: number[]) => {
      const board = Array.from({ length: this.nqueensInput }, () =>
        Array(this.nqueensInput).fill(0)
      );
      rowArray.forEach((col: number, r: number) => {
        board[r][col - 1] = 1;
      });
      return board;
    });

    this.solutionIndex = 0;
    this.currentBoard = JSON.parse(JSON.stringify(this.allSolutions[0]));
    this.feedback = `Showing solution 1 of ${this.allSolutions.length}`;
  }

  prevSolution(): void {
    if (this.allSolutions.length === 0) return;
    this.solutionIndex =
      (this.solutionIndex - 1 + this.allSolutions.length) % this.allSolutions.length;
    this.currentBoard = JSON.parse(JSON.stringify(this.allSolutions[this.solutionIndex]));
    this.conflictCells.clear();
    this.feedback = `Showing solution ${this.solutionIndex + 1} of ${this.allSolutions.length}`;
  }

  nextSolution(): void {
    if (this.allSolutions.length === 0) return;
    this.solutionIndex = (this.solutionIndex + 1) % this.allSolutions.length;
    this.currentBoard = JSON.parse(JSON.stringify(this.allSolutions[this.solutionIndex]));
    this.conflictCells.clear();
    this.feedback = `Showing solution ${this.solutionIndex + 1} of ${this.allSolutions.length}`;
  }
}
