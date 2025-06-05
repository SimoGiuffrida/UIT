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
        required_points = [11, 12, 23, 24, 25, 27] # Spalle, Anche, Ginocchio Dx, Caviglia Dx
        
        # Gestione centralizzata di visibilità e stabilità
        status_ok, stability_feedback = self._handle_landmark_visibility_and_stability(landmarks, required_points)
        if not status_ok:
            # Se non stabile o non visibile, self.position_state è già stato resettato se necessario
            self.feedback = stability_feedback
            return False, self.feedback

        # Se arriviamo qui, i landmark sono visibili e stabili
        try:
            # Calcola i punti medi (spalle e anche)
            # Assicurati che i landmark esistano prima di accedervi (anche se _check_landmarks_visibility dovrebbe garantirlo)
            shoulder_mid = [(landmarks[11][0] + landmarks[12][0])/2, (landmarks[11][1] + landmarks[12][1])/2]
            hip_mid = [(landmarks[23][0] + landmarks[24][0])/2, (landmarks[23][1] + landmarks[24][1])/2]

            # Calcola angoli
            knee_angle = self._calculate_angle(hip_mid, landmarks[25], landmarks[27]) # Usa anca-ginocchio-caviglia destra
            torso_angle = self._calculate_angle(shoulder_mid, hip_mid, landmarks[25]) # Usa spalla-anca-ginocchio destra

            current_feedback = "" # Feedback specifico per la posa
            pose_correct = True

            if knee_angle > 160: # Posizione eretta (o quasi)
                if self.position_state == 'down':
                    self.rep_counter += 1
                    current_feedback = f'Ottimo! Ripetizione {self.rep_counter} completata.'
                else:
                    current_feedback = 'Piega le ginocchia per iniziare lo squat.'
                self.position_state = 'up'
            elif 90 <= knee_angle <= 100:  # Posizione squat corretta
                self.position_state = 'down'
                if torso_angle < 45: # Busto troppo piegato (soglia leggermente aumentata)
                    current_feedback = 'Mantieni la schiena più dritta, non piegare troppo il busto.'
                    pose_correct = False
                elif torso_angle > 120: # Busto troppo dritto/indietro (soglia leggermente ridotta)
                    current_feedback = 'Inclina leggermente il busto in avanti, non andare all\'indietro.'
                    pose_correct = False
                else:
                    current_feedback = 'Ottima posizione squat!'
            elif knee_angle < 90:  # Squat troppo profondo
                self.position_state = 'down' # Considerato 'down' ma non ideale
                current_feedback = 'Squat troppo profondo, risali leggermente senza estendere completamente.'
                pose_correct = False
            else: # Angolo intermedio, es. durante la discesa/salita
                if self.position_state == 'up':
                    current_feedback = 'Scendi più in basso controllando il movimento.'
                else: # self.position_state == 'down' (ma non in range ideale)
                    current_feedback = 'Completa il movimento tornando su o scendendo correttamente.'
                # Non impostare pose_correct = False qui a meno che non sia una posizione errata specifica

            # Sovrascrivi il feedback se il busto è sbagliato in modo significativo
            # Questo controllo è già parzialmente incluso sopra, ma può essere un catch-all
            if torso_angle < 40 and self.position_state == 'down': # busto molto piegato in squat
                current_feedback = 'Attenzione alla schiena! Mantienila più dritta.'
                pose_correct = False
            
            self.feedback = current_feedback if current_feedback else "Continua..."
            return pose_correct, self.feedback

        except KeyError as e:
            # Questo errore non dovrebbe accadere se _handle_landmark_visibility_and_stability funziona correttamente
            self.landmarks_currently_visible_and_stable = False # Resetta la stabilità per sicurezza
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
            # Punti chiave per l'affondo (assicurati che esistano)
            hip_right = landmarks[24][:2]
            knee_right = landmarks[26][:2]
            ankle_right = landmarks[28][:2]
            hip_left = landmarks[23][:2]
            knee_left = landmarks[25][:2]
            ankle_left = landmarks[27][:2]

            # Calcolo angoli (assumendo gamba destra avanti per ora)
            # TODO: Aggiungere logica per determinare gamba anteriore o analizzare entrambe
            front_knee_angle = self._calculate_angle(hip_right, knee_right, ankle_right)
            back_knee_angle = self._calculate_angle(hip_left, knee_left, ankle_left) # Ginocchio posteriore

            current_feedback = ""
            pose_correct = True

            # Identifica la gamba anteriore (quella più avanti sull'asse x, o con ginocchio più piegato in affondo)
            # Semplificazione: assumiamo la gamba destra avanti, o quella con ginocchio più flesso
            # Una euristica migliore: la caviglia più avanzata (minore coordinata x se non specchiato, maggiore se specchiato)
            # Consideriamo il frame specchiato, quindi x maggiore è più a destra dell'utente (sinistra del frame)
            
            # Per ora, basiamoci sull'ipotesi che l'utente sappia quale gamba usare o alterni.
            # Il feedback si riferirà genericamente a "ginocchio anteriore/posteriore".

            if front_knee_angle > 160 and back_knee_angle > 160:  # Posizione eretta
                if self.position_state == 'down':
                    self.rep_counter += 1
                    current_feedback = f'Ottimo! Ripetizione {self.rep_counter} completata.'
                else:
                    current_feedback = 'Fai un passo avanti per iniziare l\'affondo.'
                self.position_state = 'up'
            # Angolo ginocchio anteriore 85-100, ginocchio posteriore < 140 (leggermente piegato o vicino al suolo)
            elif 85 <= front_knee_angle <= 105 and back_knee_angle < 150:
                self.position_state = 'down'
                # Ulteriori controlli per l'affondo:
                # Ginocchio anteriore non oltre la punta del piede (difficile senza profondità 3D reale)
                # Busto dritto
                if ankle_right[0] < knee_right[0] - 15 : # Heuristic: knee significantly ahead of ankle (assuming right leg front)
                     current_feedback = 'Ginocchio anteriore troppo avanti! Mantienilo sopra la caviglia.'
                     pose_correct = False
                elif back_knee_angle < 90: # Ginocchio posteriore troppo piegato / tocca terra
                     current_feedback = 'Ottima profondità! Non appoggiare il ginocchio posteriore.'
                else:
                     current_feedback = 'Posizione affondo corretta!'

            else: # Posizione non corretta o in transizione
                self.position_state = 'down' # In una fase di movimento verso il basso
                pose_correct = False
                if front_knee_angle < 85:
                    current_feedback = 'Ginocchio anteriore troppo piegato o scendi di più.'
                elif front_knee_angle > 105 and self.position_state == 'down': # Solo se si è tentato di scendere
                    current_feedback = 'Piega di più il ginocchio anteriore.'
                elif back_knee_angle >= 150 and self.position_state == 'down':
                    current_feedback = 'Piega anche il ginocchio posteriore, scendendo con il corpo.'
                else:
                    current_feedback = "Aggiusta la posizione dell'affondo."
            
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