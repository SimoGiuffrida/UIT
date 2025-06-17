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
        # Informazioni per il widget di profondità dello squat
        self.squat_range_info = {
            'current_hip_y': None,
            'upper_bound_y': None,
            'correct_bound_y': None,  # NEW: ideal transition point
            'lower_bound_y': None
        }
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
            # Reset delle informazioni sul range se si perde la visibilità
            self.squat_range_info = {'current_hip_y': None, 'upper_bound_y': None, 'lower_bound_y': None}
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
            # Reset delle informazioni sul range durante l'instabilità
            self.squat_range_info = {'current_hip_y': None, 'upper_bound_y': None, 'lower_bound_y': None}
            return False, f"Mantieni una posizione stabile ({self.stable_frames}/{self.req_stable_frames})..."

    def analyze_squat(self, landmarks):
        req_points = [11, 12, 23, 24, 25, 26, 27, 28]

        # Reset
        self.target_pose_landmarks = {}
        self.squat_range_info = {'current_hip_y': None, 'upper_bound_y': None, 'lower_bound_y': None}

        status_ok, stability_feedback = self._handle_landmark_visibility_and_stability(landmarks, req_points)
        if not status_ok:
            self.feedback = stability_feedback
            return False, self.feedback

        try:
            # Coordinate Pixel per angoli
            shoulder_mid_px = [(landmarks[11][0] + landmarks[12][0])/2, (landmarks[11][1] + landmarks[12][1])/2]
            hip_mid_px = [(landmarks[23][0] + landmarks[24][0])/2, (landmarks[23][1] + landmarks[24][1])/2]
            knee_r_px = landmarks[26][:2]
            ankle_r_px = landmarks[28][:2]
            knee_l_px = landmarks[25][:2]
            ankle_l_px = landmarks[27][:2]
            knee_mid_px = [(knee_r_px[0] + knee_l_px[0])/2, (knee_r_px[1] + knee_l_px[1])/2]

            # Coordinate Normalizzate per la logica
            hip_mid_norm_y = (landmarks[23][5] + landmarks[24][5]) / 2
            
            # LOGICA MODIFICATA: Limiti più rigorosi per lo squat
            # Calcoliamo i limiti basandoci sull'altezza dello scheletro rilevato
            shoulder_mid_norm_y = (landmarks[11][5] + landmarks[12][5]) / 2
            ankle_mid_norm_y = (landmarks[27][5] + landmarks[28][5]) / 2

            SQUAT_CORRECT_BOUND_Y = None  # NEW
            SQUAT_UPPER_BOUND_Y = None
            SQUAT_LOWER_BOUND_Y = None

            # Calcoliamo l'altezza operativa (spalle -> caviglie) per rendere i limiti relativi
            operational_height = ankle_mid_norm_y - shoulder_mid_norm_y
            if operational_height > 0.1: # Controllo di sicurezza per evitare valori anomali
                # Il limite superiore rimane a circa il 35% della discesa dalle spalle
                SQUAT_UPPER_BOUND_Y = shoulder_mid_norm_y + operational_height * 0.35
                SQUAT_CORRECT_BOUND_Y = shoulder_mid_norm_y + operational_height * 0.5  # NEW: 50% depth
                # MODIFICA: Il limite inferiore è ora al 65% invece del 75% (più alto = più rigoroso)
                SQUAT_LOWER_BOUND_Y = shoulder_mid_norm_y + operational_height * 0.65
            
            # Popola le informazioni per il widget, solo se i limiti sono stati calcolati
            if SQUAT_UPPER_BOUND_Y is not None:
                self.squat_range_info = {
                    'current_hip_y': hip_mid_norm_y,
                    'upper_bound_y': SQUAT_UPPER_BOUND_Y,
                    'correct_bound_y': SQUAT_CORRECT_BOUND_Y,  # NEW
                    'lower_bound_y': SQUAT_LOWER_BOUND_Y
                }

            # Calcolo angoli
            knee_angle_r = self._calculate_angle(hip_mid_px, knee_r_px, ankle_r_px)
            knee_angle_l = self._calculate_angle(hip_mid_px, knee_l_px, ankle_l_px)
            knee_angle = (knee_angle_r + knee_angle_l) / 2
            torso_angle = self._calculate_angle(shoulder_mid_px, hip_mid_px, knee_mid_px)

            current_feedback = ""
            pose_correct = True

            # LOGICA MODIFICATA: Range di angoli più rigoroso
            if knee_angle > 160:
                # Se il ginocchio è quasi dritto, l'utente è in posizione "su"
                if self.pos_state == 'down':
                    # Se l'utente era in posizione "giù" e ora è "su", una ripetizione è completa
                    self.rep_count += 1
                    current_feedback = f'Ottimo! Ripetizione {self.rep_count} completata.'
                else:
                    current_feedback = 'Piega le ginocchia per iniziare lo squat.'
                self.pos_state = 'up' # Imposta lo stato a 'up'
            elif 110 <= knee_angle <= 130:
                # Questa è la zona di squat valido
                self.pos_state = 'down' # L'utente è sceso abbastanza
                if torso_angle < 45:
                    current_feedback = 'Tieni la schiena più dritta, non piegare troppo il busto.'
                    pose_correct = False
                else:
                    current_feedback = 'Ottima posizione per lo squat!'
            elif knee_angle < 110:
                # Squat troppo profondo
                self.pos_state = 'down' # Anche se troppo profondo, è comunque considerato "giù"
                current_feedback = 'Squat troppo profondo, risali fino alla zona corretta.'
                pose_correct = False
            elif 130 < knee_angle <= 160:
                # L'utente non è sceso abbastanza per un squat valido, ma è in fase di discesa
                if self.pos_state == 'up': # Se prima era in alto
                    current_feedback = 'Scendi di più per un squat valido.'
                elif self.pos_state == 'down': # Se era già "down" (ad es. troppo profondo) e sta risalendo in questo range
                    current_feedback = 'Scendi ancora un po\' per completare il movimento.'
                else: # Stato iniziale o indefinito
                    current_feedback = "Scendi di più per raggiungere la posizione corretta."
                # IMPORTANTE: non cambiamo self.pos_state a 'down' qui per non convalidare un mezzo squat
            else:
                # Stati intermedi o non riconosciuti
                if self.pos_state == 'up':
                    current_feedback = 'Scendi controllando il movimento.'
                elif self.pos_state == 'down':
                    current_feedback = 'Completa il movimento salendo correttamente.'
                else:
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
        req_points = [23, 24, 25, 26, 27, 28]

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

            knee_r_angle = self._calculate_angle(hip_r, knee_r, ankle_r)
            knee_l_angle = self._calculate_angle(hip_l, knee_l, ankle_l)

            current_feedback = ""
            pose_correct = True

            if knee_r_angle > 160 and knee_l_angle > 160:
                if self.pos_state == 'down':
                    self.rep_count += 1
                    current_feedback = f'Ottimo! Ripetizione {self.rep_count} completata.'
                else:
                    current_feedback = 'Fai un passo per iniziare l\'affondo.'
                self.pos_state = 'up'

            elif (75 <= knee_r_angle <= 115 and 65 <= knee_l_angle <= 150) or \
                 (75 <= knee_l_angle <= 115 and 65 <= knee_r_angle <= 150):
                self.pos_state = 'down'
                current_feedback = 'Buona posizione di affondo!'

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
        # Reset anche del range info
        self.squat_range_info = {'current_hip_y': None, 'upper_bound_y': None, 'lower_bound_y': None}
        self.target_pose_landmarks = {} # Reset target landmarks