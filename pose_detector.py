import cv2
import mediapipe as mp
import numpy as np

class PoseDetector:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5,
                                     min_tracking_confidence=0.5,
                                     enable_segmentation=False,
                                     model_complexity=1)
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_draw_styles = mp.solutions.drawing_styles
        
        # Colori per il feedback visivo
        self.color_correct = (0, 255, 0)  # Verde per posizione corretta
        self.color_incorrect = (0, 0, 255)  # Rosso per posizione errata
        self.color_neutral = (255, 255, 0)  # Giallo per posizione neutra
        
        # Configurazione per visualizzare solo i landmark del corpo
        self.landmark_drawing_spec = self.mp_draw.DrawingSpec(
            color=self.color_neutral,
            thickness=1,
            circle_radius=4
        )
        self.connection_drawing_spec = self.mp_draw.DrawingSpec(
            color=self.color_neutral,
            thickness=2
        )

    def find_pose(self, img, draw=True, exercise_success=None):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.pose.process(img_rgb)
        
        if self.results.pose_landmarks and draw:
            # Aggiorna i colori in base al feedback dell'esercizio
            color = self.color_neutral  # Colore predefinito
            if exercise_success is not None:
                color = self.color_correct if exercise_success else self.color_incorrect
            
            # Aggiorna le specifiche di disegno con il colore appropriato
            self.landmark_drawing_spec = self.mp_draw.DrawingSpec(
                color=color,
                thickness=2,
                circle_radius=4
            )
            self.connection_drawing_spec = self.mp_draw.DrawingSpec(
                color=color,
                thickness=2
            )
            
            # Aggiungi un bordo colorato all'immagine
            if exercise_success is not None:
                border_thickness = 10
                h, w = img.shape[:2]
                overlay = img.copy()
                cv2.rectangle(overlay, (0, 0), (w, h), color, border_thickness)
                img = cv2.addWeighted(overlay, 0.2, img, 0.8, 0)
            
            # Disegna i landmark del corpo
            body_landmarks = self.results.pose_landmarks
            self.mp_draw.draw_landmarks(
                img,
                body_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                self.landmark_drawing_spec,
                self.connection_drawing_spec)
        return img

    def find_position(self, img):
        landmarks_list = {}
        if self.results and self.results.pose_landmarks:
            # Lista dei landmark necessari per gli esercizi (spalle, anche, ginocchia, caviglie)
            body_landmarks = [11, 12, 23, 24, 25, 26, 27, 28]
            h, w, c = img.shape
            # Processa ogni landmark una sola volta
            for id in body_landmarks:
                if id < len(self.results.pose_landmarks.landmark):
                    lm = self.results.pose_landmarks.landmark[id]
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    # Salva il landmark nel dizionario solo se non è già presente
                    if id not in landmarks_list:
                        landmarks_list[id] = [cx, cy]
        return landmarks_list

    def calculate_angle(self, p1, p2, p3):
        """Calcola l'angolo tra tre punti"""
        p1 = np.array(p1)
        p2 = np.array(p2)
        p3 = np.array(p3)
        
        radians = np.arctan2(p3[1]-p2[1], p3[0]-p2[0]) - \
                 np.arctan2(p1[1]-p2[1], p1[0]-p2[0])
        angle = np.abs(radians*180.0/np.pi)
        
        if angle > 180.0:
            angle = 360-angle
            
        return angle

    def release(self):
        """Rilascia le risorse di MediaPipe"""
        if self.pose:
            self.pose.close()
            self.pose = None