import numpy as np
import mediapipe as mp

class GhostGuide:
    def __init__(self, animation_speed=1):
        self.mp_pose = mp.solutions.pose
        self.animation_frame = 0
        self.animation_speed = animation_speed
        self.frame_counter = 0
        self.animations = {
            'Squat': self._create_squat_animation(),
            'Lunge': self._create_lunge_animation()
        }
        self.reference_metrics = self.get_reference_metrics()

    def _create_squat_animation(self):
        """Crea la sequenza di animazione per lo Squat con proporzioni costanti e più landmark."""
        # POSE ERETTA (UP) - Proporzioni costanti
        pose_up = {
            # Testa
            0:  [0.5, 0.1, 0],   # Naso
            1:  [0.40, 0.08, 0], # Occhio interno sinistro
            2:  [0.45, 0.08, 0], # Occhio interno destro
            5:  [0.40, 0.9, 0], # Orecchio sinistro
            6:  [0.52, 0.9, 0], # Orecchio destro
            7:  [0.45, 0.15, 0], # Bocca sinistra (angolo)
            8:  [0.55, 0.15, 0], # Bocca destra (angolo)

            # Spalle
            11: [0.35, 0.25, 0], 12: [0.65, 0.25, 0],
            # Gomiti
            13: [0.3, 0.4, 0], 14: [0.7, 0.4, 0],
            # Polsi
            15: [0.25, 0.55, 0], 16: [0.75, 0.55, 0],
            # Dita (ad esempio, mignolo, indice, pollice)
            17: [0.23, 0.57, 0], 18: [0.77, 0.57, 0], # Mignolo
            19: [0.24, 0.58, 0], 20: [0.76, 0.58, 0], # Indice
            21: [0.25, 0.59, 0], 22: [0.75, 0.59, 0], # Pollice

            # Anche
            23: [0.35, 0.5, 0], 24: [0.65, 0.5, 0],
            # Ginocchia
            25: [0.35, 0.7, 0], 26: [0.65, 0.7, 0],
            # Caviglie
            27: [0.35, 0.9, 0], 28: [0.65, 0.9, 0],
            # Talloni (nuovi)
            29: [0.34, 0.92, 0], 30: [0.66, 0.92, 0],
            # Piedi (nuovi punti per completare lo scheletro)
            31: [0.35, 0.95, 0], 32: [0.65, 0.95, 0]
        }

        # POSE BASSA (DOWN) - Stesse proporzioni orizzontali
        pose_down = {
            # Testa
            0:  [0.5, 0.3, 0],
            1:  [0.48, 0.32, 0], 2:  [0.52, 0.32, 0],
            3:  [0.47, 0.33, 0], 4:  [0.53, 0.33, 0],
            5:  [0.48, 0.31, 0], 6:  [0.52, 0.31, 0],
            7:  [0.45, 0.35, 0], 8:  [0.55, 0.35, 0],

            # Spalle
            11: [0.35, 0.45, 0.1], 12: [0.65, 0.45, 0.1],
            # Gomiti
            13: [0.3, 0.55, 0.1], 14: [0.7, 0.55, 0.1],
            # Polsi
            15: [0.25, 0.65, 0.1], 16: [0.75, 0.65, 0.1],
            # Dita
            17: [0.23, 0.67, 0.1], 18: [0.77, 0.67, 0.1],
            19: [0.24, 0.68, 0.1], 20: [0.76, 0.68, 0.1],
            21: [0.25, 0.69, 0.1], 22: [0.75, 0.69, 0.1],

            # Anche
            23: [0.35, 0.65, 0.1], 24: [0.65, 0.65, 0.1],
            # Ginocchia
            25: [0.35, 0.8, 0], 26: [0.65, 0.8, 0],
            # Caviglie
            27: [0.35, 0.9, 0], 28: [0.65, 0.9, 0],
            # Talloni
            29: [0.34, 0.92, 0], 30: [0.66, 0.92, 0],
            # Piedi
            31: [0.35, 0.95, 0], 32: [0.65, 0.95, 0]
        }
        
        animation_frames = []
        num_frames = 30
        
        # Transizione da up a down
        for i in range(num_frames):
            alpha = i / (num_frames - 1)
            frame = {lm: np.array(pose_up[lm]) * (1 - alpha) + np.array(pose_down[lm]) * alpha 
                     for lm in pose_up} # Assicurati che l'interpolazione avvenga su tutti i landmark definiti in pose_up
            animation_frames.append(frame)
        
        # Transizione da down a up
        for i in range(num_frames):
            alpha = i / (num_frames - 1)
            frame = {lm: np.array(pose_down[lm]) * (1 - alpha) + np.array(pose_up[lm]) * alpha 
                     for lm in pose_up} # Stesso qui
            animation_frames.append(frame)

        return animation_frames
    
    def _create_lunge_animation(self):
        """Crea l'animazione per l'affondo con proporzioni costanti e più landmark."""
        # POSE INIZIALE (simmetrica)
        pose_start = {
            # Testa
            0:  [0.5, 0.1, 0],
            1:  [0.48, 0.12, 0], 2:  [0.52, 0.12, 0],
            3:  [0.47, 0.13, 0], 4:  [0.53, 0.13, 0],
            5:  [0.48, 0.11, 0], 6:  [0.52, 0.11, 0],
            7:  [0.45, 0.15, 0], 8:  [0.55, 0.15, 0],

            # Spalle
            11: [0.35, 0.25, 0], 12: [0.65, 0.25, 0],
            # Gomiti
            13: [0.3, 0.4, 0], 14: [0.7, 0.4, 0],
            # Polsi
            15: [0.25, 0.55, 0], 16: [0.75, 0.55, 0],
            # Dita
            17: [0.23, 0.57, 0], 18: [0.77, 0.57, 0],
            19: [0.24, 0.58, 0], 20: [0.76, 0.58, 0],
            21: [0.25, 0.59, 0], 22: [0.75, 0.59, 0],

            # Anche
            23: [0.35, 0.5, 0], 24: [0.65, 0.5, 0],
            # Ginocchia
            25: [0.35, 0.7, 0], 26: [0.65, 0.7, 0],
            # Caviglie
            27: [0.35, 0.9, 0], 28: [0.65, 0.9, 0],
            # Talloni
            29: [0.34, 0.92, 0], 30: [0.66, 0.92, 0],
            # Piedi
            31: [0.35, 0.95, 0], 32: [0.65, 0.95, 0]
        }

        # POSE AFFONDO (gamba destra avanti)
        pose_lunge = {
            # Testa leggermente più bassa
            0:  [0.5, 0.25, 0],
            1:  [0.48, 0.27, 0], 2:  [0.52, 0.27, 0],
            3:  [0.47, 0.28, 0], 4:  [0.53, 0.28, 0],
            5:  [0.48, 0.26, 0], 6:  [0.52, 0.26, 0],
            7:  [0.45, 0.30, 0], 8:  [0.55, 0.30, 0],

            # Spalle
            11: [0.4, 0.35, 0], 12: [0.6, 0.35, 0],
            # Gomiti (braccia leggermente piegate)
            13: [0.35, 0.45, 0], 14: [0.65, 0.45, 0],
            # Polsi
            15: [0.3, 0.55, 0], 16: [0.7, 0.55, 0],
            # Dita
            17: [0.28, 0.57, 0], 18: [0.72, 0.57, 0],
            19: [0.29, 0.58, 0], 20: [0.71, 0.58, 0],
            21: [0.30, 0.59, 0], 22: [0.70, 0.59, 0],

            # Anche
            23: [0.45, 0.55, 0], 24: [0.55, 0.55, 0],
            # Ginocchia
            25: [0.5, 0.75, 0], # Ginocchio destro avanti
            26: [0.6, 0.75, 0], # Ginocchio sinistro indietro
            # Caviglie
            27: [0.5, 0.9, 0],  # Caviglia destra avanti
            28: [0.65, 0.85, 0], # Caviglia sinistra indietro (più alta)
            # Talloni
            29: [0.49, 0.92, 0], # Tallone destro avanti
            30: [0.64, 0.87, 0], # Tallone sinistro indietro
            # Piedi
            31: [0.5, 0.95, 0],  # Punta piede destro avanti
            32: [0.65, 0.9, 0]   # Punta piede sinistro indietro
        }
        
        animation_frames = []
        num_frames = 30
        
        for i in range(num_frames):
            alpha = i / (num_frames - 1)
            frame = {lm: np.array(pose_start[lm]) * (1 - alpha) + np.array(pose_lunge[lm]) * alpha 
                     for lm in pose_start}
            animation_frames.append(frame)
        
        for i in range(num_frames):
            alpha = i / (num_frames - 1)
            frame = {lm: np.array(pose_lunge[lm]) * (1 - alpha) + np.array(pose_start[lm]) * alpha 
                     for lm in pose_start}
            animation_frames.append(frame)

        return animation_frames

    def get_reference_metrics(self):
        """
        Calcola le metriche di riferimento basate sull'altezza e sulla posizione delle caviglie.
        """
        p_up = self.animations['Squat'][0]
        # Calcola il centro delle caviglie come punto di ancoraggio
        ankle_center = (np.array(p_up[27]) + np.array(p_up[28])) / 2
        # Usa il naso come punto più alto della testa
        head_top = np.array(p_up[0])
        # Calcola l'altezza del corpo come distanza caviglie-testa
        body_height = np.linalg.norm(head_top - ankle_center)
        return {"anchor_center": ankle_center, "body_height": body_height}

    def update_animation_frame(self):
        self.frame_counter += 1
        if self.frame_counter % self.animation_speed == 0:
            self.animation_frame = (self.animation_frame + 1)
    
    def get_current_ghost_landmarks(self, exercise_type):
        anim = self.animations.get(exercise_type, [])
        if not anim: return None
        if self.animation_frame >= len(anim): self.animation_frame = 0
        return anim[self.animation_frame]

    def get_pose_connections(self):
        return self.mp_pose.POSE_CONNECTIONS

    def reset(self):
        self.animation_frame = 0
        self.frame_counter = 0