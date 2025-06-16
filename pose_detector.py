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
        self.results = None

        # Colori per la posa dell'utente
        self.color_correct = (0, 255, 0)      # Verde
        self.color_incorrect = (0, 0, 255)    # Rosso
        self.color_neutral = (255, 255, 0)    # Giallo/Ciano

        # Colore per i punti target successivi
        self.color_target = (0, 255, 255) # Giallo/Ciano per i punti target

    def find_pose(self, img):
        """
        Elabora l'immagine per trovare i landmark della posa, ma non disegna nulla.
        Salva i risultati nell'attributo 'self.results'.
        """
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.pose.process(img_rgb)
        return self.results

    def draw_user_pose(self, img, exercise_success=None):
        """
        Disegna i landmark dell'utente e un bordo colorato sull'immagine
        in base ai risultati salvati.
        """
        current_color = self.color_neutral
        if exercise_success is not None:
            current_color = self.color_correct if exercise_success else self.color_incorrect

        # Disegna un bordo colorato attorno al frame
        border_thickness = 10
        if exercise_success is not None:
            overlay = img.copy()
            h, w = img.shape[:2]
            cv2.rectangle(overlay, (0, 0), (w, h), current_color, border_thickness)
            img = cv2.addWeighted(overlay, 0.3, img, 0.7, 0)

        # Disegna i landmark della posa dell'utente
        if self.results and self.results.pose_landmarks:
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

    # Rimosso il metodo draw_ghost_pose

    def draw_squat_depth_guide(self, img, user_hip_y, optimal_hip_y):
        """
        Disegna una linea guida per la profondità dello squat se è troppo profondo.
        user_hip_y: Coordinata Y normalizzata dell'anca dell'utente.
        optimal_hip_y: Coordinata Y normalizzata dell'anca per la profondità ottimale.
        """
        if user_hip_y is None or optimal_hip_y is None:
            return img

        h, w, _ = img.shape

        # Converti le coordinate Y normalizzate in coordinate pixel
        user_y_px = int(user_hip_y * h)
        optimal_y_px = int(optimal_hip_y * h)

        # Definisci il punto di partenza e fine della linea (allineata al centro dell'immagine)
        line_x = w // 2

        # Disegna la linea se l'utente è andato troppo in basso (user_y_px è maggiore di optimal_y_px)
        if user_y_px > optimal_y_px:
            # Colore rosso per indicare la correzione necessaria
            line_color = (0, 0, 255) # Rosso
            line_thickness = 3

            # Punto iniziale (profondità ottimale)
            start_point = (line_x, optimal_y_px)
            # Punto finale (profondità attuale dell'utente)
            end_point = (line_x, user_y_px)

            # Disegna la linea
            cv2.line(img, start_point, end_point, line_color, line_thickness, cv2.LINE_AA)

            # Aggiungi una freccia alla fine della linea per indicare la direzione di risalita
            arrow_size = 10
            cv2.arrowedLine(img, start_point, end_point, line_color, line_thickness, cv2.LINE_AA, tipLength=0.3)

            # Puoi anche aggiungere del testo sulla linea o vicino ad essa
            text = "Risali!"
            text_pos = (line_x + 10, (optimal_y_px + user_y_px) // 2)
            cv2.putText(img, text, text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.7, line_color, 2, cv2.LINE_AA)

        return img

    # Rimosso il metodo draw_lunge_path_guide

    def draw_target_landmarks(self, img, target_landmarks_dict):
        """
        Disegna i punti chiave target sull'immagine.
        target_landmarks_dict: dizionario {landmark_id: [normalized_x, normalized_y]}
        """
        h, w, _ = img.shape
        target_radius = 10
        target_thickness = 2

        for lm_id, coords in target_landmarks_dict.items():
            x, y = int(coords[0] * w), int(coords[1] * h)
            # Disegna un cerchio per il punto target
            cv2.circle(img, (x, y), target_radius, self.color_target, target_thickness, cv2.LINE_AA)
            # Disegna una croce all'interno del cerchio per un target più chiaro
            cv2.line(img, (x - target_radius + 3, y), (x + target_radius - 3, y), self.color_target, target_thickness, cv2.LINE_AA)
            cv2.line(img, (x, y - target_radius + 3), (x, y + target_radius - 3), self.color_target, target_thickness, cv2.LINE_AA)
        return img


    def find_position(self, img):
        # Estrae le coordinate dei landmark
        landmarks_list = {}
        if self.results and self.results.pose_landmarks:
            h, w, _ = img.shape
            for id, lm in enumerate(self.results.pose_landmarks.landmark):
                if lm.visibility > 0.3:
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    # NOTA: qui salviamo anche le coordinate normalizzate (lm.x, lm.y)
                    landmarks_list[id] = [cx, cy, lm.z, lm.visibility, lm.x, lm.y]
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