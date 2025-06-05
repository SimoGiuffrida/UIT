import numpy as np

class ExerciseAnalyzer:
    def __init__(self):
        self.rep_counter = 0 #
        self.position_state = None  # 'up' o 'down' #
        self.feedback = '' #
        self.landmarks_currently_visible_and_stable = False #
        self.stable_frames = 0 #
        self.unstable_frames = 0 #
        self.required_stable_frames = 20 #
        self.max_unstable_frames = 15 #

    def _check_landmarks_visibility(self, landmarks, required_points):
        if not landmarks: #
            return False, "Non sei visibile nella telecamera. Posizionati di fronte alla telecamera per iniziare."

        missing_points_data = [] #
        for point_id in required_points: #
            if point_id not in landmarks or not landmarks[point_id] or len(landmarks[point_id]) < 2: #
                missing_points_data.append(str(point_id)) #

        if missing_points_data: #
            if len(missing_points_data) == len(required_points): #
                return False, "Non sei visibile nella telecamera. Posizionati di fronte alla telecamera per iniziare."
            else:
                return False, "Alcuni punti del corpo non sono visibili. Assicurati che tutto il corpo sia inquadrato." #
        return True, "" #

    def _handle_landmark_visibility_and_stability(self, landmarks, required_points):
        all_landmarks_present_this_frame, feedback_visibility = self._check_landmarks_visibility(landmarks, required_points) #

        if not all_landmarks_present_this_frame: #
            self.unstable_frames += 1 #
            self.stable_frames = 0 #
            if self.landmarks_currently_visible_and_stable: #
                self.position_state = None #
                self.feedback = "Visibilità persa, riposizionati." #
            self.landmarks_currently_visible_and_stable = False #
            if self.unstable_frames >= self.max_unstable_frames: #
                return False, "Visibilità persa per troppo tempo. Riposizionati e mantieni la stabilità."
            return False, feedback_visibility #

        self.stable_frames += 1 #
        self.unstable_frames = 0 #

        if self.stable_frames >= self.required_stable_frames: #
            if not self.landmarks_currently_visible_and_stable: #
                self.feedback = "Stabile. Puoi iniziare l'esercizio!" #
            self.landmarks_currently_visible_and_stable = True #
            return True, "" #
        else:
            self.landmarks_currently_visible_and_stable = False #
            return False, f"Mantieni la posizione stabile ({self.stable_frames}/{self.required_stable_frames})..." #

    def analyze_squat(self, landmarks):
        required_points = [11, 12, 23, 24, 25, 27] # Spalle, Anche, Ginocchio Dx, Caviglia Dx #
        
        status_ok, stability_feedback = self._handle_landmark_visibility_and_stability(landmarks, required_points) #
        if not status_ok: #
            self.feedback = stability_feedback #
            return False, self.feedback #

        try:
            shoulder_mid = [(landmarks[11][0] + landmarks[12][0])/2, (landmarks[11][1] + landmarks[12][1])/2] #
            hip_mid = [(landmarks[23][0] + landmarks[24][0])/2, (landmarks[23][1] + landmarks[24][1])/2] #

            knee_angle = self._calculate_angle(hip_mid, landmarks[25], landmarks[27]) #
            torso_angle = self._calculate_angle(shoulder_mid, hip_mid, landmarks[25]) #

            current_feedback = "" #
            pose_correct = True #

            if knee_angle > 160: # Posizione eretta (o quasi) #
                if self.position_state == 'down': #
                    self.rep_counter += 1 #
                    current_feedback = f'Ottimo! Ripetizione {self.rep_counter} completata.' #
                else:
                    current_feedback = 'Piega le ginocchia per iniziare lo squat.' #
                self.position_state = 'up' #
            elif 90 <= knee_angle <= 120:  # Posizione squat corretta #
                self.position_state = 'down' #
                if torso_angle < 45: # Busto troppo piegato #
                    current_feedback = 'Mantieni la schiena più dritta, non piegare troppo il busto.' #
                    pose_correct = False #
                elif torso_angle > 100: # Busto troppo dritto/indietro (era 120, ridotto per più flessibilità) #
                    current_feedback = 'Inclina leggermente il busto in avanti, non andare all\'indietro.' #
                    pose_correct = False #
                else:
                    current_feedback = 'Ottima posizione squat!' #
            elif knee_angle < 90:  # Squat troppo profondo #
                self.position_state = 'down' #
                current_feedback = 'Squat troppo profondo, risali leggermente senza estendere completamente.' #
                pose_correct = False #
            else: # Angolo intermedio #
                # Mantenere lo stato precedente se non si entra in una nuova categoria definita
                # E dare feedback appropriato
                if self.position_state == 'up': #
                    current_feedback = 'Scendi più in basso controllando il movimento.' #
                elif self.position_state == 'down': #
                     current_feedback = 'Completa il movimento tornando su o scendendo correttamente.' #
                else: # position_state is None
                    current_feedback = "Preparati per lo squat."
                pose_correct = False # Non è una posa definita perfetta, ma potrebbe essere una transizione #

            if torso_angle < 40 and self.position_state == 'down': # busto molto piegato in squat #
                current_feedback = 'Attenzione alla schiena! Mantienila più dritta.' #
                pose_correct = False #
            
            self.feedback = current_feedback if current_feedback else "Continua..." #
            return pose_correct, self.feedback #

        except KeyError as e:
            self.landmarks_currently_visible_and_stable = False #
            self.position_state = None #
            self.feedback = f"Errore: punto chiave {e} non trovato. Riposizionati." #
            return False, self.feedback #
        except Exception as e:
            self.position_state = None #
            self.feedback = f"Errore durante l'analisi dello squat: {str(e)}" #
            return False, self.feedback #

    def analyze_lunge(self, landmarks):
        required_points = [23, 24, 25, 26, 27, 28] # Anche, ginocchia, caviglie (entrambe le gambe) #

        status_ok, stability_feedback = self._handle_landmark_visibility_and_stability(landmarks, required_points) #
        if not status_ok: #
            self.feedback = stability_feedback #
            return False, self.feedback #

        try:
            hip_right = landmarks[24][:2] #
            knee_right_pt = landmarks[26][:2] #
            ankle_right_pt = landmarks[28][:2] #
            hip_left = landmarks[23][:2] #
            knee_left_pt = landmarks[25][:2] #
            ankle_left_pt = landmarks[27][:2] #

            knee_R_angle = self._calculate_angle(hip_right, knee_right_pt, ankle_right_pt)
            knee_L_angle = self._calculate_angle(hip_left, knee_left_pt, ankle_left_pt)

            current_feedback = ""
            pose_correct = True

            # Condizione UP: entrambe le ginocchia estese
            if knee_R_angle > 160 and knee_L_angle > 160:
                if self.position_state == 'down':
                    self.rep_counter += 1
                    current_feedback = f'Ottimo! Ripetizione {self.rep_counter} completata.'
                else:
                    current_feedback = 'Fai un passo per iniziare l\'affondo.'
                self.position_state = 'up'
                # pose_correct è True perché 'up' è una posa valida per iniziare/finire una rep
            
            # Condizione DOWN: una gamba anteriore (80-110 gradi), una posteriore (70-145 gradi)
            # is_R_front: Gamba Destra è anteriore, Gamba Sinistra è posteriore
            elif (80 <= knee_R_angle <= 110 and 70 <= knee_L_angle <= 145):
                self.position_state = 'down'
                current_feedback = 'Buona posizione di affondo (Dx avanti)!'
                # Qui si potrebbero aggiungere controlli specifici per la gamba destra come anteriore se necessario
                # Esempio: if landmarks[26][0] < landmarks[28][0] - 15: # Ginocchio Dx troppo avanti (se specchiato e di profilo)
                # current_feedback = 'Ginocchio destro (anteriore) un po\' troppo avanti.'
                # pose_correct = False 
            
            # is_L_front: Gamba Sinistra è anteriore, Gamba Destra è posteriore
            elif (80 <= knee_L_angle <= 110 and 70 <= knee_R_angle <= 145):
                self.position_state = 'down'
                current_feedback = 'Buona posizione di affondo (Sx avanti)!'
                # Qui si potrebbero aggiungere controlli specifici per la gamba sinistra come anteriore
                # Esempio: if landmarks[25][0] > landmarks[27][0] + 15: # Ginocchio Sx troppo avanti (se specchiato e di profilo)
                # current_feedback = 'Ginocchio sinistro (anteriore) un po\' troppo avanti.'
                # pose_correct = False
            
            # Non è UP e non è una configurazione DOWN chiara
            else:
                pose_correct = False
                if self.position_state == 'up' or self.position_state is None:
                    current_feedback = 'Scendi in affondo: una gamba avanti piegata (circa 90°), l\'altra dietro con ginocchio flesso.'
                elif self.position_state == 'down': # Era 'down' ma ora non è più una buona posa 'down'
                    # Controlla se sta risalendo o se la forma si è persa
                    if knee_R_angle > 110 or knee_L_angle > 110: # Almeno una gamba si sta estendendo
                        current_feedback = "Stai risalendo? Completa tornando su o correggi la posizione di affondo."
                    else: # Entrambe le gambe sono ancora piegate ma non nella configurazione corretta
                        current_feedback = 'Aggiusta la posizione dell\'affondo. Ricontrolla gli angoli delle ginocchia.'
                # Non cambiare position_state qui a meno di una transizione chiara a 'up',
                # per coerenza con lo squat. Se la forma è errata ma si era 'down', si resta 'down' con errore.

            self.feedback = current_feedback
            return pose_correct, self.feedback

        except KeyError as e:
            self.landmarks_currently_visible_and_stable = False #
            self.position_state = None #
            self.feedback = f"Errore: punto chiave {e} non trovato per l'affondo. Riposizionati." #
            return False, self.feedback #
        except Exception as e:
            self.position_state = None #
            self.feedback = f"Errore durante l'analisi dell'affondo: {str(e)}" #
            return False, self.feedback #

    def _calculate_angle(self, p1, p2, p3):
        p1, p2, p3 = np.array(p1), np.array(p2), np.array(p3) #
        radians = np.arctan2(p3[1]-p2[1], p3[0]-p2[0]) - \
                 np.arctan2(p1[1]-p2[1], p1[0]-p2[0]) #
        angle = np.abs(radians*180.0/np.pi) #
        if angle > 180.0: #
            angle = 360-angle #
        return angle #

    def get_rep_count(self):
        return self.rep_counter #

    def reset_counter(self):
        self.rep_counter = 0 #
        self.position_state = None #
        self.feedback = 'Contatore resettato. Preparati.' #
        self.landmarks_currently_visible_and_stable = False #
        self.stable_frames = 0 #
        self.unstable_frames = 0 #