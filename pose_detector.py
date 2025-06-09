import cv2
import mediapipe as mp
import numpy as np

class PoseDetector:
    def __init__(self, mode=False, model_complexity=1, smooth_landmarks=True, enable_segmentation=False, smooth_segmentation=True,
                 min_detection_confidence=0.5, min_tracking_confidence=0.5):
        # Inizializza i parametri per il rilevamento della posa
        self.mode = mode
        self.model_complexity = model_complexity
        self.smooth_landmarks = smooth_landmarks
        self.enable_segmentation = enable_segmentation
        self.smooth_segmentation = smooth_segmentation
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence

        # Configura MediaPipe per il rilevamento della posa
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(self.mode, self.model_complexity, self.smooth_landmarks,
                                     self.enable_segmentation, self.smooth_segmentation,
                                     self.min_detection_confidence, self.min_tracking_confidence)
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        # Colori per il feedback visivo
        self.color_neutral = (255, 255, 255)
        self.color_success = (0, 255, 0)
        self.color_error = (0, 0, 255)

    def find_pose(self, img, draw=True, exercise_success=None):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.pose.process(img_rgb)

        current_color = self.color_neutral
        if exercise_success is not None:
            current_color = self.color_correct if exercise_success else self.color_incorrect

        if draw:
            # Disegna il bordo colorato
            border_thickness = 10
            h, w = img.shape[:2]
            
            if exercise_success is not None: 
                overlay = img.copy()
                
                half_thickness = border_thickness // 2
                pt1_border = (half_thickness, half_thickness)
                pt2_border = (w - half_thickness, h - half_thickness)
                
                cv2.rectangle(overlay, pt1_border, pt2_border, current_color, border_thickness)
                img = cv2.addWeighted(overlay, 0.3, img, 0.7, 0) # Riduci alpha per bordo più tenue

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

    def find_position(self, img, draw=True):
        self.lm_list = []
        if self.results.pose_landmarks:
            for id, lm in enumerate(self.results.pose_landmarks.landmark):
                h, w, c = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                self.lm_list.append([id, cx, cy, lm.visibility])

        return self.lm_list

    def calculate_angle(self, img, p1, p2, p3, draw=True):
        x1, y1 = self.lm_list[p1][1:3]
        x2, y2 = self.lm_list[p2][1:3]
        x3, y3 = self.lm_list[p3][1:3]

        angle = math.degrees(math.atan2(y3 - y2, x3 - x2) -
                           math.atan2(y1 - y2, x1 - x2))
        if angle < 0:
            angle += 360
        if angle > 180:
            angle = 360 - angle

        return angle

    def release(self):
        if hasattr(self, 'pose') and self.pose:
            self.pose.close()
            self.pose = None