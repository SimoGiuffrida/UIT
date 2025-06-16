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
        self.squat_depth_info = {'user_hip_y': None, 'optimal_hip_y': None} # Nuovo: informazioni per la guida della profondità dello squat
        self.target_pose_landmarks = {} # Stores normalized [x, y] for target points

    def _check_landmarks_visibility(self, landmarks, req_points):
        # Controlla la visibilità dei landmark richiesti
        if not landmarks:
            return False, "Non sei visibile alla telecamera. Posizionati di fronte per iniziare."

        missing_points = []
        for point_id in req_points:
            # Assicurati che il landmark esista e che abbia almeno le coordinate [x, y]
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

        # Reset target landmarks for the current frame
        self.target_pose_landmarks = {}
        # Reset delle informazioni sulla profondità all'inizio di ogni analisi
        self.squat_depth_info = {'user_hip_y': None, 'optimal_hip_y': None}

        status_ok, stability_feedback = self._handle_landmark_visibility_and_stability(landmarks, req_points)
        if not status_ok:
            self.feedback = stability_feedback
            return False, self.feedback

        try:
            # Assicurati di prendere le coordinate pixel per il calcolo dell'angolo e le normalizzate per il feedback visivo
            shoulder_mid_px = [(landmarks[11][0] + landmarks[12][0])/2, (landmarks[11][1] + landmarks[12][1])/2]
            hip_mid_px = [(landmarks[23][0] + landmarks[24][0])/2, (landmarks[23][1] + landmarks[24][1])/2]

            # Use normalized coordinates for relative calculations
            hip_mid_norm_y = (landmarks[23][5] + landmarks[24][5]) / 2
            knee_mid_norm_y = (landmarks[25][5] + landmarks[26][5]) / 2
            ankle_mid_norm_y = (landmarks[27][5] + landmarks[28][5]) / 2

            # Average X coordinates for symmetry
            hip_mid_norm_x = (landmarks[23][4] + landmarks[24][4]) / 2
            knee_mid_norm_x = (landmarks[25][4] + landmarks[26][4]) / 2


            knee_angle = self._calculate_angle(hip_mid_px, landmarks[25][:2], landmarks[27][:2])
            torso_angle = self._calculate_angle(shoulder_mid_px, hip_mid_px, landmarks[25][:2])

            current_feedback = ""
            pose_correct = True

            # Valore y normalizzato per l'anca alla profondità ottimale (es. 0.65)
            optimal_hip_y_for_feedback = 0.65

            if knee_angle > 160:  # Posizione eretta (utente UP)
                if self.pos_state == 'down':
                    self.rep_count += 1
                    current_feedback = f'Ottimo! Ripetizione {self.rep_count} completata.'
                else:
                    current_feedback = 'Piega le ginocchia per iniziare lo squat.'
                    # If user is UP, set target for DOWN position
                    if self.landmarks_stable: # Only show targets when stable
                        # Define target Y position relative to current hip/ankle Y
                        # These ratios are empirical and might need fine-tuning based on testing
                        target_hip_y = ankle_mid_norm_y * 0.75 # Example: hip moves down to 75% of distance from top to ankle
                        target_knee_y = ankle_mid_norm_y * 0.9 # Example: knee moves down to 90% of distance from top to ankle

                        # Keep X relative to user's body width / center
                        self.target_pose_landmarks[23] = [hip_mid_norm_x - 0.05, target_hip_y] # Left Hip
                        self.target_pose_landmarks[24] = [hip_mid_norm_x + 0.05, target_hip_y] # Right Hip
                        self.target_pose_landmarks[25] = [knee_mid_norm_x - 0.05, target_knee_y] # Left Knee
                        self.target_pose_landmarks[26] = [knee_mid_norm_x + 0.05, target_knee_y] # Right Knee


                self.pos_state = 'up'
            elif 110 <= knee_angle < 140:  # Posizione corretta dello squat (utente DOWN)
                self.pos_state = 'down'
                self.target_pose_landmarks = {} # Clear targets when in correct down position
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
                self.target_pose_landmarks = {} # Clear targets
                current_feedback = 'Squat troppo profondo, risali un po\' senza estendere completamente.'
                pose_correct = False
                # Imposta le informazioni per la guida visiva
                self.squat_depth_info['user_hip_y'] = hip_mid_norm_y
                self.squat_depth_info['optimal_hip_y'] = optimal_hip_y_for_feedback
            else:  # Angolo intermedio
                if self.pos_state == 'up':
                    current_feedback = 'Scendi controllando il movimento.'
                    # User is transitioning down, keep showing targets
                    if self.landmarks_stable:
                        target_hip_y = ankle_mid_norm_y * 0.75
                        target_knee_y = ankle_mid_norm_y * 0.9

                        self.target_pose_landmarks[23] = [hip_mid_norm_x - 0.05, target_hip_y]
                        self.target_pose_landmarks[24] = [hip_mid_norm_x + 0.05, target_hip_y]
                        self.target_pose_landmarks[25] = [knee_mid_norm_x - 0.05, target_knee_y]
                        self.target_pose_landmarks[26] = [knee_mid_norm_x + 0.05, target_knee_y]

                elif self.pos_state == 'down':
                    self.target_pose_landmarks = {} # No targets needed when going up
                    current_feedback = 'Completa il movimento salendo o scendendo correttamente.'
                else:  # pos_state è None
                    self.target_pose_landmarks = {} # No targets initially
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
            self.target_pose_landmarks = {}
            return False, self.feedback
        except Exception as e:
            self.pos_state = None
            self.feedback = f"Errore durante l'analisi dello squat: {str(e)}"
            self.target_pose_landmarks = {}
            return False, self.feedback

    def analyze_lunge(self, landmarks):
        req_points = [23, 24, 25, 26, 27, 28]  # Anche, ginocchia, caviglie (entrambe le gambe)

        # Reset target landmarks for the current frame
        self.target_pose_landmarks = {}

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

            # Normalized coordinates for target calculation
            knee_r_norm_x, knee_r_norm_y = landmarks[26][4], landmarks[26][5]
            knee_l_norm_x, knee_l_norm_y = landmarks[25][4], landmarks[25][5]
            ankle_r_norm_x, ankle_r_norm_y = landmarks[28][4], landmarks[28][5]
            ankle_l_norm_x, ankle_l_norm_y = landmarks[27][4], landmarks[27][5]


            knee_r_angle = self._calculate_angle(hip_r, knee_r, ankle_r)
            knee_l_angle = self._calculate_angle(hip_l, knee_l, ankle_l)

            current_feedback = ""
            pose_correct = True

            # Condizione su: entrambe le ginocchia estese (utente UP)
            if knee_r_angle > 160 and knee_l_angle > 160:
                if self.pos_state == 'down':
                    self.rep_count += 1
                    current_feedback = f'Ottimo! Ripetizione {self.rep_count} completata.'
                else:
                    current_feedback = 'Fai un passo per iniziare l\'affondo.'
                    # If user is UP, set target for DOWN lunge position
                    if self.landmarks_stable:
                        # Queste posizioni target sono euristiche basate sulla posa ideale di un affondo
                        # Si assume che una gamba (es. destra) vada avanti e l'altra (sinistra) indietro.
                        # Questi valori potrebbero necessitare di fine-tuning.

                        # Target ginocchio destro (presumendo gamba destra avanti)
                        target_knee_r_y = ankle_r_norm_y * 0.8 # Profondità del ginocchio anteriore
                        target_knee_r_x = knee_r_norm_x + 0.1 # Spostamento orizzontale in avanti
                        self.target_pose_landmarks[26] = [target_knee_r_x, target_knee_r_y]

                        # Target ginocchio sinistro (presumendo gamba sinistra indietro)
                        target_knee_l_y = ankle_l_norm_y * 0.9 # Profondità del ginocchio posteriore
                        target_knee_l_x = knee_l_norm_x + 0.05 # Spostamento orizzontale indietro/leggermente verso il centro
                        self.target_pose_landmarks[25] = [target_knee_l_x, target_knee_l_y]

                self.pos_state = 'up'

            # Condizione giù: una gamba avanti (75-115 deg), una indietro (65-150 deg)
            elif (75 <= knee_r_angle <= 115 and 65 <= knee_l_angle <= 150) or \
                 (75 <= knee_l_angle <= 115 and 65 <= knee_r_angle <= 150):
                self.pos_state = 'down'
                self.target_pose_landmarks = {} # Clear targets when in correct down position
                current_feedback = 'Buona posizione di affondo!'

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
                        # User is transitioning down, keep showing targets
                        if self.landmarks_stable:
                            target_knee_r_y = ankle_r_norm_y * 0.8
                            target_knee_r_x = knee_r_norm_x + 0.1
                            self.target_pose_landmarks[26] = [target_knee_r_x, target_knee_r_y]

                            target_knee_l_y = ankle_l_norm_y * 0.9
                            target_knee_l_x = knee_l_norm_x + 0.05
                            self.target_pose_landmarks[25] = [target_knee_l_x, target_knee_l_y]

                    elif self.pos_state == 'down':
                        self.target_pose_landmarks = {} # No targets needed when going up
                        current_feedback = "Stai risalendo o correggendo la tua forma..."
                    else:
                        self.target_pose_landmarks = {}
                        current_feedback = "Aggiusta la posizione dell'affondo."
                        pose_correct = False

            self.feedback = current_feedback if current_feedback else "Continua l'affondo..."
            return pose_correct, self.feedback

        except KeyError as e:
            self.landmarks_stable = False
            self.pos_state = None
            self.feedback = f"Errore: punto chiave {e} non trovato per l'affondo. Riposizionati."
            self.target_pose_landmarks = {}
            return False, self.feedback
        except Exception as e:
            self.pos_state = None
            self.feedback = f"Errore durante l'analisi dell'affondo: {str(e)}"
            self.target_pose_landmarks = {}
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
        self.squat_depth_info = {'user_hip_y': None, 'optimal_hip_y': None} # Reset anche del feedback profondità
        self.target_pose_landmarks = {} # Reset target landmarks