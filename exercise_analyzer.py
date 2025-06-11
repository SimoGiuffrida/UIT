# exercise_analyzer.py
import numpy as np

class ExerciseAnalyzer:
    def __init__(self):
        self.rep_count = 0  # Contatore ripetizioni
        self.pos_state = None  # Stato della posizione: 'up' o 'down'
        self.feedback = ''  # Messaggio di feedback
        self.landmarks_stable = False  # Flag per stabilità dei landmark
        self.stable_frames = 0  # Frame stabili consecutivi
        self.unstable_frames = 0  # Frame instabili consecutivi
        self.req_stable_frames = 20  # Frame necessari per la stabilità
        self.max_unstable_frames = 15  # Max frame instabili tollerati

    def _check_landmarks_visibility(self, landmarks, req_points):
        # Controlla la visibilità dei landmark richiesti
        if not landmarks:
            return False, "Non sei visibile alla telecamera. Posizionati di fronte per iniziare."

        missing_points = []
        for point_id in req_points:
            if point_id not in landmarks or not landmarks[point_id] or len(landmarks[point_id]) < 2:
                missing_points.append(str(point_id))

        if missing_points:
            if len(missing_points) == len(req_points):
                return False, "Non sei visibile alla telecamera. Posizionati di fronte per iniziare."
            else:
                return False, "Alcuni punti del corpo non sono visibili. Assicurati di essere interamente nell'inquadratura."
        return True, ""

    def _handle_landmark_visibility_and_stability(self, landmarks, req_points):
        # Gestisce visibilità e stabilità dei landmark
        all_landmarks_present, feedback_visibility = self._check_landmarks_visibility(landmarks, req_points)

        if not all_landmarks_present:
            self.unstable_frames += 1
            self.stable_frames = 0
            if self.landmarks_stable:
                self.pos_state = None
                self.feedback = "Visibilità persa, riposizionati."
            self.landmarks_stable = False
            if self.unstable_frames >= self.max_unstable_frames:
                return False, "Visibilità persa troppo a lungo. Riposizionati e mantieni la stabilità."
            return False, feedback_visibility

        self.stable_frames += 1
        self.unstable_frames = 0

        if self.stable_frames >= self.req_stable_frames:
            if not self.landmarks_stable:
                self.feedback = "Stabile. Puoi iniziare l'esercizio!"
            self.landmarks_stable = True
            return True, ""
        else:
            self.landmarks_stable = False
            return False, f"Mantieni una posizione stabile ({self.stable_frames}/{self.req_stable_frames})..."

    def analyze_squat(self, landmarks):
        req_points = [11, 12, 23, 24, 25, 27]  # Spalle, Anche, Ginocchio Destro, Caviglia Destra
        
        status_ok, stability_feedback = self._handle_landmark_visibility_and_stability(landmarks, req_points)
        if not status_ok:
            self.feedback = stability_feedback
            return False, self.feedback

        try:
            shoulder_mid = [(landmarks[11][0] + landmarks[12][0])/2, (landmarks[11][1] + landmarks[12][1])/2]
            hip_mid = [(landmarks[23][0] + landmarks[24][0])/2, (landmarks[23][1] + landmarks[24][1])/2]

            knee_angle = self._calculate_angle(hip_mid, landmarks[25], landmarks[27])
            torso_angle = self._calculate_angle(shoulder_mid, hip_mid, landmarks[25])

            current_feedback = "" 
            pose_correct = True 

            if knee_angle > 160:  # Posizione eretta
                if self.pos_state == 'down':
                    self.rep_count += 1
                    current_feedback = f'Ottimo! Ripetizione {self.rep_count} completata.'
                else:
                    current_feedback = 'Piega le ginocchia per iniziare lo squat.'
                self.pos_state = 'up'
            elif 110 <= knee_angle < 140:  # Posizione corretta dello squat
                self.pos_state = 'down'
                if torso_angle < 45:  # Torso troppo piegato
                    current_feedback = 'Tieni la schiena più dritta, non piegare troppo il busto.'
                    pose_correct = False
                elif torso_angle > 150:  # Torso troppo dritto/indietro
                    current_feedback = 'Inclina leggermente il busto in avanti, non andare indietro.'
                    pose_correct = False
                else:
                    current_feedback = 'Ottima posizione per lo squat!'
            elif knee_angle < 90:  # Squat troppo profondo
                self.pos_state = 'down' 
                current_feedback = 'Squat troppo profondo, risali un po\' senza estendere completamente.'
                pose_correct = False
            else:  # Angolo intermedio
                if self.pos_state == 'up':
                    current_feedback = 'Scendi controllando il movimento.'
                elif self.pos_state == 'down': 
                    current_feedback = 'Completa il movimento salendo o scendendo correttamente.'
                else:  # pos_state è None
                     current_feedback = "Preparati per lo squat."

            if torso_angle < 40 and self.pos_state == 'down':
                current_feedback = 'Attenzione alla schiena! Tienila più dritta.'
                pose_correct = False
            
            self.feedback = current_feedback if current_feedback else "Continua..."
            return pose_correct, self.feedback

        except KeyError as e:
            self.landmarks_stable = False 
            self.pos_state = None
            self.feedback = f"Errore: punto chiave {e} non trovato. Riposizionati."
            return False, self.feedback
        except Exception as e:
            self.pos_state = None
            self.feedback = f"Errore durante l'analisi dello squat: {str(e)}"
            return False, self.feedback

    def analyze_lunge(self, landmarks):
        req_points = [23, 24, 25, 26, 27, 28]  # Anche, ginocchia, caviglie (entrambe le gambe)

        status_ok, stability_feedback = self._handle_landmark_visibility_and_stability(landmarks, req_points)
        if not status_ok:
            self.feedback = stability_feedback
            return False, self.feedback

        try:
            hip_r = landmarks[24][:2]
            knee_r = landmarks[26][:2]
            ankle_r = landmarks[28][:2]
            hip_l = landmarks[23][:2]
            knee_l = landmarks[25][:2]
            ankle_l = landmarks[27][:2]

            knee_r_angle = self._calculate_angle(hip_r, knee_r, ankle_r)
            knee_l_angle = self._calculate_angle(hip_l, knee_l, ankle_l)

            current_feedback = ""
            pose_correct = True

            # Condizione su: entrambe le ginocchia estese
            if knee_r_angle > 160 and knee_l_angle > 160:
                if self.pos_state == 'down':
                    self.rep_count += 1
                    current_feedback = f'Ottimo! Ripetizione {self.rep_count} completata.'
                else:
                    current_feedback = 'Fai un passo per iniziare l\'affondo.'
                self.pos_state = 'up'
            
            # Condizione giù: una gamba avanti (75-115 deg), una indietro (65-150 deg)
            elif (75 <= knee_r_angle <= 115 and 65 <= knee_l_angle <= 150):
                self.pos_state = 'down'
                current_feedback = 'Buona posizione di affondo (gamba destra avanti)!'
            
            # Gamba sinistra avanti, gamba destra indietro
            elif (75 <= knee_l_angle <= 115 and 65 <= knee_r_angle <= 150):
                self.pos_state = 'down'
                current_feedback = 'Buona posizione di affondo (gamba sinistra avanti)!'
            
            # Angolo intermedio o configurazione errata
            else:
                feedback_set_in_else = False
                if knee_r_angle < 65 and knee_l_angle < 65 :
                    current_feedback = "Affondo troppo profondo o posizione errata, risali un po'."
                    pose_correct = False
                    feedback_set_in_else = True
                    if self.pos_state != 'down':
                        self.pos_state = 'down'

                if not feedback_set_in_else:
                    if self.pos_state == 'up' or self.pos_state is None:
                        current_feedback = 'Scendi nell\'affondo...'
                        pose_correct = False 
                    elif self.pos_state == 'down':
                        current_feedback = "Stai risalendo o correggendo la tua forma..."
                    else:
                        current_feedback = "Aggiusta la posizione dell'affondo."
                        pose_correct = False

            self.feedback = current_feedback if current_feedback else "Continua l'affondo..."
            return pose_correct, self.feedback

        except KeyError as e:
            self.landmarks_stable = False
            self.pos_state = None
            self.feedback = f"Errore: punto chiave {e} non trovato per l'affondo. Riposizionati."
            return False, self.feedback
        except Exception as e:
            self.pos_state = None
            self.feedback = f"Errore durante l'analisi dell'affondo: {str(e)}"
            return False, self.feedback

    def _calculate_angle(self, p1, p2, p3):
        # Calcola l'angolo tra tre punti
        p1, p2, p3 = np.array(p1), np.array(p2), np.array(p3)
        radians = np.arctan2(p3[1]-p2[1], p3[0]-p2[0]) - \
                 np.arctan2(p1[1]-p2[1], p1[0]-p2[0])
        angle = np.abs(radians*180.0/np.pi)
        if angle > 180.0:
            angle = 360-angle
        return angle

    def get_rep_count(self):
        return self.rep_count

    def reset_counter(self):
        self.rep_count = 0
        self.pos_state = None
        self.feedback = 'Contatore azzerato. Preparati.'
        self.landmarks_stable = False
        self.stable_frames = 0
        self.unstable_frames = 0