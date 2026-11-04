from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.application import Application


class DeckCard(QGroupBox):
    action_requested = Signal(str, str)
    lock_changed = Signal(str, bool)
    loop_changed = Signal(str, bool)

    def __init__(self, deck_id: str, title: str, parent=None) -> None:
        super().__init__(title, parent)
        self.deck_id = deck_id
        layout = QVBoxLayout(self)
        self.file_label = QLabel("No video loaded")
        self.file_label.setWordWrap(True)
        self.file_label.setMinimumWidth(130)
        self.state_label = QLabel("IDLE")
        self.state_label.setObjectName("mutedLabel")
        layout.addWidget(self.file_label)
        layout.addWidget(self.state_label)

        buttons = QHBoxLayout()
        play_button = QPushButton("PLAY")
        pause_button = QPushButton("PAUSE")
        stop_button = QPushButton("STOP")
        play_button.clicked.connect(lambda: self.action_requested.emit(deck_id, "play"))
        pause_button.clicked.connect(lambda: self.action_requested.emit(deck_id, "pause"))
        stop_button.clicked.connect(lambda: self.action_requested.emit(deck_id, "stop"))
        buttons.addWidget(play_button)
        buttons.addWidget(pause_button)
        buttons.addWidget(stop_button)
        layout.addLayout(buttons)

        options = QHBoxLayout()
        self.loop_checkbox = QCheckBox("Loop")
        self.loop_checkbox.setChecked(True)
        self.loop_checkbox.toggled.connect(
            lambda checked: self.loop_changed.emit(deck_id, checked)
        )
        self.lock_checkbox = QCheckBox("Lock")
        self.lock_checkbox.toggled.connect(
            lambda checked: self.lock_changed.emit(deck_id, checked)
        )
        options.addWidget(self.loop_checkbox)
        options.addWidget(self.lock_checkbox)
        layout.addLayout(options)

    def update_state(
            self,
            path: str | None,
            playing: bool,
            error: str | None,
            loop: bool,
            locked: bool,
    ) -> None:
        self.file_label.setText(Path(path).name if path else "No video loaded")
        if error:
            state = f"ERROR · {error}"
        elif playing:
            state = "PLAYING"
        elif path:
            state = "PAUSED / READY"
        else:
            state = "IDLE"
        self.state_label.setText(state)

        self.loop_checkbox.blockSignals(True)
        self.loop_checkbox.setChecked(loop)
        self.loop_checkbox.blockSignals(False)
        self.lock_checkbox.blockSignals(True)
        self.lock_checkbox.setChecked(locked)
        self.lock_checkbox.blockSignals(False)


class DeckPanel(QWidget):
    action_requested = Signal(str, str)
    lock_changed = Signal(str, bool)
    loop_changed = Signal(str, bool)

    def __init__(self, application: Application, parent=None) -> None:
        super().__init__(parent)
        self.application = application
        layout = QGridLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        self.cards: dict[str, DeckCard] = {}
        titles = {
            "deck_a": "VIDEO DECK A",
            "deck_b": "VIDEO DECK B",
            "deck_c": "VIDEO DECK C",
            "deck_d": "VIDEO DECK D",
        }
        for index, (deck_id, deck) in enumerate(application.decks.items()):
            card = DeckCard(deck_id, titles[deck_id])
            card.action_requested.connect(self.action_requested)
            card.lock_changed.connect(self._on_lock)
            card.loop_changed.connect(self.loop_changed)
            self.cards[deck_id] = card
            layout.addWidget(card, 0, index)
            card.lock_checkbox.setChecked(deck.locked)
            card.loop_checkbox.setChecked(deck.loop)
        self.refresh()

    def _on_lock(self, deck_id: str, locked: bool) -> None:
        self.application.decks[deck_id].locked = locked
        self.lock_changed.emit(deck_id, locked)

    def refresh(self) -> None:
        for deck_id, deck in self.application.decks.items():
            self.cards[deck_id].update_state(
                deck.path,
                deck.is_playing,
                deck.error,
                deck.loop,
                deck.locked,
            )
