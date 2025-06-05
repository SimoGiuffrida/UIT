import sys
import cv2
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QComboBox, QPushButton, QLabel, QSpinBox,
                             QSizePolicy) # Aggiunto QSpinBox e QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QImage, QPixmap, QFont # Aggiunto QFont
from PyQt6.QtMultimedia import QSoundEffect

from pose_detector import PoseDetector
from exercise_analyzer import ExerciseAnalyzer

class FitnessCoachApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Fitness Coach AR - Nun Mollà Edition')
        # Impostiamo una dimensione iniziale, l'utente può ridimensionare
        self.setGeometry(50, 50, 1600, 900) # Dimensioni più grandi per il nuovo layout

        self.pose_detector = PoseDetector()
        self.exercise_analyzer = ExerciseAnalyzer()
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.last_rep_count = 0
        self.current_target_reps = 0 # Nuovo per memorizzare l'obiettivo

        self.rep_sound = QSoundEffect(self)
        sound_file_path = "sounds/rumore.wav"
        qurl_sound = QUrl.fromLocalFile(sound_file_path)
        if not qurl_sound.isValid() or qurl_sound.isEmpty():
            print(f"Errore: File audio non trovato o percorso non valido: {sound_file_path}")
            self.rep_sound = None
        else:
            self.rep_sound.setSource(qurl_sound)
            self.rep_sound.setVolume(0.8)

        self.setup_ui()
        self.update_feedback_and_reps()

    def setup_ui(self):
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #DFDFDF;") # Sfondo leggermente diverso per il widget centrale
        self.setCentralWidget(central_widget)

        # Layout Verticale Principale (VMainLayout)
        v_main_layout = QVBoxLayout(central_widget)
        v_main_layout.setContentsMargins(10, 10, 10, 10) # Margini ridotti
        v_main_layout.setSpacing(10)

        # --- Contenitore Superiore (TopContainerWidget) ---
        top_container_widget = QWidget()
        # top_container_widget.setStyleSheet("background-color: lightblue;") # Debug
        h_top_layout = QHBoxLayout(top_container_widget)
        h_top_layout.setContentsMargins(0,0,0,0)
        h_top_layout.setSpacing(10)

        # Pannello Sinistro (Controlli) - left_panel
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

        # --- NUOVO: Input Obiettivo Ripetizioni ---
        target_reps_label = QLabel('OBIETTIVO RIPETIZIONI:')
        target_reps_label.setStyleSheet('font-size: 16px; margin-top: 15px;')
        left_layout.addWidget(target_reps_label)

        self.target_reps_input = QSpinBox()
        self.target_reps_input.setMinimum(0) # 0 significa nessun obiettivo specifico
        self.target_reps_input.setMaximum(200)
        self.target_reps_input.setValue(10) # Valore di default
        left_layout.addWidget(self.target_reps_input)
        # --- FINE NUOVO ---

        self.start_button = QPushButton('Inizia Allenamento')
        self.start_button.setStyleSheet('font-size: 15px; margin-top:15px;')
        self.start_button.clicked.connect(self.toggle_exercise)
        left_layout.addWidget(self.start_button)

        self.rep_label = QLabel('RIPETIZIONI: 0')
        self.rep_label.setStyleSheet('font-size: 26px; color: #e67e22; margin: 20px 0; font-weight: bold;')
        self.rep_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.rep_label)
        
        left_layout.addStretch() # Spinge tutto in alto nel pannello sinistro
        
        # Pannello Destro (Webcam) - image_label
        self.image_label = QLabel()
        self.image_label.setStyleSheet("background-color: #222; border-radius: 10px;")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Imposta una politica di dimensione espandibile per la webcam
        self.image_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)


        h_top_layout.addWidget(self.left_panel, 1) # Peso 1 per il pannello controlli
        h_top_layout.addWidget(self.image_label, 3) # Peso 3 per la webcam (più grande)

        # --- Etichetta Feedback Inferiore ---
        self.feedback_label = QLabel('Pronto per iniziare!')
        # Aumenta significativamente la dimensione del font per il feedback
        feedback_font = QFont("Segoe UI", 32, QFont.Weight.Bold) # Esempio: 32pt Bold
        self.feedback_label.setFont(feedback_font)
        self.feedback_label.setStyleSheet('''
            color: white; 
            background-color: #34495e; /* Sfondo scuro per contrasto */
            padding: 20px; 
            border-radius: 10px; 
        ''')
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Imposta una politica di dimensione espandibile per il feedback
        self.feedback_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)


        # Aggiungi TopContainerWidget e FeedbackLabel al layout verticale principale
        v_main_layout.addWidget(top_container_widget)
        v_main_layout.addWidget(self.feedback_label)

        # Imposta i fattori di estensione per la divisione 2/3 altezza per top, 1/3 per bottom
        v_main_layout.setStretchFactor(top_container_widget, 2) # 2/3 dell'altezza
        v_main_layout.setStretchFactor(self.feedback_label, 1)   # 1/3 dell'altezza


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
        
        self.current_target_reps = self.target_reps_input.value() # Leggi l'obiettivo
        if self.current_target_reps == 0:
            initial_feedback = "Nessun obiettivo impostato. Fai del tuo meglio!\nAttendere stabilizzazione..."
        else:
            initial_feedback = f"Obiettivo: {self.current_target_reps} ripetizioni. DAJE!\nAttendere stabilizzazione..."

        self.pose_detector = PoseDetector()
        self.exercise_analyzer.reset_counter()
        self.last_rep_count = 0
        self.update_feedback_and_reps(feedback_text=initial_feedback)
        
        self.start_button.setText('Termina Allenamento')
        self.exercise_selector.setEnabled(False)
        self.target_reps_input.setEnabled(False) # Disabilita anche input obiettivo
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
        self.target_reps_input.setEnabled(True) # Riabilita input obiettivo
        
        cleaned_image = QPixmap(self.image_label.size()) # Crea un QPixmap delle dimensioni attuali
        cleaned_image.fill(Qt.GlobalColor.black) # Riempi di nero
        self.image_label.setPixmap(cleaned_image) # Sfondo scuro
        
        self.update_feedback_and_reps(feedback_text='Allenamento terminato. Imposta un nuovo obiettivo e riparti!')
        self.last_rep_count = 0
        self.current_target_reps = 0 # Resetta obiettivo interno

    def update_feedback_and_reps(self, feedback_text=None, rep_count=None):
        """Aggiorna il feedback testuale e il conteggio delle ripetizioni, includendo la motivazione."""
        
        form_feedback = feedback_text if feedback_text is not None else self.exercise_analyzer.feedback
        
        actual_reps = rep_count if rep_count is not None else self.exercise_analyzer.get_rep_count()
        self.rep_label.setText(f'RIPETIZIONI: {actual_reps}')

        motivational_text = ""
        target = self.current_target_reps

        if target > 0: # Solo se un obiettivo è impostato
            if actual_reps >= target:
                motivational_text = f"\nCOMPLIMENTI! OBIETTIVO DI {target} RAGGIUNTO E SUPERATO! SEI UN GRANDE!"
                # Qui potresti anche fermare l'esercizio automaticamente se vuoi
                # self.stop_exercise() # Opzionale
            elif actual_reps == target - 1 and target > 1: # Evita per target = 1
                motivational_text = "\nNUN MOLLA'! È L'ULTIMA!"
            elif actual_reps == target - 2 and target > 2:
                motivational_text = "\nNUN MOLLA'! QUASI FINITO, SOLO DUE!"
            elif actual_reps > 0 and actual_reps >= target * 0.75 : # Circa al 75%
                 motivational_text = f"\nFORZA, SEI VICINISSIMO ({actual_reps}/{target})!"
            elif actual_reps > 0 and actual_reps >= target * 0.5 : # Metà strada
                 motivational_text = f"\nOTTIMO! PIÙ DELLA METÀ ({actual_reps}/{target})! CONTINUA COSÌ!"
            elif actual_reps > 0 :
                 motivational_text = f"\nBENE! Procedi verso {target} ({actual_reps}/{target})."

        final_feedback_display = form_feedback
        if motivational_text:
            final_feedback_display += motivational_text
        
        self.feedback_label.setText(final_feedback_display)

        if actual_reps > self.last_rep_count:
            if self.rep_sound:
                self.rep_sound.play()
            self.last_rep_count = actual_reps

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
        current_form_feedback = self.exercise_analyzer.feedback # Prendi feedback base da analyzer

        if landmarks and len(landmarks) > 0:
            exercise_type = self.exercise_selector.currentText()
            try:
                if exercise_type == 'Squat':
                    analysis_success, current_form_feedback = self.exercise_analyzer.analyze_squat(landmarks)
                elif exercise_type == 'Affondo':
                    analysis_success, current_form_feedback = self.exercise_analyzer.analyze_lunge(landmarks)
                
                self.update_feedback_and_reps(feedback_text=current_form_feedback)

            except Exception as e:
                current_form_feedback = f'Errore analisi: {str(e)}'
                print(f"Errore grave analisi esercizio: {e}")
                self.update_feedback_and_reps(feedback_text=current_form_feedback)
                analysis_success = False
        else:
            # Se non ci sono landmark, l'analyzer dovrebbe già fornire feedback tipo "Visibilità persa"
            # tramite _handle_landmark_visibility_and_stability
            # Qui possiamo solo confermare di aggiornare la UI con quel feedback
            if hasattr(self.exercise_analyzer, '_handle_landmark_visibility_and_stability'):
                 _, visibility_feedback = self.exercise_analyzer._handle_landmark_visibility_and_stability(landmarks, []) # Passa empty required_points
                 current_form_feedback = visibility_feedback
            else:
                 current_form_feedback = "Nessun corpo rilevato. Posizionati correttamente."
            self.update_feedback_and_reps(feedback_text=current_form_feedback)


        final_frame_to_draw = self.pose_detector.find_pose(frame, draw=True, exercise_success=analysis_success if self.exercise_analyzer.landmarks_currently_visible_and_stable else None)

        try:
            rgb_image = cv2.cvtColor(final_frame_to_draw, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            pixmap = QPixmap.fromImage(qt_image)
            # Scala mantenendo le proporzioni per adattarsi al QLabel, che ora si espande
            scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)

        except Exception as e:
            print(f"Errore conversione/visualizzazione frame: {e}")
            # Non aggiornare feedback qui per non sovrascrivere quello dell'esercizio

    def closeEvent(self, event):
        self.stop_exercise()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FitnessCoachApp()
    window.show() # Mostra la finestra
    # window.showMaximized() # Opzionale: avvia massimizzato
    sys.exit(app.exec())