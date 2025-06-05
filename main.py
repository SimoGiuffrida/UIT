import sys
import cv2
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QComboBox, QPushButton, QLabel, QSpinBox,
                             QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QImage, QPixmap, QFont
from PyQt6.QtMultimedia import QSoundEffect

from pose_detector import PoseDetector
from exercise_analyzer import ExerciseAnalyzer

class FitnessCoachApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Fitness Coach AR - Nun Mollà Edition')
        self.setGeometry(50, 50, 1600, 900)

        self.pose_detector = PoseDetector()
        self.exercise_analyzer = ExerciseAnalyzer()
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.last_rep_count = 0
        self.current_target_reps = 0

        # --- Flag per la gestione dei suoni ---
        self.start_sound_played_since_last_unstable = False
        self.target_sound_played_this_session = False
        self.error_sound_played_for_this_error_instance = False
        # self.was_stable_on_previous_frame = False # Alternativa per start_sound, ma usiamo il feedback diretto

        # --- Caricamento Suoni ---
        self.one_rep_sound = self.load_sound("sounds/oneRep.wav")
        self.start_sound = self.load_sound("sounds/start.wav")
        self.target_reached_sound = self.load_sound("sounds/obbiettivo.wav") # Come da richiesta
        self.form_error_sound = self.load_sound("sounds/redflag.wav")

        self.setup_ui()
        self.update_feedback_and_reps()

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

        exercise_label_title = QLabel('SCEGLI ESERCIZIO')
        exercise_label_title.setStyleSheet('font-size: 16px; color: #2c3e50; margin-bottom: 8px;')
        left_layout.addWidget(exercise_label_title)

        self.exercise_selector = QComboBox()
        self.exercise_selector.addItems(['Squat', 'Affondo'])
        self.exercise_selector.setStyleSheet('font-size: 14px;')
        left_layout.addWidget(self.exercise_selector)

        target_reps_label = QLabel('OBIETTIVO RIPETIZIONI:')
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
        
        self.current_target_reps = self.target_reps_input.value()
        if self.current_target_reps == 0:
            initial_feedback = "Nessun obiettivo impostato. Fai del tuo meglio!\nAttendere stabilizzazione..."
        else:
            initial_feedback = f"Obiettivo: {self.current_target_reps} ripetizioni. DAJE!\nAttendere stabilizzazione..."

        self.pose_detector = PoseDetector()
        self.exercise_analyzer.reset_counter()
        self.last_rep_count = 0
        
        # Reset flag suoni
        self.start_sound_played_since_last_unstable = False
        self.target_sound_played_this_session = False
        self.error_sound_played_for_this_error_instance = False
        # self.was_stable_on_previous_frame = False

        self.update_feedback_and_reps(feedback_text=initial_feedback)
        
        self.start_button.setText('Termina Allenamento')
        self.exercise_selector.setEnabled(False)
        self.target_reps_input.setEnabled(False)
        self.timer.start(33)

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
        
        cleaned_image = QPixmap(self.image_label.size())
        cleaned_image.fill(Qt.GlobalColor.black)
        self.image_label.setPixmap(cleaned_image)
        
        self.update_feedback_and_reps(feedback_text='Allenamento terminato. Imposta un nuovo obiettivo e riparti!')
        self.last_rep_count = 0
        self.current_target_reps = 0

    def update_feedback_and_reps(self, feedback_text=None, rep_count=None):
        form_feedback = feedback_text if feedback_text is not None else self.exercise_analyzer.feedback
        actual_reps = rep_count if rep_count is not None else self.exercise_analyzer.get_rep_count()
        
        self.rep_label.setText(f'RIPETIZIONI: {actual_reps}')

        motivational_text = ""
        target = self.current_target_reps

        if target > 0:
            if actual_reps >= target:
                motivational_text = f"\nCOMPLIMENTI! OBIETTIVO DI {target} RAGGIUNTO E SUPERATO! SEI UN GRANDE!"
                if not self.target_sound_played_this_session:
                    if self.target_reached_sound:
                        self.target_reached_sound.play()
                    self.target_sound_played_this_session = True
            elif actual_reps == target - 1 and target > 1:
                motivational_text = "\nNUN MOLLA'! È L'ULTIMA!"
            elif actual_reps == target - 2 and target > 2:
                motivational_text = "\nNUN MOLLA'! QUASI FINITO, SOLO DUE!"
            elif actual_reps > 0 and actual_reps >= target * 0.75 :
                 motivational_text = f"\nFORZA, SEI VICINISSIMO ({actual_reps}/{target})!"
            elif actual_reps > 0 and actual_reps >= target * 0.5 :
                 motivational_text = f"\nOTTIMO! PIÙ DELLA METÀ ({actual_reps}/{target})! CONTINUA COSÌ!"
            elif actual_reps > 0 :
                 motivational_text = f"\nBENE! Procedi verso {target} ({actual_reps}/{target})."

        final_feedback_display = form_feedback
        if motivational_text:
            final_feedback_display += motivational_text
        
        self.feedback_label.setText(final_feedback_display)

        # Suono per ripetizione corretta (oneRep.wav)
        # Spostato qui perché last_rep_count deve essere aggiornato dopo il confronto
        if actual_reps > self.last_rep_count:
            if self.one_rep_sound:
                self.one_rep_sound.play()
            self.last_rep_count = actual_reps
            self.error_sound_played_for_this_error_instance = False # Reset error sound flag if rep is good


    def update_frame(self):
        if self.cap is None or not self.cap.isOpened():
            self.update_feedback_and_reps(feedback_text='Errore: Webcam persa.')
            self.stop_exercise()
            return

        ret, frame = self.cap.read()
        if not ret or frame is None:
            self.update_feedback_and_reps(feedback_text='Errore: No frame dalla webcam.')
            self.stop_exercise()
            return

        frame = cv2.flip(frame, 1)
        processed_frame_for_landmarks = self.pose_detector.find_pose(frame.copy(), draw=False)
        landmarks = self.pose_detector.find_position(processed_frame_for_landmarks)

        analysis_success = False
        current_form_feedback = self.exercise_analyzer.feedback # Prendi feedback base

        if landmarks and len(landmarks) > 0:
            exercise_type = self.exercise_selector.currentText()
            try:
                if exercise_type == 'Squat':
                    analysis_success, current_form_feedback = self.exercise_analyzer.analyze_squat(landmarks)
                elif exercise_type == 'Affondo':
                    analysis_success, current_form_feedback = self.exercise_analyzer.analyze_lunge(landmarks)
                
                # --- Logica Suoni Basata sull'Analisi ---

                # Suono per "stabile, puoi iniziare" (start.wav)
                if "Stabile. Puoi iniziare l'esercizio!" in current_form_feedback and \
                   not self.start_sound_played_since_last_unstable:
                    #if self.start_sound:
                    self.start_sound.play()
                    self.start_sound_played_since_last_unstable = True
                
                # Suono per forma errata (redflag.wav)
                if self.exercise_analyzer.landmarks_currently_visible_and_stable:
                    if not analysis_success: # Errore di forma
                        if not self.error_sound_played_for_this_error_instance:
                            if self.form_error_sound:
                                self.form_error_sound.play()
                            self.error_sound_played_for_this_error_instance = True
                    else: # Forma corretta
                        self.error_sound_played_for_this_error_instance = False
                else: # Landmark non stabili o non visibili
                    self.error_sound_played_for_this_error_instance = False
                    self.start_sound_played_since_last_unstable = False # Resetta anche flag suono start se si perde stabilità

                # L'aggiornamento del feedback testuale e del conteggio rep avviene qui
                self.update_feedback_and_reps(feedback_text=current_form_feedback)


            except Exception as e:
                current_form_feedback = f'Errore analisi: {str(e)}'
                print(f"Errore grave analisi esercizio: {e}")
                self.update_feedback_and_reps(feedback_text=current_form_feedback)
                analysis_success = False
        else:
            # Se non ci sono landmark, l'analyzer dovrebbe già fornire feedback
            if hasattr(self.exercise_analyzer, '_handle_landmark_visibility_and_stability'):
                 _, visibility_feedback = self.exercise_analyzer._handle_landmark_visibility_and_stability(landmarks, [])
                 current_form_feedback = visibility_feedback
            else:
                 current_form_feedback = "Nessun corpo rilevato. Posizionati correttamente."
            
            self.error_sound_played_for_this_error_instance = False # No error sound if no landmarks
            self.start_sound_played_since_last_unstable = False # Reset flag suono start se si perde visibilità
            self.update_feedback_and_reps(feedback_text=current_form_feedback)


        # Aggiorna self.was_stable_on_previous_frame per il prossimo frame (se usato)
        # self.was_stable_on_previous_frame = self.exercise_analyzer.landmarks_currently_visible_and_stable
        
        # Disegna il frame finale
        final_frame_to_draw = self.pose_detector.find_pose(frame, draw=True, exercise_success=analysis_success if self.exercise_analyzer.landmarks_currently_visible_and_stable else None)

        try:
            rgb_image = cv2.cvtColor(final_frame_to_draw, cv2.COLOR_BGR2RGB)
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