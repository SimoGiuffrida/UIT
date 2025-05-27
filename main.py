import sys
import cv2
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QComboBox, QPushButton, QLabel)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from pose_detector import PoseDetector
from exercise_analyzer import ExerciseAnalyzer

class FitnessCoachApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Fitness Coach AR')
        self.setGeometry(100, 100, 1200, 800)

        # Inizializzazione componenti
        self.pose_detector = PoseDetector()
        self.exercise_analyzer = ExerciseAnalyzer()
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        # Widget principale
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)

        # Layout sinistro per controlli
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Selezione esercizio
        self.exercise_selector = QComboBox()
        self.exercise_selector.addItems(['Squat', 'Affondo'])
        left_layout.addWidget(QLabel('Seleziona Esercizio:'))
        left_layout.addWidget(self.exercise_selector)

        # Pulsanti
        self.start_button = QPushButton('Inizia Allenamento')
        self.start_button.clicked.connect(self.toggle_exercise)
        left_layout.addWidget(self.start_button)

        # Contatore ripetizioni
        self.rep_label = QLabel('Ripetizioni: 0')
        self.rep_label.setStyleSheet('font-size: 24px;')
        left_layout.addWidget(self.rep_label)

        # Feedback
        self.feedback_label = QLabel('Preparati all\'esercizio')
        self.feedback_label.setStyleSheet('font-size: 18px; color: blue;')
        self.feedback_label.setWordWrap(True)
        left_layout.addWidget(self.feedback_label)

        left_layout.addStretch()
        layout.addWidget(left_panel)

        # Display webcam
        self.image_label = QLabel()
        self.image_label.setMinimumSize(800, 600)
        layout.addWidget(self.image_label)

    def toggle_exercise(self):
        if self.timer.isActive():
            self.stop_exercise()
        else:
            self.start_exercise()

    def start_exercise(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.feedback_label.setText('Errore: Webcam non disponibile')
                return

        # Reinizializza il PoseDetector
        self.pose_detector = PoseDetector()
        self.exercise_analyzer.reset_counter()
        self.start_button.setText('Termina Allenamento')
        self.timer.start(30)  # ~30 FPS

    def stop_exercise(self):
        self.timer.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.pose_detector.release()
        self.start_button.setText('Inizia Allenamento')
        self.image_label.clear()

    def update_frame(self):
        try:
            if self.cap is None or not self.cap.isOpened():
                self.stop_exercise()
                self.feedback_label.setText('Errore: Webcam non disponibile')
                return

            ret, frame = self.cap.read()
            if not ret:
                self.stop_exercise()
                self.feedback_label.setText('Errore: Impossibile leggere il frame dalla webcam')
                return

            # Specchia l'immagine orizzontalmente
            frame = cv2.flip(frame, 1)

            # Visualizza la posa e ottieni il frame processato
            try:
                # Prima disegna la posa base
                frame = self.pose_detector.find_pose(frame, draw=False)
                
                # Poi trova i landmark per l'analisi
                landmarks = self.pose_detector.find_position(frame)
                success = None
                
                # Analizza l'esercizio se i landmark sono disponibili
                if landmarks and len(landmarks) > 0:
                    exercise = self.exercise_selector.currentText()
                    try:
                        if exercise == 'Squat':
                            success, feedback = self.exercise_analyzer.analyze_squat(landmarks)
                        else:  # Affondo
                            success, feedback = self.exercise_analyzer.analyze_lunge(landmarks)
                        
                        # Aggiorna le etichette di feedback
                        self.feedback_label.setText(feedback)
                        if success:  # Aggiorna il contatore solo se l'analisi ha avuto successo
                            self.rep_label.setText(f'Ripetizioni: {self.exercise_analyzer.get_rep_count()}')
                            
                        # Ridisegna la posa con il colore appropriato
                        frame = self.pose_detector.find_pose(frame, exercise_success=success)
                    except Exception as e:
                        self.feedback_label.setText('Errore durante l\'analisi dell\'esercizio')
                        return
                else:
                    self.feedback_label.setText('Non riesco a rilevare i punti chiave del corpo')
            except Exception as e:
                self.feedback_label.setText('Errore durante il rilevamento della posa')
                return


            # Converti il frame per Qt
            try:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                # Ridimensiona il frame mantenendo le proporzioni
                label_size = self.image_label.size()
                scaled_pixmap = pixmap.scaled(label_size.width(), label_size.height(),
                                            Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
                # Centra l'immagine nel QLabel
                self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            except Exception as e:
                self.feedback_label.setText('Errore durante la visualizzazione del frame')
                return

        except Exception as e:
            self.feedback_label.setText('Errore imprevisto durante l\'aggiornamento del frame')
            self.stop_exercise()

    def closeEvent(self, event):
        self.stop_exercise()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FitnessCoachApp()
    window.show()
    sys.exit(app.exec())