# main.py
import sys
import cv2
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QComboBox, QPushButton, QLabel, QSpinBox,
                             QSizePolicy, QDialog)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QImage, QPixmap, QFont
from PyQt6.QtMultimedia import QSoundEffect

from pose_detector import PoseDetector
from exercise_analyzer import ExerciseAnalyzer

class ErrorReviewDialog(QDialog):
    """
    Una finestra di dialogo per rivedere le schermate degli errori catturate
    durante l'esercizio, con il feedback testuale associato.
    """
    def __init__(self, error_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Revisione Errori di Postura')
        self.error_data = error_data
        self.current_index = 0
        
        self.setMinimumSize(800, 700)
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        self.image_label = QLabel("Nessuna immagine da mostrare.")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: black; border-radius: 8px;")
        layout.addWidget(self.image_label, 1)

        self.feedback_display_label = QLabel("")
        self.feedback_display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feedback_display_label.setWordWrap(True)
        self.feedback_display_label.setStyleSheet("""
            font-size: 18px; color: #c0392b; font-weight: bold; 
            background-color: #f2f2f2; border: 1px solid #e0e0e0;
            border-radius: 8px; padding: 10px;
        """)
        layout.addWidget(self.feedback_display_label)

        control_layout = QHBoxLayout()
        self.prev_button = QPushButton("<< Precedente")
        self.prev_button.clicked.connect(self.show_prev_image)
        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.next_button = QPushButton("Successivo >>")
        self.next_button.clicked.connect(self.show_next_image)
        control_layout.addWidget(self.prev_button)
        control_layout.addStretch()
        control_layout.addWidget(self.info_label)
        control_layout.addStretch()
        control_layout.addWidget(self.next_button)
        layout.addLayout(control_layout)

        self.close_button = QPushButton("Chiudi")
        self.close_button.clicked.connect(self.accept)
        layout.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.update_view()

    def update_view(self):
        if not self.error_data: return
        pixmap, feedback_text = self.error_data[self.current_index]
        scaled_pixmap = pixmap.scaled(self.image_label.size(), 
                                      Qt.AspectRatioMode.KeepAspectRatio, 
                                      Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        self.feedback_display_label.setText(feedback_text)
        self.info_label.setText(f"Errore {self.current_index + 1} di {len(self.error_data)}")
        self.prev_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < len(self.error_data) - 1)

    def show_prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_view()

    def show_next_image(self):
        if self.current_index < len(self.error_data) - 1:
            self.current_index += 1
            self.update_view()
            
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_view()

class FitnessCoachApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Fitness Coach AR')
        self.setGeometry(50, 50, 1600, 900)

        self.pose_detector = PoseDetector()
        self.ex_analyzer = ExerciseAnalyzer()
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.last_rep = 0
        self.target_reps = 0

        self.start_sound_played = False
        self.target_sound_played = False
        self.error_sound_played = False

        self.one_rep_sound = self.load_sound("sounds/oneRep.wav")
        self.start_sound = self.load_sound("sounds/start.wav")
        self.target_reached_sound = self.load_sound("sounds/obbiettivo.wav")
        self.form_error_sound = self.load_sound("sounds/redflag.wav")

        self.countdown_timer = None
        self.countdown_value = 0
        self.exercise_started = False
        
        self.error_screenshots = []
        
        # NUOVA LOGICA: Cooldown per la cattura degli errori
        self.is_on_error_cooldown = False
        self.error_cooldown_timer = QTimer(self)
        self.error_cooldown_timer.setSingleShot(True)
        self.error_cooldown_timer.timeout.connect(self.end_error_cooldown)
        self.COOLDOWN_DURATION_MS = 5000  # 5 secondi

        self.setup_ui()
        self.update_feedback_and_reps()

    # NUOVO METODO per terminare il cooldown
    def end_error_cooldown(self):
        self.is_on_error_cooldown = False

    def load_sound(self, file_path):
        sound_effect = QSoundEffect(self)
        qurl_sound = QUrl.fromLocalFile(file_path)
        if not qurl_sound.isValid() or qurl_sound.isEmpty():
            print(f"Errore: File audio non trovato o percorso non valido: {file_path}")
            return None
        sound_effect.setSource(qurl_sound)
        sound_effect.setVolume(0.8)
        return sound_effect

    def setup_ui(self):
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #DFDFDF;")
        self.setCentralWidget(central_widget)

        v_main_layout = QVBoxLayout(central_widget)
        v_main_layout.setContentsMargins(10, 10, 10, 10)
        v_main_layout.setSpacing(10)

        top_container_widget = QWidget()
        h_top_layout = QHBoxLayout(top_container_widget)
        h_top_layout.setContentsMargins(0,0,0,0)
        h_top_layout.setSpacing(10)

        self.left_panel = QWidget()
        self.left_panel.setStyleSheet("""
            QWidget { background-color: white; border-radius: 10px; padding: 15px; }
            QLabel { color: #2c3e50; font-weight: bold; margin-bottom: 5px; font-family: "Segoe UI", sans-serif; }
            QComboBox { padding: 10px; border: 1px solid #e0e0e0; border-radius: 5px; background-color: white; min-width: 200px; margin-bottom: 10px; font-family: "Segoe UI", sans-serif;}
            QComboBox:hover { border-color: #3498db; }
            QSpinBox { padding: 8px; border: 1px solid #e0e0e0; border-radius: 5px; font-family: "Segoe UI", sans-serif; font-size: 14px; min-width: 200px;}
            QSpinBox:hover { border-color: #3498db; }
            QPushButton { background-color: #3498db; color: white; border: none; padding: 12px 20px; border-radius: 5px; font-weight: bold; min-width: 200px; margin: 8px 0; font-family: "Segoe UI", sans-serif;}
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:pressed { background-color: #2472a4; }
        """)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0,0,0,0)

        exercise_label_title = QLabel('SELEZIONA ESERCIZIO')
        exercise_label_title.setStyleSheet('font-size: 16px; color: #2c3e50; margin-bottom: 8px;')
        left_layout.addWidget(exercise_label_title)

        self.exercise_selector = QComboBox()
        self.exercise_selector.addItems(['Squat', 'Lunge'])
        self.exercise_selector.setStyleSheet('font-size: 14px;')
        left_layout.addWidget(self.exercise_selector)

        target_reps_label = QLabel('RIPETIZIONI OBIETTIVO:')
        target_reps_label.setStyleSheet('font-size: 16px; margin-top: 15px;')
        left_layout.addWidget(target_reps_label)

        self.target_reps_input = QSpinBox()
        self.target_reps_input.setMinimum(0)
        self.target_reps_input.setMaximum(200)
        self.target_reps_input.setValue(10)
        left_layout.addWidget(self.target_reps_input)

        self.start_button = QPushButton('Inizia Allenamento')
        self.start_button.setStyleSheet('font-size: 15px; margin-top:15px;')
        self.start_button.clicked.connect(self.toggle_exercise)
        left_layout.addWidget(self.start_button)

        self.rep_label = QLabel('RIPETIZIONI: 0')
        self.rep_label.setStyleSheet('font-size: 26px; color: #e67e22; margin: 20px 0; font-weight: bold;')
        self.rep_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.rep_label)

        left_layout.addStretch()

        self.image_label = QLabel()
        self.image_label.setStyleSheet("background-color: #222; border-radius: 10px;")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        h_top_layout.addWidget(self.left_panel, 1)
        h_top_layout.addWidget(self.image_label, 3)

        self.feedback_label = QLabel('Pronto per iniziare!')
        feedback_font = QFont("Segoe UI", 32, QFont.Weight.Bold)
        self.feedback_label.setFont(feedback_font)
        self.feedback_label.setStyleSheet('''
            color: white;
            background-color: #34495e;
            padding: 20px;
            border-radius: 10px;
        ''')
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feedback_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        v_main_layout.addWidget(top_container_widget)
        v_main_layout.addWidget(self.feedback_label)

        v_main_layout.setStretchFactor(top_container_widget, 2)
        v_main_layout.setStretchFactor(self.feedback_label, 1)

    def toggle_exercise(self):
        if self.timer.isActive():
            self.stop_exercise()
        else:
            self.start_exercise()

    def start_exercise(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.update_feedback_and_reps(feedback_text='Errore: Webcam non disponibile.')
                self.cap = None
                return

        self.target_reps = self.target_reps_input.value()
        if self.target_reps == 0:
            initial_feedback = "Nessun obiettivo impostato. Fai del tuo meglio!\nIn attesa di stabilizzazione..."
        else:
            initial_feedback = f"Obiettivo: {self.target_reps} ripetizioni. Forza!\nIn attesa di stabilizzazione..."

        self.pose_detector = PoseDetector()
        self.ex_analyzer.reset_counter()
        self.last_rep = 0
        self.error_screenshots = []

        self.start_sound_played = False
        self.target_sound_played = False
        self.error_sound_played = False
        
        # MODIFICA: Assicurarsi che il cooldown sia disattivo all'inizio
        self.is_on_error_cooldown = False
        self.error_cooldown_timer.stop()

        self.update_feedback_and_reps(feedback_text=initial_feedback)
        self.start_button.setText('Termina Allenamento')
        self.exercise_selector.setEnabled(False)
        self.target_reps_input.setEnabled(False)

        self.countdown_value = 3
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.start(1000)
        self.update_feedback_and_reps(feedback_text=f'Preparati! {self.countdown_value}')
        self.start_button.setEnabled(False)
        self.exercise_started = False
        self.timer.start(33)

    def update_countdown(self):
        self.countdown_value -= 1
        if self.countdown_value > 0:
            self.update_feedback_and_reps(feedback_text=f'Preparati! {self.countdown_value}')
        elif self.countdown_value == 0:
             self.update_feedback_and_reps(feedback_text='VIA!')
        else:
            self.countdown_timer.stop()
            self.countdown_timer = None
            self.exercise_started = True
            self.update_feedback_and_reps(feedback_text='In attesa di stabilizzazione...')
            self.start_button.setEnabled(True)

    def stop_exercise(self):
        self.timer.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if self.pose_detector is not None:
            self.pose_detector.release()

        self.start_button.setText('Inizia Allenamento')
        self.exercise_selector.setEnabled(True)
        self.target_reps_input.setEnabled(True)
        self.exercise_started = False
        
        # MODIFICA: Ferma il timer di cooldown se è attivo
        self.error_cooldown_timer.stop()

        cleaned_image = QPixmap(self.image_label.size())
        cleaned_image.fill(Qt.GlobalColor.black)
        self.image_label.setPixmap(cleaned_image)

        final_message = 'Allenamento terminato. Imposta un nuovo obiettivo e riavvia!'
        self.update_feedback_and_reps(feedback_text=final_message)
        self.last_rep = 0
        
        if self.error_screenshots:
            error_dialog = ErrorReviewDialog(self.error_screenshots, self)
            error_dialog.exec()

    def update_feedback_and_reps(self, feedback_text=None, rep_count=None):
        form_feedback = feedback_text if feedback_text is not None else self.ex_analyzer.feedback
        actual_reps = rep_count if rep_count is not None else self.ex_analyzer.get_rep_count()

        self.rep_label.setText(f'RIPETIZIONI: {actual_reps}')
        motivational_text = ""
        target = self.target_reps

        if target > 0 and actual_reps >= target and not self.target_sound_played:
            motivational_text = f"\nCOMPLIMENTI! OBIETTIVO DI {target} RAGGIUNTO E SUPERATO! SEI GRANDE!"
            if self.target_reached_sound: self.target_reached_sound.play()
            self.target_sound_played = True
            self.feedback_label.setText(form_feedback + motivational_text)
            QApplication.processEvents()
            QTimer.singleShot(2000, self.stop_exercise)
            return

        if target > 0 and not self.target_sound_played:
            if actual_reps == target - 1 and target > 1: motivational_text = "\nQUESTA E' L'ULTIMA!"
            elif actual_reps == target - 2 and target > 2: motivational_text = "\nQUASI FATTO, SOLO DUE ANCORA!"
            elif actual_reps > 0 and actual_reps >= target * 0.75: motivational_text = f"\nCONTINUA COSÌ, SEI VICINISSIMO ({actual_reps}/{target})!"
            elif actual_reps > 0 and actual_reps >= target * 0.5: motivational_text = f"\nOTTIMO! PIÙ DI METÀ FATTO ({actual_reps}/{target})! VAI AVANTI COSÌ!"
            elif actual_reps > 0: motivational_text = f"\nBENE! Procedi verso {target} ({actual_reps}/{target})."
        
        final_feedback_display = form_feedback + motivational_text
        self.feedback_label.setText(final_feedback_display)

        if actual_reps > self.last_rep:
            if self.one_rep_sound: self.one_rep_sound.play()
            self.last_rep = actual_reps
            self.error_sound_played = False

    def update_frame(self):
        if not self.timer.isActive() or self.cap is None or not self.cap.isOpened(): return

        ret, frame = self.cap.read()
        if not ret or frame is None:
            self.update_feedback_and_reps(feedback_text='Errore: Nessun frame dalla webcam.')
            self.stop_exercise()
            return

        frame = cv2.flip(frame, 1)
        output_frame = frame.copy()

        if self.exercise_started:
            h, w, _ = frame.shape
            video_area_frame = frame[:, :int(w*0.8)]
            
            self.pose_detector.find_pose(video_area_frame)
            landmarks = self.pose_detector.find_position(video_area_frame)

            analysis_success = False
            current_form_feedback = self.ex_analyzer.feedback
            exercise_type = self.exercise_selector.currentText()

            if landmarks:
                try:
                    if exercise_type == 'Squat':
                        analysis_success, current_form_feedback = self.ex_analyzer.analyze_squat(landmarks)
                    elif exercise_type == 'Lunge':
                        analysis_success, current_form_feedback = self.ex_analyzer.analyze_lunge(landmarks)

                    # --- LOGICA DI CATTURA ERRORE CON COOLDOWN ---
                    # MODIFICATO: Aggiunto controllo per self.is_on_error_cooldown
                    if not analysis_success and self.ex_analyzer.landmarks_stable and not self.error_sound_played and not self.is_on_error_cooldown:
                        if self.form_error_sound: self.form_error_sound.play()
                        self.error_sound_played = True
                        
                        # NUOVO: Avvia il cooldown per evitare catture troppo ravvicinate
                        self.is_on_error_cooldown = True
                        self.error_cooldown_timer.start(self.COOLDOWN_DURATION_MS)
                        
                        rgb_image = cv2.cvtColor(output_frame, cv2.COLOR_BGR2RGB)
                        h_img, w_img, ch = rgb_image.shape
                        bytes_per_line = ch * w_img
                        qt_image = QImage(rgb_image.data, w_img, h_img, bytes_per_line, QImage.Format.Format_RGB888)
                        self.error_screenshots.append((QPixmap.fromImage(qt_image), current_form_feedback))
                    
                    elif analysis_success and self.error_sound_played:
                        self.error_sound_played = False

                except Exception as e:
                    current_form_feedback = f'Errore analisi: {str(e)}'
            else:
                _, visibility_feedback = self.ex_analyzer._handle_landmark_visibility_and_stability(landmarks, [])
                current_form_feedback = visibility_feedback

            self.update_feedback_and_reps(feedback_text=current_form_feedback)

            if exercise_type == 'Squat':
                output_frame = self.pose_detector.draw_squat_depth_widget(output_frame, self.ex_analyzer.squat_range_info)

            is_stable = self.ex_analyzer.landmarks_stable
            output_frame = self.pose_detector.draw_user_pose(output_frame, exercise_success=analysis_success if is_stable else None)
            
            if self.ex_analyzer.target_pose_landmarks:
                output_frame = self.pose_detector.draw_target_landmarks(output_frame, self.ex_analyzer.target_pose_landmarks)
        else:
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_to_display = str(self.countdown_value) if self.countdown_value > 0 else 'VIA!'
            text_size = 3
            (text_w, text_h), _ = cv2.getTextSize(text_to_display, font, text_size, 5)
            text_x = (frame.shape[1] - text_w) // 2
            text_y = (frame.shape[0] + text_h) // 2
            cv2.putText(output_frame, text_to_display, (text_x, text_y), font, text_size, (255, 255, 255), 5, cv2.LINE_AA)

        try:
            rgb_image = cv2.cvtColor(output_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Errore conversione/visualizzazione frame: {e}")

    def closeEvent(self, event):
        self.stop_exercise()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FitnessCoachApp()
    window.show()
    sys.exit(app.exec())