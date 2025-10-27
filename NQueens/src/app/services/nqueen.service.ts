import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class NqueenService {
  results: any = [];
  mainDiagonal = new Set();
  antiDiagonal = new Set();
  rows: Array<number> = [];
  cols: Array<number> = [];

  getQueens(input: number): [] {
    this.results = [];
    this.rows = [];
    this.cols = [];
    this.mainDiagonal.clear();
    this.antiDiagonal.clear();

    this.placeQueens(0, input);

    return this.results;
  }

  placeQueens(row: number, input: number): void {
    if (row === input) {
      this.results.push([...this.rows.map((col) => col + 1)]);

      return;
    }

    for (let c: number = 0; c < input; c++) {
      if (
        this.cols.includes(c) ||
        this.mainDiagonal.has(row - c) ||
        this.antiDiagonal.has(row + c)
      ) {
        continue;
      }

      this.rows[row] = c;
      this.cols.push(c);
      this.mainDiagonal.add(row - c);
      this.antiDiagonal.add(row + c);

      this.placeQueens(row + 1, input);

      const colIndex = this.cols.indexOf(c);

      if (colIndex > -1) {
        this.cols.splice(colIndex, 1);
      }

      this.mainDiagonal.delete(row - c);
      this.antiDiagonal.delete(row + c);
    }
  }
}
