import sys
import cv2
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QComboBox, QPushButton, QLabel)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtMultimedia import QSoundEffect # QSoundEffect è per suoni brevi
# from PyQt6.QtMultimedia import QMediaPlayer # Per musica o suoni più lunghi

from pose_detector import PoseDetector
from exercise_analyzer import ExerciseAnalyzer

class FitnessCoachApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Fitness Coach AR')
        self.setGeometry(100, 100, 1280, 720) # Leggermente più grande per comodità

        self.pose_detector = PoseDetector()
        self.exercise_analyzer = ExerciseAnalyzer()
        self.cap = None
        self.timer = QTimer(self) # Specifica parent
        self.timer.timeout.connect(self.update_frame)
        self.last_rep_count = 0

        self.rep_sound = QSoundEffect(self) # Specifica parent
        # Assicurati che il percorso sia corretto rispetto a dove esegui lo script
        # o usa un percorso assoluto.
        sound_file_path = "sounds/rumore.wav" # Metti il file in una sottocartella "sounds"
        
        # Prova a caricare il suono e gestisci l'errore se non trovato
        qurl_sound = QUrl.fromLocalFile(sound_file_path)
        if not qurl_sound.isValid() or qurl_sound.isEmpty():
            print(f"Errore: File audio non trovato o percorso non valido: {sound_file_path}")
            print(f"URL tentato: {qurl_sound.toString()}")
            # Potresti usare un suono di sistema o disabilitare il suono
            self.rep_sound = None 
        else:
            self.rep_sound.setSource(qurl_sound)
            self.rep_sound.setVolume(0.8) # Volume da 0.0 a 1.0

        self.setup_ui()
        self.update_feedback_and_reps() # Imposta feedback iniziale

    def setup_ui(self):
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #f0f2f5;")
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Pannello Sinistro (Controlli)
        left_panel = QWidget()
        left_panel.setStyleSheet("""
            QWidget { background-color: white; border-radius: 10px; padding: 20px; }
            QLabel { color: #2c3e50; font-weight: bold; margin-bottom: 5px; font-family: "Segoe UI", sans-serif; }
            QComboBox { padding: 10px; border: 1px solid #e0e0e0; border-radius: 5px; background-color: white; min-width: 220px; margin-bottom: 15px; font-family: "Segoe UI", sans-serif;}
            QComboBox:hover { border-color: #3498db; }
            QPushButton { background-color: #3498db; color: white; border: none; padding: 12px 24px; border-radius: 5px; font-weight: bold; min-width: 220px; margin: 10px 0; font-family: "Segoe UI", sans-serif;}
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:pressed { background-color: #2472a4; }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0,0,0,0) # Rimuovi margini interni se padding è sul widget

        exercise_label_title = QLabel('SCEGLI ESERCIZIO')
        exercise_label_title.setStyleSheet('font-size: 18px; color: #2c3e50; margin-bottom: 10px;')
        left_layout.addWidget(exercise_label_title)

        self.exercise_selector = QComboBox()
        self.exercise_selector.addItems(['Squat', 'Affondo'])
        self.exercise_selector.setStyleSheet('font-size: 14px;')
        left_layout.addWidget(self.exercise_selector)

        self.start_button = QPushButton('Inizia Allenamento')
        self.start_button.setStyleSheet('font-size: 15px;')
        self.start_button.clicked.connect(self.toggle_exercise)
        left_layout.addWidget(self.start_button)

        self.rep_label = QLabel('RIPETIZIONI: 0')
        self.rep_label.setStyleSheet('font-size: 28px; color: #e67e22; margin: 25px 0; font-weight: bold;')
        self.rep_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.rep_label)
        
        feedback_title_label = QLabel("CONSIGLI:")
        feedback_title_label.setStyleSheet('font-size: 16px; color: #2c3e50; margin-top: 15px; margin-bottom: 0px;')
        left_layout.addWidget(feedback_title_label)

        self.feedback_label = QLabel('Pronto per iniziare!')
        self.feedback_label.setStyleSheet('''
            font-size: 20px; /* Aumentato da 15px a 20px */
            font-weight: bold; /* Aggiunto per maggiore leggibilità */
            color: #2980b9; 
            background-color: #eaf5ff; 
            padding: 15px; /* Leggermente aumentato per il testo più grande */
            border-radius: 8px; 
            margin-top: 5px; 
            min-height: 80px; /* Aumentato per accomodare più testo o testo più grande */
        ''')
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setAlignment(Qt.AlignmentFlag.AlignTop) # o Qt.AlignmentFlag.AlignCenter se preferisci
        left_layout.addWidget(self.feedback_label)

        left_layout.addStretch() # Spinge tutto in alto
        main_layout.addWidget(left_panel, 1) # Peso 1

        # Pannello Destro (Webcam)
        self.image_label = QLabel()
        self.image_label.setMinimumSize(800, 600)
        self.image_label.setStyleSheet("background-color: #333; border-radius: 10px; padding: 0px;") # Nero quando vuoto
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.image_label, 3) # Peso 3 (più grande)


    def toggle_exercise(self):
        if self.timer.isActive():
            self.stop_exercise()
        else:
            self.start_exercise()

    def start_exercise(self):
        if self.cap is None: # Inizializza solo se non già fatto o dopo release
            self.cap = cv2.VideoCapture(0) # Prova con API diverse se ci sono problemi: cv2.CAP_DSHOW
            if not self.cap.isOpened():
                self.update_feedback_and_reps(feedback_text='Errore: Webcam non disponibile o non accessibile.')
                self.cap = None # Resetta per permettere un nuovo tentativo
                return

        # Reinizializza detector e analyzer per un nuovo allenamento
        self.pose_detector = PoseDetector() # Ricrea per resettare stato interno di MediaPipe
        self.exercise_analyzer.reset_counter()
        self.last_rep_count = 0
        self.update_feedback_and_reps(feedback_text='Attendere stabilizzazione...') # Feedback iniziale
        
        self.start_button.setText('Termina Allenamento')
        self.exercise_selector.setEnabled(False) # Disabilita cambio esercizio durante l'esecuzione
        self.timer.start(33)  # Circa 30 FPS (1000ms / 30fps = ~33ms)

    def stop_exercise(self):
        self.timer.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        if self.pose_detector is not None:
            self.pose_detector.release() # Rilascia risorse MediaPipe
            # self.pose_detector = None # Non serve nullificarlo se lo ricrei in start_exercise

        self.start_button.setText('Inizia Allenamento')
        self.exercise_selector.setEnabled(True)
        self.image_label.clear() # Pulisce l'immagine
        self.image_label.setStyleSheet("background-color: #333; border-radius: 10px;") # Sfondo scuro
        self.update_feedback_and_reps(feedback_text='Allenamento terminato. Pronto per il prossimo!')
        self.last_rep_count = 0 # Resetta anche qui


    def update_feedback_and_reps(self, feedback_text=None, rep_count=None):
        if feedback_text is not None:
            self.feedback_label.setText(feedback_text)
        
        current_reps = rep_count if rep_count is not None else self.exercise_analyzer.get_rep_count()
        self.rep_label.setText(f'RIPETIZIONI: {current_reps}')

        if current_reps > self.last_rep_count:
            if self.rep_sound:
                self.rep_sound.play()
            self.last_rep_count = current_reps


    def update_frame(self):
        if self.cap is None or not self.cap.isOpened():
            self.update_feedback_and_reps(feedback_text='Errore: Connessione webcam persa.')
            self.stop_exercise() # Arresta l'esercizio se la webcam si disconnette
            return

        ret, frame = self.cap.read()
        if not ret or frame is None:
            self.update_feedback_and_reps(feedback_text='Errore: Impossibile leggere frame dalla webcam.')
            self.stop_exercise() # Arresta se non si possono leggere frame
            return

        frame = cv2.flip(frame, 1) # Specchia per effetto "specchio"

        # Processamento della posa e analisi esercizio
        processed_frame = self.pose_detector.find_pose(frame, draw=False) # Trova la posa ma non disegnarla ancora
        landmarks = self.pose_detector.find_position(processed_frame) # Ottieni i landmark dalla posa trovata

        analysis_success = False # Flag per il colore del bordo/landmark
        current_feedback = "Rilevamento in corso..." # Feedback di default

        if landmarks and len(landmarks) > 0:
            exercise_type = self.exercise_selector.currentText()
            try:
                if exercise_type == 'Squat':
                    analysis_success, current_feedback = self.exercise_analyzer.analyze_squat(landmarks)
                elif exercise_type == 'Affondo':
                    analysis_success, current_feedback = self.exercise_analyzer.analyze_lunge(landmarks)
                
                # Aggiorna UI con feedback e ripetizioni dall'analyzer
                self.update_feedback_and_reps(feedback_text=current_feedback)

            except Exception as e:
                current_feedback = f'Errore analisi: {str(e)}'
                print(f"Errore grave durante l'analisi dell'esercizio: {e}")
                self.update_feedback_and_reps(feedback_text=current_feedback)
                analysis_success = False # Errore nell'analisi è considerato 'non successo'
        else:
            # Questo feedback viene sovrascritto da _handle_landmark_visibility_and_stability
            # se i landmark sono parzialmente visibili o instabili.
            # Manteniamolo per il caso di nessun landmark rilevato.
            current_feedback = self.exercise_analyzer.feedback if self.exercise_analyzer.feedback else "Nessun corpo rilevato o troppo lontano."
            self.update_feedback_and_reps(feedback_text=current_feedback)
            # Se nessun landmark, resetta stato di stabilità nell'analyzer
            if hasattr(self.exercise_analyzer, '_handle_landmark_visibility_and_stability'):
                 # Simula una chiamata con landmark vuoti per triggerare la logica di instabilità
                 self.exercise_analyzer._handle_landmark_visibility_and_stability({}, [])


        # Ridisegna la posa sul frame originale con il colore corretto
        # Ora `analysis_success` riflette il successo della *forma* dell'esercizio se i landmark sono stabili
        # o `False` se i landmark non sono stabili/visibili (gestito in analyzer)
        final_frame_to_draw = self.pose_detector.find_pose(frame, draw=True, exercise_success=analysis_success if self.exercise_analyzer.landmarks_currently_visible_and_stable else None)

        # Conversione e visualizzazione frame
        try:
            rgb_image = cv2.cvtColor(final_frame_to_draw, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            pixmap = QPixmap.fromImage(qt_image)
            # Scala mantenendo le proporzioni per adattarsi al QLabel
            scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)

        except Exception as e:
            print(f"Errore durante la conversione/visualizzazione del frame: {e}")
            self.update_feedback_and_reps(feedback_text='Errore visualizzazione frame.')
            # Non fermare l'esercizio per questo, potrebbe essere un problema temporaneo

    def closeEvent(self, event):
        self.stop_exercise() # Assicura che tutto sia rilasciato correttamente
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FitnessCoachApp()
    window.show()
    sys.exit(app.exec())