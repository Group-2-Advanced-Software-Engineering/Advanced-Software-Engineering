import { NgModule, provideBrowserGlobalErrorListeners, provideZonelessChangeDetection } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { BrowserModule } from '@angular/platform-browser';
import { DragDropModule } from '@angular/cdk/drag-drop';

import { AppRoutingModule } from './app-routing-module';
import { App } from './app';
import { Chessboard } from './components/chessboard/chessboard';

@NgModule({
  declarations: [
    App,
    Chessboard,
  ],
  imports: [
    BrowserModule,
    FormsModule,
    DragDropModule,
    AppRoutingModule
],
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection()
  ],
  bootstrap: [App]
})
export class AppModule { }
