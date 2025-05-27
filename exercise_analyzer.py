import numpy as np

class ExerciseAnalyzer:
    def __init__(self):
        self.rep_counter = 0
        self.position_state = None  # 'up' o 'down'
        self.feedback = ''
        self.landmarks_visible = False
        self.stable_frames = 0
        self.unstable_frames = 0
        self.required_stable_frames = 15  # Numero di frame consecutivi necessari per considerare i landmark stabili
        self.max_unstable_frames = 10  # Numero massimo di frame instabili prima di resettare

    def _check_landmarks_visibility(self, landmarks, required_points):
        if not landmarks:
            return False, "Non sei visibile nella telecamera. Posizionati di fronte alla telecamera per iniziare."
        
        missing_points = [point for point in required_points if point not in landmarks or len(landmarks[point]) < 2]
        if missing_points:
            if len(missing_points) == len(required_points):
                return False, "Non sei visibile nella telecamera. Posizionati di fronte alla telecamera per iniziare."
            else:
                return False, "Alcuni punti del corpo non sono visibili. Assicurati che tutto il corpo sia inquadrato."
        return True, ""

    def analyze_squat(self, landmarks):
        required_points = [11, 12, 23, 24, 25, 27]  # Spalle destra e sinistra, anche destra e sinistra, ginocchio destro, caviglia destra
        landmarks_visible, feedback = self._check_landmarks_visibility(landmarks, required_points)
        
        if not landmarks_visible:
            if self.landmarks_visible:  # Se prima erano visibili e ora non lo sono più
                self.position_state = None  # Reset dello stato
                self.stable_frames = 0
                self.unstable_frames = 0
            self.landmarks_visible = False
            return False, feedback

        try:
            # Verifica che tutti i punti necessari siano presenti
            for point in required_points:
                if point not in landmarks:
                    return False, f"Punto {point} mancante. Assicurati che tutto il corpo sia visibile."

            # Calcola i punti medi (spalle e anche)
            shoulder_mid = [(landmarks[11][0] + landmarks[12][0])/2, (landmarks[11][1] + landmarks[12][1])/2]
            hip_mid = [(landmarks[23][0] + landmarks[24][0])/2, (landmarks[23][1] + landmarks[24][1])/2]

            # Calcola angoli
            knee_angle = self._calculate_angle(hip_mid, landmarks[25], landmarks[27])
            torso_angle = self._calculate_angle(shoulder_mid, hip_mid, landmarks[25])

            # Analisi della posa (resto del codice invariato)
            if knee_angle > 160:
                if self.position_state == 'down':
                    self.rep_counter += 1
                self.position_state = 'up'
                self.feedback = 'Piega le ginocchia per iniziare lo squat'
                return True, self.feedback
            elif 90 <= knee_angle <= 120:  # Posizione squat corretta
                self.position_state = 'down'
                # Verifica l'angolazione del busto
                if torso_angle < 40:  # Il busto è troppo piegato in avanti
                    self.feedback = 'Mantieni la schiena più dritta'
                    return False, self.feedback
                elif torso_angle > 110:  # Il busto è troppo inclinato all'indietro
                    self.feedback = 'Non piegare il busto all\'indietro'
                    return False, self.feedback
                else:
                    self.feedback = 'Ottima posizione!'
                    return True, self.feedback

            elif knee_angle < 90:  # Squat troppo profondo
                self.position_state = 'down'
                self.feedback = 'Squat troppo profondo, risali leggermente'
                return False, self.feedback

            # Se l'angolazione del busto non è corretta in qualsiasi posizione
            if torso_angle < 40 or torso_angle > 110:
                self.feedback = 'Mantieni la schiena dritta'
                return False, self.feedback

            self.landmarks_visible = True
            return True, self.feedback
        except Exception as e:
            return False, f"Errore nell'analisi: {str(e)}"  # Restituisci l'errore specifico

    def analyze_lunge(self, landmarks):
        required_points = [23, 24, 25, 26, 27, 28]  # Anche, ginocchia e caviglie di entrambe le gambe
        landmarks_visible, feedback = self._check_landmarks_visibility(landmarks, required_points)
        
        if not landmarks_visible:
            if self.landmarks_visible:  # Se prima erano visibili e ora non lo sono più
                self.position_state = None  # Reset dello stato
                self.stable_frames = 0
                self.unstable_frames = 0
            self.landmarks_visible = False
            return False, feedback

        # Verifica la stabilità dei landmark
        if landmarks_visible:
            self.stable_frames += 1
            self.unstable_frames = 0
            if self.stable_frames < self.required_stable_frames:
                return False, "Mantieni la posizione per iniziare l'esercizio..."
            self.landmarks_visible = True
        else:
            self.unstable_frames += 1
            if self.unstable_frames >= self.max_unstable_frames:
                self.stable_frames = 0
                self.landmarks_visible = False
                return False, "Riposizionati correttamente nella telecamera..."
            return False, feedback

        # Punti chiave per l'affondo
        hip_right = landmarks[24][:2]  # Anca destra
        knee_right = landmarks[26][:2]  # Ginocchio destro
        ankle_right = landmarks[28][:2]  # Caviglia destra
        hip_left = landmarks[23][:2]  # Anca sinistra
        knee_left = landmarks[25][:2]  # Ginocchio sinistro
        ankle_left = landmarks[27][:2]  # Caviglia sinistra

        # Calcolo angoli
        front_knee_angle = self._calculate_angle(hip_right, knee_right, ankle_right)
        back_knee_angle = self._calculate_angle(hip_left, knee_left, ankle_left)

        # Analisi della posizione
        if front_knee_angle > 160 and back_knee_angle > 160:  # Posizione eretta
            if self.position_state == 'down':
                self.rep_counter += 1
            self.position_state = 'up'
            self.feedback = 'Fai un passo avanti per iniziare l\'affondo'
            return True, self.feedback

        elif 85 <= front_knee_angle <= 95 and back_knee_angle < 120:  # Posizione affondo corretta
            self.position_state = 'down'
            self.feedback = 'Ottima posizione!'
            self.landmarks_visible = True
            return True, self.feedback

        else:  # Posizione non corretta
            self.position_state = 'down'
            if front_knee_angle < 85:
                self.feedback = 'Ginocchio anteriore troppo piegato'
            elif front_knee_angle > 95:
                self.feedback = 'Piega di più il ginocchio anteriore'
            self.landmarks_visible = True
            return False, self.feedback

    def _calculate_angle(self, p1, p2, p3):
        """Calcola l'angolo tra tre punti"""
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