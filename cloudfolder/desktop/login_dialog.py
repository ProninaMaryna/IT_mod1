"""Вікно входу / реєстрації."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from .api_client import ApiClient, ApiError


class LoginDialog(QDialog):
    def __init__(self, server_url: str = "http://127.0.0.1:8000", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Хмарне сховище — вхід")
        self.setMinimumWidth(420)
        self.client: ApiClient | None = None

        title = QLabel("<h2>Хмарне сховище</h2><p>Увійдіть до свого особистого простору</p>")
        title.setAlignment(Qt.AlignCenter)

        self.server = QLineEdit(server_url)
        self.username = QLineEdit()
        self.username.setPlaceholderText("логін")
        self.password = QLineEdit()
        self.password.setPlaceholderText("пароль (мін. 6 символів)")
        self.password.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow("Сервер:", self.server)
        form.addRow("Логін:", self.username)
        form.addRow("Пароль:", self.password)

        self.error = QLabel()
        self.error.setStyleSheet("color: #c0392b")
        self.error.setWordWrap(True)

        self.login_btn = QPushButton("Увійти")
        self.login_btn.setDefault(True)
        self.register_btn = QPushButton("Зареєструватися")
        self.login_btn.clicked.connect(lambda: self._submit(register=False))
        self.register_btn.clicked.connect(lambda: self._submit(register=True))

        buttons = QHBoxLayout()
        buttons.addWidget(self.register_btn)
        buttons.addStretch()
        buttons.addWidget(self.login_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addWidget(self.error)
        layout.addLayout(buttons)

    def _submit(self, register: bool) -> None:
        self.error.clear()
        client = ApiClient(self.server.text().strip() or "http://127.0.0.1:8000")
        try:
            if register:
                client.register(self.username.text(), self.password.text())
            else:
                client.login(self.username.text(), self.password.text())
        except ApiError as exc:
            self.error.setText(str(exc))
            return
        self.client = client
        self.accept()
