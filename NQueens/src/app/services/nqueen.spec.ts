import { TestBed } from '@angular/core/testing';

import { NqueenService } from './nqueen.service';

describe('Nqueen', () => {
  let service: NqueenService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(NqueenService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
