import sys
import os
import json
import requests
import hashlib
import sqlite3
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLineEdit, QTextEdit, QListWidget, QLabel, QStackedWidget, QFileDialog, 
                             QColorDialog, QFontDialog, QInputDialog, QMessageBox, QScrollArea, QSplitter,
                             QDialog, QDialogButtonBox, QTabWidget, QComboBox, QCheckBox)
from PyQt6.QtGui import QIcon, QColor, QFont, QPixmap, QTextCharFormat
from PyQt6.QtCore import Qt, QSize, QTimer

GEMINI_API_KEY = ""  # Replace with your actual API key
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"

class Theme:
    def __init__(self, name, background, sidebar, text, accent, button, button_text):
        self.name = name
        self.background = background
        self.sidebar = sidebar
        self.text = text
        self.accent = accent
        self.button = button
        self.button_text = button_text

class Themes:
    LIGHT = Theme("Light", "#FFFFFF", "#F0F0F0", "#333333", "#4A90E2", "#E0E0E0", "#333333")
    DARK = Theme("Dark", "#1E1E1E", "#252526", "#FFFFFF", "#007ACC", "#3C3C3C", "#FFFFFF")
    CUSTOM = Theme("Custom", "#FFFFFF", "#F0F0F0", "#333333", "#4A90E2", "#E0E0E0", "#333333")

class PasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Password")
        layout = QVBoxLayout(self)
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter password")
        layout.addWidget(self.password_input)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

class AtmostNotes(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Atmost Notes")
        self.setGeometry(100, 100, 1200, 800)
        self.current_user = None
        self.current_note_id = None
        self.current_theme = Themes.LIGHT
        self.ai_enabled = True
        
        self.init_db()
        self.init_ui()
        self.update_styles()
    
    def init_ui(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # Sidebar
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(250)
        sidebar_layout = QVBoxLayout()
        
        self.profile_pic = QLabel()
        self.profile_pic.setFixedSize(80, 80)
        self.profile_pic.setObjectName("profile_pic")
        
        self.username_label = QLabel("Not logged in")
        self.username_label.setObjectName("username_label")
        
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.login)
        login_btn.setObjectName("sidebar_button")
        
        register_btn = QPushButton("Register")
        register_btn.clicked.connect(self.register)
        register_btn.setObjectName("sidebar_button")
        
        new_note_btn = QPushButton("New Note")
        new_note_btn.clicked.connect(self.new_note)
        new_note_btn.setObjectName("sidebar_button")
        
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Search notes...")
        search_bar.textChanged.connect(self.search_notes)
        search_bar.setObjectName("search_bar")
        
        self.note_list = QListWidget()
        self.note_list.itemClicked.connect(self.load_note)
        self.note_list.setObjectName("note_list")
        
        options_btn = QPushButton("Options")
        options_btn.clicked.connect(self.show_options)
        options_btn.setObjectName("sidebar_button")
        
        sidebar_layout.addWidget(self.profile_pic, alignment=Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(self.username_label, alignment=Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(login_btn)
        sidebar_layout.addWidget(register_btn)
        sidebar_layout.addWidget(new_note_btn)
        sidebar_layout.addWidget(search_bar)
        sidebar_layout.addWidget(self.note_list)
        sidebar_layout.addWidget(options_btn)
        self.sidebar.setLayout(sidebar_layout)
        
        # Main content area
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        
        # Top bar
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout()
        
        toggle_sidebar_btn = QPushButton("≡")
        toggle_sidebar_btn.clicked.connect(self.toggle_sidebar)
        toggle_sidebar_btn.setObjectName("toggle_button")
        
        self.ai_toggle_btn = QPushButton("AI: ON")
        self.ai_toggle_btn.clicked.connect(self.toggle_ai)
        self.ai_toggle_btn.setObjectName("ai_toggle_button")
        
        top_bar_layout.addWidget(toggle_sidebar_btn)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.ai_toggle_btn)
        top_bar.setLayout(top_bar_layout)
        
        content_layout.addWidget(top_bar)
        
        self.content_stack = QStackedWidget()
        
        # Note editing page
        note_edit_widget = QSplitter(Qt.Orientation.Horizontal)
        
        note_area = QWidget()
        note_layout = QVBoxLayout()
        
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Note title")
        self.title_edit.setObjectName("title_edit")
        
        self.tag_edit = QLineEdit()
        self.tag_edit.setPlaceholderText("Tags (comma-separated)")
        self.tag_edit.setObjectName("tag_edit")
        
        formatting_layout = QHBoxLayout()
        bold_btn = QPushButton("B")
        bold_btn.clicked.connect(lambda: self.format_text("bold"))
        italic_btn = QPushButton("I")
        italic_btn.clicked.connect(lambda: self.format_text("italic"))
        underline_btn = QPushButton("U")
        underline_btn.clicked.connect(lambda: self.format_text("underline"))
        bullet_list_btn = QPushButton("•")
        bullet_list_btn.clicked.connect(self.toggle_bullet_list)
        numbered_list_btn = QPushButton("1.")
        numbered_list_btn.clicked.connect(self.toggle_numbered_list)
        
        formatting_layout.addWidget(bold_btn)
        formatting_layout.addWidget(italic_btn)
        formatting_layout.addWidget(underline_btn)
        formatting_layout.addWidget(bullet_list_btn)
        formatting_layout.addWidget(numbered_list_btn)
        
        self.content_edit = QTextEdit()
        self.content_edit.setObjectName("content_edit")
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_note)
        save_btn.setObjectName("save_button")
        
        note_layout.addWidget(self.title_edit)
        note_layout.addWidget(self.tag_edit)
        note_layout.addLayout(formatting_layout)
        note_layout.addWidget(self.content_edit)
        note_layout.addWidget(save_btn)
        note_area.setLayout(note_layout)
        
        # AI Assistant panel
        ai_panel = QTabWidget()
        ai_panel.setObjectName("ai_panel")
        
        # Chat tab
        chat_tab = QWidget()
        chat_layout = QVBoxLayout()
        
        self.ai_chat = QTextEdit()
        self.ai_chat.setReadOnly(True)
        self.ai_chat.setObjectName("ai_chat")
        
        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText("Chat with AI...")
        self.ai_input.returnPressed.connect(self.send_ai_message)
        self.ai_input.setObjectName("ai_input")
        
        chat_layout.addWidget(self.ai_chat)
        chat_layout.addWidget(self.ai_input)
        chat_tab.setLayout(chat_layout)
        
        # Summary tab
        summary_tab = QWidget()
        summary_layout = QVBoxLayout()
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setObjectName("summary_text")
        
        summarize_btn = QPushButton("Summarize Note")
        summarize_btn.clicked.connect(self.summarize_note)
        summarize_btn.setObjectName("ai_button")
        
        copy_summary_btn = QPushButton("Copy Summary")
        copy_summary_btn.clicked.connect(lambda: self.copy_text(self.summary_text))
        copy_summary_btn.setObjectName("ai_button")
        
        summary_layout.addWidget(self.summary_text)
        summary_layout.addWidget(summarize_btn)
        summary_layout.addWidget(copy_summary_btn)
        summary_tab.setLayout(summary_layout)
        
        # Suggestions tab
        suggestions_tab = QWidget()
        suggestions_layout = QVBoxLayout()
        
        self.suggestions_text = QTextEdit()
        self.suggestions_text.setReadOnly(True)
        self.suggestions_text.setObjectName("suggestions_text")
        
        suggest_btn = QPushButton("Get Suggestions")
        suggest_btn.clicked.connect(self.get_suggestions)
        suggest_btn.setObjectName("ai_button")
        
        copy_suggestions_btn = QPushButton("Copy Suggestions")
        copy_suggestions_btn.clicked.connect(lambda: self.copy_text(self.suggestions_text))
        copy_suggestions_btn.setObjectName("ai_button")
        
        suggestions_layout.addWidget(self.suggestions_text)
        suggestions_layout.addWidget(suggest_btn)
        suggestions_layout.addWidget(copy_suggestions_btn)
        suggestions_tab.setLayout(suggestions_layout)
        
        ai_panel.addTab(chat_tab, "Chat")
        ai_panel.addTab(summary_tab, "Summary")
        ai_panel.addTab(suggestions_tab, "Suggestions")
        
        note_edit_widget.addWidget(note_area)
        note_edit_widget.addWidget(ai_panel)
        note_edit_widget.setStretchFactor(0, 2)
        note_edit_widget.setStretchFactor(1, 1)
        
        self.content_stack.addWidget(note_edit_widget)
        
        # Options page
        options_widget = QScrollArea()
        options_content = QWidget()
        options_layout = QVBoxLayout()
        
        change_username_btn = QPushButton("Change Username")
        change_username_btn.clicked.connect(self.change_username)
        change_username_btn.setObjectName("options_button")
        
        change_password_btn = QPushButton("Change Password")
        change_password_btn.clicked.connect(self.change_password)
        change_password_btn.setObjectName("options_button")
        
        change_profile_pic_btn = QPushButton("Change Profile Picture")
        change_profile_pic_btn.clicked.connect(self.change_profile_pic)
        change_profile_pic_btn.setObjectName("options_button")
        
        theme_label = QLabel("Choose Theme:")
        theme_combo = QComboBox()
        theme_combo.addItems(["Light", "Dark", "Custom"])
        theme_combo.currentTextChanged.connect(self.change_theme)
        
        custom_theme_btn = QPushButton("Customize Theme")
        custom_theme_btn.clicked.connect(self.customize_theme)
        custom_theme_btn.setObjectName("options_button")
        
        change_font_btn = QPushButton("Change Font")
        change_font_btn.clicked.connect(self.change_font)
        change_font_btn.setObjectName("options_button")
        
        export_notes_btn = QPushButton("Export Notes")
        export_notes_btn.clicked.connect(self.export_notes)
        export_notes_btn.setObjectName("options_button")
        
        import_notes_btn = QPushButton("Import Notes")
        import_notes_btn.clicked.connect(self.import_notes)
        import_notes_btn.setObjectName("options_button")
        
        options_layout.addWidget(change_username_btn)
        options_layout.addWidget(change_password_btn)
        options_layout.addWidget(change_profile_pic_btn)
        options_layout.addWidget(theme_label)
        options_layout.addWidget(theme_combo)
        options_layout.addWidget(custom_theme_btn)
        options_layout.addWidget(change_font_btn)
        options_layout.addWidget(export_notes_btn)
        options_layout.addWidget(import_notes_btn)
        options_layout.addStretch()
        options_content.setLayout(options_layout)
        options_widget.setWidget(options_content)
        options_widget.setWidgetResizable(True)
        
        self.content_stack.addWidget(options_widget)
        
        content_layout.addWidget(self.content_stack)
        content_widget.setLayout(content_layout)
        
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(content_widget)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
    
    def init_db(self):
        self.conn = sqlite3.connect('atmostnotes.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                title TEXT,
                content TEXT,
                tags TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                password TEXT,
                profile_pic BLOB
            )
        ''')
        self.conn.commit()
    
    def toggle_sidebar(self):
        if self.sidebar.isVisible():
            self.sidebar.hide()
        else:
            self.sidebar.show()

    def toggle_ai(self):
        self.ai_enabled = not self.ai_enabled
        self.ai_toggle_btn.setText("AI: ON" if self.ai_enabled else "AI: OFF")
        self.update_ai_panel_visibility()

    def update_ai_panel_visibility(self):
        note_edit_widget = self.content_stack.widget(0)
        ai_panel = note_edit_widget.widget(1)
        ai_panel.setVisible(self.ai_enabled)

    def login(self):
        username, ok = QInputDialog.getText(self, "Login", "Enter your username:")
        if ok and username:
            self.cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = self.cursor.fetchone()
            if user:
                password, ok = QInputDialog.getText(self, "Login", "Enter your password:", QLineEdit.EchoMode.Password)
                if ok:
                    hashed_password = hashlib.sha256(password.encode()).hexdigest()
                    if hashed_password == user[2]:
                        self.current_user = user[0]
                        self.username_label.setText(username)
                        if user[3]:
                            pixmap = QPixmap()
                            pixmap.loadFromData(user[3])
                            self.profile_pic.setPixmap(pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                        self.update_note_list()
                    else:
                        QMessageBox.warning(self, "Login Failed", "Incorrect password.")
            else:
                QMessageBox.warning(self, "Login Failed", "User not found. Please register.")

    def register(self):
        username, ok = QInputDialog.getText(self, "Register", "Enter a username:")
        if ok and username:
            self.cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            if self.cursor.fetchone():
                QMessageBox.warning(self, "Registration Failed", "Username already exists.")
            else:
                password_dialog = PasswordDialog(self)
                if password_dialog.exec():
                    password = password_dialog.password_input.text()
                    hashed_password = hashlib.sha256(password.encode()).hexdigest()
                    
                    # Profile picture upload
                    file_name, _ = QFileDialog.getOpenFileName(self, "Select Profile Picture", "", "Image Files (*.png *.jpg *.bmp)")
                    if file_name:
                        with open(file_name, "rb") as image_file:
                            image_data = image_file.read()
                    else:
                        image_data = None
                    
                    self.cursor.execute('INSERT INTO users (username, password, profile_pic) VALUES (?, ?, ?)', 
                                        (username, hashed_password, image_data))
                    self.conn.commit()
                    self.current_user = self.cursor.lastrowid
                    self.username_label.setText(username)
                    if image_data:
                        pixmap = QPixmap()
                        pixmap.loadFromData(image_data)
                        self.profile_pic.setPixmap(pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    self.update_note_list()
                    QMessageBox.information(self, "Registration Successful", "Your account has been created.")

    def new_note(self):
        if not self.current_user:
            QMessageBox.warning(self, "Not Logged In", "Please log in to create a note.")
            return
        self.title_edit.clear()
        self.tag_edit.clear()
        self.content_edit.clear()
        self.current_note_id = None
        self.content_stack.setCurrentIndex(0)

    def save_note(self):
        if not self.current_user:
            QMessageBox.warning(self, "Not Logged In", "Please log in to save a note.")
            return
        title = self.title_edit.text()
        content = self.content_edit.toHtml()
        tags = self.tag_edit.text()
        
        if self.current_note_id:
            self.cursor.execute('''
                UPDATE notes SET title = ?, content = ?, tags = ?
                WHERE id = ? AND user_id = ?
            ''', (title, content, tags, self.current_note_id, self.current_user))
        else:
            self.cursor.execute('''
                INSERT INTO notes (user_id, title, content, tags)
                VALUES (?, ?, ?, ?)
            ''', (self.current_user, title, content, tags))
            self.current_note_id = self.cursor.lastrowid
        
        self.conn.commit()
        self.update_note_list()
        QMessageBox.information(self, "Success", "Note saved successfully.")

    def load_note(self, item):
        if not self.current_user:
            return
        title = item.text()
        self.cursor.execute('SELECT * FROM notes WHERE user_id = ? AND title = ?', (self.current_user, title))
        note = self.cursor.fetchone()
        
        if note:
            self.current_note_id = note[0]
            self.title_edit.setText(note[2])
            self.content_edit.setHtml(note[3])
            self.tag_edit.setText(note[4])
            self.content_stack.setCurrentIndex(0)

    def search_notes(self, query):
        if not self.current_user:
            return
        self.cursor.execute('''
            SELECT title FROM notes
            WHERE user_id = ? AND (title LIKE ? OR content LIKE ? OR tags LIKE ?)
        ''', (self.current_user, f'%{query}%', f'%{query}%', f'%{query}%'))
        results = self.cursor.fetchall()
        
        self.note_list.clear()
        for result in results:
            self.note_list.addItem(result[0])

    def update_note_list(self):
        if not self.current_user:
            self.note_list.clear()
            return
        self.cursor.execute('SELECT title FROM notes WHERE user_id = ?', (self.current_user,))
        notes = self.cursor.fetchall()
        
        self.note_list.clear()
        for note in notes:
            self.note_list.addItem(note[0])

    def show_options(self):
        self.content_stack.setCurrentIndex(1)

    def change_username(self):
        if not self.current_user:
            QMessageBox.warning(self, "Not Logged In", "Please log in to change username.")
            return
        new_username, ok = QInputDialog.getText(self, "Change Username", "Enter new username:")
        if ok and new_username:
            self.cursor.execute('UPDATE users SET username = ? WHERE id = ?', (new_username, self.current_user))
            self.conn.commit()
            self.username_label.setText(new_username)

    def change_password(self):
        if not self.current_user:
            QMessageBox.warning(self, "Not Logged In", "Please log in to change password.")
            return
        old_password, ok = QInputDialog.getText(self, "Change Password", "Enter current password:", QLineEdit.EchoMode.Password)
        if ok:
            self.cursor.execute('SELECT password FROM users WHERE id = ?', (self.current_user,))
            current_hashed_password = self.cursor.fetchone()[0]
            if hashlib.sha256(old_password.encode()).hexdigest() == current_hashed_password:
                new_password, ok = QInputDialog.getText(self, "Change Password", "Enter new password:", QLineEdit.EchoMode.Password)
                if ok:
                    confirm_password, ok = QInputDialog.getText(self, "Change Password", "Confirm new password:", QLineEdit.EchoMode.Password)
                    if ok and new_password == confirm_password:
                        hashed_new_password = hashlib.sha256(new_password.encode()).hexdigest()
                        self.cursor.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_new_password, self.current_user))
                        self.conn.commit()
                        QMessageBox.information(self, "Success", "Password changed successfully.")
                    else:
                        QMessageBox.warning(self, "Error", "Passwords do not match.")
            else:
                QMessageBox.warning(self, "Error", "Incorrect current password.")

    def change_profile_pic(self):
        if not self.current_user:
            QMessageBox.warning(self, "Not Logged In", "Please log in to change profile picture.")
            return
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Profile Picture", "", "Image Files (*.png *.jpg *.bmp)")
        if file_name:
            with open(file_name, "rb") as image_file:
                image_data = image_file.read()
            self.cursor.execute('UPDATE users SET profile_pic = ? WHERE id = ?', (image_data, self.current_user))
            self.conn.commit()
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            self.profile_pic.setPixmap(pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def change_theme(self, theme_name):
        if theme_name == "Light":
            self.current_theme = Themes.LIGHT
        elif theme_name == "Dark":
            self.current_theme = Themes.DARK
        elif theme_name == "Custom":
            self.current_theme = Themes.CUSTOM
        self.update_styles()

    def customize_theme(self):
        color_dialog = QColorDialog(self)
        custom_colors = {
            "Background": self.current_theme.background,
            "Sidebar": self.current_theme.sidebar,
            "Text": self.current_theme.text,
            "Accent": self.current_theme.accent,
            "Button": self.current_theme.button,
            "Button Text": self.current_theme.button_text
        }
        
        for name, color in custom_colors.items():
            new_color = color_dialog.getColor(QColor(color), self, f"Choose {name} Color")
            if new_color.isValid():
                custom_colors[name] = new_color.name()
        
        Themes.CUSTOM = Theme("Custom", custom_colors["Background"], custom_colors["Sidebar"],
                              custom_colors["Text"], custom_colors["Accent"], custom_colors["Button"],
                              custom_colors["Button Text"])
        self.current_theme = Themes.CUSTOM
        self.update_styles()

    def change_font(self):
        font, ok = QFontDialog.getFont()
        if ok:
            self.setFont(font)
            self.update_styles()

    def export_notes(self):
        if not self.current_user:
            QMessageBox.warning(self, "Not Logged In", "Please log in to export notes.")
            return
        directory = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if directory:
            self.cursor.execute('SELECT * FROM notes WHERE user_id = ?', (self.current_user,))
            notes = self.cursor.fetchall()
            for note in notes:
                with open(os.path.join(directory, f"{note[2]}.html"), "w", encoding="utf-8") as f:
                    f.write(note[3])
            QMessageBox.information(self, "Export Complete", "Notes exported successfully!")

    def import_notes(self):
        if not self.current_user:
            QMessageBox.warning(self, "Not Logged In", "Please log in to import notes.")
            return
        directory = QFileDialog.getExistingDirectory(self, "Select Import Directory")
        if directory:
            for filename in os.listdir(directory):
                if filename.endswith(".html"):
                    with open(os.path.join(directory, filename), "r", encoding="utf-8") as f:
                        content = f.read()
                        title = os.path.splitext(filename)[0]
                        self.cursor.execute('''
                            INSERT INTO notes (user_id, title, content, tags)
                            VALUES (?, ?, ?, ?)
                        ''', (self.current_user, title, content, ""))
            self.conn.commit()
            self.update_note_list()
            QMessageBox.information(self, "Import Complete", "Notes imported successfully!")

    def format_text(self, format_type):
        cursor = self.content_edit.textCursor()
        if format_type == "bold":
            if cursor.charFormat().fontWeight() == QFont.Weight.Bold:
                cursor.setCharFormat(QTextCharFormat())
            else:
                format = QTextCharFormat()
                format.setFontWeight(QFont.Weight.Bold)
                cursor.mergeCharFormat(format)
        elif format_type == "italic":
            format = QTextCharFormat()
            format.setFontItalic(not cursor.charFormat().fontItalic())
            cursor.mergeCharFormat(format)
        elif format_type == "underline":
            format = QTextCharFormat()
            format.setFontUnderline(not cursor.charFormat().fontUnderline())
            cursor.mergeCharFormat(format)
        self.content_edit.setTextCursor(cursor)

    def toggle_bullet_list(self):
        cursor = self.content_edit.textCursor()
        list_format = cursor.currentList()
        if list_format:
            cursor.beginEditBlock()
            for i in range(list_format.count()):
                cursor.setPosition(list_format.item(i).position())
                cursor.insertText(list_format.item(i).text())
            cursor.endEditBlock()
            self.content_edit.setTextCursor(cursor)
        else:
            list_format = QTextListFormat()
            list_format.setStyle(QTextListFormat.Style.ListDisc)
            cursor.createList(list_format)

    def toggle_numbered_list(self):
        cursor = self.content_edit.textCursor()
        list_format = cursor.currentList()
        if list_format:
            cursor.beginEditBlock()
            for i in range(list_format.count()):
                cursor.setPosition(list_format.item(i).position())
                cursor.insertText(list_format.item(i).text())
            cursor.endEditBlock()
            self.content_edit.setTextCursor(cursor)
        else:
            list_format = QTextListFormat()
            list_format.setStyle(QTextListFormat.Style.ListDecimal)
            cursor.createList(list_format)

    def send_ai_message(self):
        if not self.ai_enabled:
            return
        user_message = self.ai_input.text()
        self.ai_chat.append(f"You: {user_message}")
        self.ai_input.clear()

        # Get AI response
        ai_response = self.get_ai_response(user_message)
        self.ai_chat.append(f"AI: {ai_response}")

    def summarize_note(self):
        if not self.ai_enabled:
            return
        if not self.current_note_id:
            QMessageBox.warning(self, "No Note Selected", "Please select a note to summarize.")
            return
        
        note_content = self.content_edit.toPlainText()
        prompt = f"Please summarize the following note:\n\n{note_content}"
        summary = self.get_ai_response(prompt)
        self.summary_text.setPlainText(summary)

    def get_suggestions(self):
        if not self.ai_enabled:
            return
        if not self.current_note_id:
            QMessageBox.warning(self, "No Note Selected", "Please select a note to get suggestions.")
            return
        
        note_content = self.content_edit.toPlainText()
        prompt = f"Based on the following note, please provide suggestions for improvement or expansion:\n\n{note_content}"
        suggestions = self.get_ai_response(prompt)
        self.suggestions_text.setPlainText(suggestions)

    def get_ai_response(self, prompt):
        headers = {
            'Content-Type': 'application/json',
        }
        data = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        try:
            response = requests.post(f'{GEMINI_API_URL}?key={GEMINI_API_KEY}', headers=headers, json=data)
            response_json = response.json()
            ai_response = response_json['candidates'][0]['content']['parts'][0]['text']
            # Remove asterisks from the response
            cleaned_response = ai_response.replace('*', '')
            return cleaned_response
        except Exception as e:
            return f"Error: Unable to get AI response. {str(e)}"

    def copy_text(self, text_edit):
        text_edit.selectAll()
        text_edit.copy()
        cursor = text_edit.textCursor()
        cursor.clearSelection()
        text_edit.setTextCursor(cursor)
        QMessageBox.information(self, "Copied", "Text copied to clipboard.")

    def update_styles(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: {self.current_theme.background}; color: {self.current_theme.text}; }}
            QWidget#sidebar {{ background-color: {self.current_theme.sidebar}; border-right: 1px solid {self.current_theme.accent}; }}
            QPushButton {{ background-color: {self.current_theme.button}; color: {self.current_theme.button_text}; border: none; padding: 10px; margin: 5px; border-radius: 5px; }}
            QPushButton:hover {{ background-color: {self.current_theme.accent}; }}
            QLineEdit, QTextEdit {{ background-color: {self.current_theme.button}; color: {self.current_theme.text}; border: 1px solid {self.current_theme.accent}; border-radius: 5px; padding: 5px; }}
            QLabel {{ color: {self.current_theme.text}; }}
            QLabel#username_label {{ font-weight: bold; font-size: 14px; }}
            QListWidget {{ background-color: {self.current_theme.button}; border: none; }}
            QListWidget::item {{ padding: 5px; border-bottom: 1px solid {self.current_theme.accent}; }}
            QListWidget::item:selected {{ background-color: {self.current_theme.accent}; color: {self.current_theme.button_text}; }}
            QPushButton#save_button, QPushButton#ai_button {{ background-color: {self.current_theme.accent}; color: {self.current_theme.button_text}; }}
            QTabWidget::pane {{ border: 1px solid {self.current_theme.accent}; }}
            QTabWidget::tab-bar {{ alignment: center; }}
            QTabBar::tab {{ background-color: {self.current_theme.button}; color: {self.current_theme.button_text}; padding: 8px; }}
            QTabBar::tab:selected {{ background-color: {self.current_theme.accent}; }}
            QScrollArea {{ border: none; }}
            QComboBox {{ background-color: {self.current_theme.button}; color: {self.current_theme.text}; border: 1px solid {self.current_theme.accent}; border-radius: 5px; padding: 5px; }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox::down-arrow {{ image: url(down_arrow.png); }}
            QComboBox QAbstractItemView {{ background-color: {self.current_theme.background}; color: {self.current_theme.text}; selection-background-color: {self.current_theme.accent}; }}
            QPushButton#toggle_button {{ background-color: transparent; color: {self.current_theme.text}; font-size: 24px; }}
            QPushButton#ai_toggle_button {{ background-color: {self.current_theme.accent}; color: {self.current_theme.button_text}; }}
        """)

    def closeEvent(self, event):
        self.conn.close()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AtmostNotes()
    window.show()
    sys.exit(app.exec())
