import numpy as np

class ExerciseAnalyzer:
    def __init__(self):
        self.rep_counter = 0
        self.position_state = None  # 'up' o 'down'
        self.feedback = ''
        # Flag per tracciare se i landmark sono visibili E stabili
        self.landmarks_currently_visible_and_stable = False
        self.stable_frames = 0
        self.unstable_frames = 0
        # Aumentato per dare più tempo per la stabilizzazione iniziale
        self.required_stable_frames = 20
        self.max_unstable_frames = 15 # Leggermente aumentato per tollerare brevi occlusioni

    def _check_landmarks_visibility(self, landmarks, required_points):
        """Controlla solo la presenza dei landmark, non la stabilità."""
        if not landmarks:
            return False, "Non sei visibile nella telecamera. Posizionati di fronte alla telecamera per iniziare."

        missing_points_data = []
        for point_id in required_points:
            if point_id not in landmarks or not landmarks[point_id] or len(landmarks[point_id]) < 2:
                missing_points_data.append(str(point_id)) # Potresti mappare gli ID a nomi qui

        if missing_points_data:
            if len(missing_points_data) == len(required_points):
                return False, "Non sei visibile nella telecamera. Posizionati di fronte alla telecamera per iniziare."
            else:
                # Fornisce un feedback più specifico sui punti mancanti, se desiderato
                # Per ora, manteniamo un messaggio generico per semplicità
                return False, "Alcuni punti del corpo non sono visibili. Assicurati che tutto il corpo sia inquadrato."
        return True, ""

    def _handle_landmark_visibility_and_stability(self, landmarks, required_points):
        """Gestisce sia la visibilità che la stabilità dei landmark."""
        all_landmarks_present_this_frame, feedback_visibility = self._check_landmarks_visibility(landmarks, required_points)

        if not all_landmarks_present_this_frame:
            self.unstable_frames += 1
            # Resetta stable_frames se i landmark non sono presenti
            self.stable_frames = 0
            if self.landmarks_currently_visible_and_stable: # Era stabile, ora non più
                self.position_state = None # Reset dello stato dell'esercizio
                self.feedback = "Visibilità persa, riposizionati."
            self.landmarks_currently_visible_and_stable = False
            if self.unstable_frames >= self.max_unstable_frames:
                return False, "Visibilità persa per troppo tempo. Riposizionati e mantieni la stabilità."
            return False, feedback_visibility

        # Se siamo qui, i landmark sono presenti in questo frame
        self.stable_frames += 1
        self.unstable_frames = 0 # Resetta il conteggio instabile dato che abbiamo un frame valido

        if self.stable_frames >= self.required_stable_frames:
            if not self.landmarks_currently_visible_and_stable:
                self.feedback = "Stabile. Puoi iniziare l'esercizio!" # Feedback quando si diventa stabili
            self.landmarks_currently_visible_and_stable = True
            # Non restituire feedback qui, lascia che sia l'analisi specifica dell'esercizio a farlo
            return True, ""
        else:
            # I landmark sono presenti, ma non ancora abbastanza stabili
            self.landmarks_currently_visible_and_stable = False
            return False, f"Mantieni la posizione stabile ({self.stable_frames}/{self.required_stable_frames})..."

    def analyze_squat(self, landmarks):
        # Logica ripristinata dalla versione del 4 giugno (originale fornita)
        required_points = [11, 12, 23, 24, 25, 27] # Spalle, Anche, Ginocchio Dx, Caviglia Dx
        
        status_ok, stability_feedback = self._handle_landmark_visibility_and_stability(landmarks, required_points)
        if not status_ok:
            self.feedback = stability_feedback
            return False, self.feedback

        try:
            shoulder_mid = [(landmarks[11][0] + landmarks[12][0])/2, (landmarks[11][1] + landmarks[12][1])/2]
            hip_mid = [(landmarks[23][0] + landmarks[24][0])/2, (landmarks[23][1] + landmarks[24][1])/2]

            knee_angle = self._calculate_angle(hip_mid, landmarks[25], landmarks[27]) # Usa anca-ginocchio-caviglia destra
            torso_angle = self._calculate_angle(shoulder_mid, hip_mid, landmarks[25]) # Usa spalla-anca-ginocchio destra

            current_feedback = "" 
            pose_correct = True 

            if knee_angle > 160: # Posizione eretta (o quasi)
                if self.position_state == 'down':
                    self.rep_counter += 1
                    current_feedback = f'Ottimo! Ripetizione {self.rep_counter} completata.'
                else:
                    current_feedback = 'Piega le ginocchia per iniziare lo squat.'
                self.position_state = 'up'
            elif 110 <= knee_angle < 140:  # Posizione squat corretta
                self.position_state = 'down'
                if torso_angle < 45: # Busto troppo piegato
                    current_feedback = 'Mantieni la schiena più dritta, non piegare troppo il busto.'
                    pose_correct = False
                elif torso_angle > 150: # Busto troppo dritto/indietro
                    current_feedback = 'Inclina leggermente il busto in avanti, non andare all\'indietro.'
                    pose_correct = False
                else:
                    current_feedback = 'Ottima posizione squat!'
            elif knee_angle < 90:  # Squat troppo profondo
                self.position_state = 'down' 
                current_feedback = 'Squat troppo profondo, risali leggermente senza estendere completamente.'
                pose_correct = False
            else: # Angolo intermedio, es. durante la discesa/salita
                if self.position_state == 'up':
                    current_feedback = 'Scendi più in basso controllando il movimento.'
                elif self.position_state == 'down': 
                    current_feedback = 'Completa il movimento tornando su o scendendo correttamente.'
                else: # position_state is None
                     current_feedback = "Preparati per lo squat."
                # Non impostare pose_correct = False qui a meno che non sia una posizione errata specifica
                # pose_correct rimane True se è solo una transizione non definita come errore

            # Controllo aggiuntivo busto (catch-all)
            if torso_angle < 40 and self.position_state == 'down': # busto molto piegato in squat
                current_feedback = 'Attenzione alla schiena! Mantienila più dritta.'
                pose_correct = False
            
            self.feedback = current_feedback if current_feedback else "Continua..."
            return pose_correct, self.feedback

        except KeyError as e:
            self.landmarks_currently_visible_and_stable = False 
            self.position_state = None
            self.feedback = f"Errore: punto chiave {e} non trovato. Riposizionati."
            return False, self.feedback
        except Exception as e:
            self.position_state = None
            self.feedback = f"Errore durante l'analisi dello squat: {str(e)}"
            return False, self.feedback

    def analyze_lunge(self, landmarks):
        required_points = [23, 24, 25, 26, 27, 28] # Anche, ginocchia, caviglie (entrambe le gambe)

        status_ok, stability_feedback = self._handle_landmark_visibility_and_stability(landmarks, required_points)
        if not status_ok:
            self.feedback = stability_feedback
            return False, self.feedback

        try:
            hip_right = landmarks[24][:2]
            knee_right_pt = landmarks[26][:2]
            ankle_right_pt = landmarks[28][:2]
            hip_left = landmarks[23][:2]
            knee_left_pt = landmarks[25][:2]
            ankle_left_pt = landmarks[27][:2]

            knee_R_angle = self._calculate_angle(hip_right, knee_right_pt, ankle_right_pt)
            knee_L_angle = self._calculate_angle(hip_left, knee_left_pt, ankle_left_pt)

            current_feedback = ""
            pose_correct = True # Default a True, diventa False per errori specifici

            # Condizione UP: entrambe le ginocchia estese
            if knee_R_angle > 160 and knee_L_angle > 160:
                if self.position_state == 'down':
                    self.rep_counter += 1
                    current_feedback = f'Ottimo! Ripetizione {self.rep_counter} completata.'
                else:
                    current_feedback = 'Fai un passo per iniziare l\'affondo.'
                self.position_state = 'up'
            
            # Condizione DOWN: una gamba anteriore (75-115 gradi), una posteriore (65-150 gradi)
            # Gamba Destra è anteriore, Gamba Sinistra è posteriore
            elif (75 <= knee_R_angle <= 115 and 65 <= knee_L_angle <= 150):
                self.position_state = 'down'
                current_feedback = 'Buona posizione di affondo (Dx avanti)!'
                # Qui si potrebbero aggiungere controlli specifici che impostano pose_correct = False
                # Esempio: if <condizione errore busto/ginocchio>: pose_correct = False; current_feedback = "Errore X"
            
            # Gamba Sinistra è anteriore, Gamba Destra è posteriore
            elif (75 <= knee_L_angle <= 115 and 65 <= knee_R_angle <= 150):
                self.position_state = 'down'
                current_feedback = 'Buona posizione di affondo (Sx avanti)!'
                # Controlli aggiuntivi per la gamba sinistra avanti
            
            # Angolo intermedio o configurazione non standard / errata
            else:
                # Se non è UP né una delle due configurazioni DOWN, la posa non è quella target/ideale.
                # Il feedback guiderà l'utente; pose_correct diventerà False se è un errore definito.
                feedback_set_in_else = False
                if knee_R_angle < 65 and knee_L_angle < 65 : # Entrambe le ginocchia troppo piegate (es. affondo esagerato)
                    current_feedback = "Affondo troppo profondo o posizione errata, risali un po'."
                    pose_correct = False
                    feedback_set_in_else = True
                    if self.position_state != 'down': # Se non era già down, consideralo down per questa posa errata
                        self.position_state = 'down'

                if not feedback_set_in_else:
                    if self.position_state == 'up' or self.position_state is None:
                        current_feedback = 'Scendi in affondo...'
                        # Durante la discesa, la posa non è ancora "down perfetta".
                        # Per il bordo colorato, questo stato di transizione è "non corretto".
                        pose_correct = False 
                    elif self.position_state == 'down':
                        current_feedback = "Stai risalendo o correggi la forma..."
                        # Durante la risalita da uno stato 'down', manteniamo pose_correct = True
                        # a meno che la risalita stessa non sia errata (non ancora implementato controllo specifico qui).
                        # Se gli angoli sono semplicemente cambiati da "down perfetto" ma non sono errori definiti,
                        # si assume una transizione valida.
                    else: # Improbabile
                        current_feedback = "Aggiusta la posizione dell'affondo."
                        pose_correct = False


            self.feedback = current_feedback if current_feedback else "Continua l'affondo..."
            return pose_correct, self.feedback

        except KeyError as e:
            self.landmarks_currently_visible_and_stable = False
            self.position_state = None
            self.feedback = f"Errore: punto chiave {e} non trovato per l'affondo. Riposizionati."
            return False, self.feedback
        except Exception as e:
            self.position_state = None
            self.feedback = f"Errore durante l'analisi dell'affondo: {str(e)}"
            return False, self.feedback

    def _calculate_angle(self, p1, p2, p3):
        p1, p2, p3 = np.array(p1), np.array(p2), np.array(p3)
        radians = np.arctan2(p3[1]-p2[1], p3[0]-p2[0]) - \
                 np.arctan2(p1[1]-p2[1], p1[0]-p2[0])
        angle = np.abs(radians*180.0/np.pi)
        if angle > 180.0:
            angle = 360-angle
        return angle

    def get_rep_count(self):
        return self.rep_counter

    def reset_counter(self):
        self.rep_counter = 0
        self.position_state = None
        self.feedback = 'Contatore resettato. Preparati.'
        self.landmarks_currently_visible_and_stable = False
        self.stable_frames = 0
        self.unstable_frames = 0