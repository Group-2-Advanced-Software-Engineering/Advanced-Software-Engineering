import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Chessboard } from './chessboard';

describe('Chessboard', () => {
  let component: Chessboard;
  let fixture: ComponentFixture<Chessboard>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [Chessboard],
    }).compileComponents();

    fixture = TestBed.createComponent(Chessboard);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
