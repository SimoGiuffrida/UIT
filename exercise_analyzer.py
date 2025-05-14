import numpy as np

class ExerciseAnalyzer:
    def __init__(self):
        self.rep_counter = 0
        self.position_state = None  # 'up' o 'down'
        self.feedback = ''

    def analyze_squat(self, landmarks):
        if not landmarks or len(landmarks) < 33:  # MediaPipe fornisce 33 punti
            return False, 'Posizione non rilevata'

        # Punti chiave per lo squat
        hip = landmarks[23][:2]  # Anca destra
        knee = landmarks[25][:2]  # Ginocchio destro
        ankle = landmarks[27][:2]  # Caviglia destra
        shoulder = landmarks[11][:2]  # Spalla destra

        # Calcolo angoli
        knee_angle = self._calculate_angle(hip, knee, ankle)
        hip_angle = self._calculate_angle(shoulder, hip, knee)

        # Analisi della posizione
        if knee_angle > 160:  # Posizione eretta
            if self.position_state == 'down':
                self.rep_counter += 1
            self.position_state = 'up'
            self.feedback = 'Piega le ginocchia per iniziare lo squat'
            return True, self.feedback

        elif 90 <= knee_angle <= 120:  # Posizione squat corretta
            self.position_state = 'down'
            if hip_angle < 90:
                self.feedback = 'Mantieni il busto più eretto'
            else:
                self.feedback = 'Buona posizione!'
            return True, self.feedback

        elif knee_angle < 90:  # Squat troppo profondo
            self.position_state = 'down'
            self.feedback = 'Squat troppo profondo, risali leggermente'
            return False, self.feedback

        return True, self.feedback

    def analyze_lunge(self, landmarks):
        if not landmarks or len(landmarks) < 33:
            return False, 'Posizione non rilevata'

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
            return True, self.feedback

        else:  # Posizione non corretta
            self.position_state = 'down'
            if front_knee_angle < 85:
                self.feedback = 'Ginocchio anteriore troppo piegato'
            elif front_knee_angle > 95:
                self.feedback = 'Piega di più il ginocchio anteriore'
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