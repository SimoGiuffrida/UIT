# pose_detector.py
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

        self.color_correct = (0, 255, 0)  # Colore per posizione corretta (verde)
        self.color_incorrect = (0, 0, 255)  # Colore per posizione errata (rosso)
        self.color_neutral = (255, 255, 0)  # Colore neutro (giallo/ciano)

    def find_pose(self, img, draw=True, exercise_success=None):
        # Elabora l'immagine per trovare i landmark della posa
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.pose.process(img_rgb)

        current_color = self.color_neutral
        if exercise_success is not None:
            current_color = self.color_correct if exercise_success else self.color_incorrect

        if draw:
            # Disegna un bordo colorato attorno al frame
            border_thickness = 10
            h, w = img.shape[:2]
            
            if exercise_success is not None:
                overlay = img.copy()
                half_thickness = border_thickness // 2
                pt1_border = (half_thickness, half_thickness)
                pt2_border = (w - half_thickness, h - half_thickness)
                
                cv2.rectangle(overlay, pt1_border, pt2_border, current_color, border_thickness)
                img = cv2.addWeighted(overlay, 0.3, img, 0.7, 0)

            # Disegna i landmark della posa
            if self.results.pose_landmarks:
                landmark_drawing_spec = self.mp_draw.DrawingSpec(
                    color=current_color, thickness=1, circle_radius=3
                )
                connection_drawing_spec = self.mp_draw.DrawingSpec(
                    color=current_color, thickness=2
                )
                self.mp_draw.draw_landmarks(
                    img,
                    self.results.pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec,
                    connection_drawing_spec
                )
        return img

    def find_position(self, img):
        # Estrae le coordinate dei landmark
        landmarks_list = {}
        if self.results and self.results.pose_landmarks:
            h, w, _ = img.shape
            for id, lm in enumerate(self.results.pose_landmarks.landmark):
                if lm.visibility > 0.3:  # Controlla la visibilità del landmark
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    landmarks_list[id] = [cx, cy, lm.z, lm.visibility]
        return landmarks_list

    def calculate_angle(self, p1, p2, p3):
        # Calcola l'angolo tra tre punti 2D
        p1, p2, p3 = np.array(p1[:2]), np.array(p2[:2]), np.array(p3[:2])
        radians = np.arctan2(p3[1]-p2[1], p3[0]-p2[0]) - \
                 np.arctan2(p1[1]-p2[1], p1[0]-p2[0])
        angle = np.abs(radians*180.0/np.pi)
        if angle > 180.0:
            angle = 360-angle
        return angle

    def release(self):
        # Rilascia le risorse di Mediapipe
        if hasattr(self, 'pose') and self.pose:
            self.pose.close()
            self.pose = None