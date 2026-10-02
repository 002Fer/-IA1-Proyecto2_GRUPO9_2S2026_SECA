import math
from collections import deque

class GestureRecognizer:

    def __init__(self):
        self.index_history = deque(maxlen=12)
        self.write_detected = False

        self.person_present = False
        self.person_detected_frames = 0
        self.person_missing_frames = 0

        self.proximity = "UNKNOWN"
        self.proximity_history = deque(maxlen=5)
        self.proximity_missing_frames = 0
        pass

    @staticmethod
    def distance(point1, point2):
        """
        Calcula la distancia euclidiana entre dos landmarks.
        """
        return math.sqrt(
            (point1.x - point2.x) ** 2 +
            (point1.y - point2.y) ** 2
        )

    @staticmethod
    def fingers_closed(hand_landmarks):
        """
        Verifica que índice, medio, anular y meñique estén recogidos.
        """
        wrist = hand_landmarks[0]

        index_tip = hand_landmarks[8]
        index_pip = hand_landmarks[6]

        middle_tip = hand_landmarks[12]
        middle_pip = hand_landmarks[10]

        ring_tip = hand_landmarks[16]
        ring_pip = hand_landmarks[14]

        pinky_tip = hand_landmarks[20]
        pinky_pip = hand_landmarks[18]

        index_closed = (
            GestureRecognizer.distance(index_tip, wrist)
            < GestureRecognizer.distance(index_pip, wrist)
        )
        middle_closed = (
            GestureRecognizer.distance(middle_tip, wrist)
            < GestureRecognizer.distance(middle_pip, wrist)
        )
        ring_closed = (
            GestureRecognizer.distance(ring_tip, wrist)
            < GestureRecognizer.distance(ring_pip, wrist)
        )
        pinky_closed = (
            GestureRecognizer.distance(pinky_tip, wrist)
            < GestureRecognizer.distance(pinky_pip, wrist)
        )
        return (
            index_closed
            and middle_closed
            and ring_closed
            and pinky_closed
        )

    @staticmethod
    def fingers_extended(hand_landmarks):
        """
        Verifica que índice, medio, anular y meñique
        estén extendidos.
        """
        wrist = hand_landmarks[0]

        index_tip = hand_landmarks[8]
        index_pip = hand_landmarks[6]

        middle_tip = hand_landmarks[12]
        middle_pip = hand_landmarks[10]

        ring_tip = hand_landmarks[16]
        ring_pip = hand_landmarks[14]

        pinky_tip = hand_landmarks[20]
        pinky_pip = hand_landmarks[18]

        index_extended = (
            GestureRecognizer.distance(index_tip, wrist)
            > GestureRecognizer.distance(index_pip, wrist)
        )
        middle_extended = (
            GestureRecognizer.distance(middle_tip, wrist)
            > GestureRecognizer.distance(middle_pip, wrist)
        )
        ring_extended = (
            GestureRecognizer.distance(ring_tip, wrist)
            > GestureRecognizer.distance(ring_pip, wrist)
        )
        pinky_extended = (
            GestureRecognizer.distance(pinky_tip, wrist)
            > GestureRecognizer.distance(pinky_pip, wrist)
        )
        return (
            index_extended
            and middle_extended
            and ring_extended
            and pinky_extended
        )

    @staticmethod
    def index_extended(hand_landmarks):
        """
        Verifica que el dedo índice esté extendido.
        """
        wrist = hand_landmarks[0]

        index_tip = hand_landmarks[8]
        index_pip = hand_landmarks[6]

        return (
            GestureRecognizer.distance(index_tip, wrist)
            > GestureRecognizer.distance(index_pip, wrist)
        )

    @staticmethod
    def other_fingers_closed(hand_landmarks):
        """
        Verifica que medio, anular y meñiqueestén recogidos.
        """
        wrist = hand_landmarks[0]

        middle_tip = hand_landmarks[12]
        middle_pip = hand_landmarks[10]

        ring_tip = hand_landmarks[16]
        ring_pip = hand_landmarks[14]

        pinky_tip = hand_landmarks[20]
        pinky_pip = hand_landmarks[18]

        middle_closed = (
            GestureRecognizer.distance(middle_tip, wrist)
            < GestureRecognizer.distance(middle_pip, wrist)
        )
        ring_closed = (
            GestureRecognizer.distance(ring_tip, wrist)
            < GestureRecognizer.distance(ring_pip, wrist)
        )

        pinky_closed = (
            GestureRecognizer.distance(pinky_tip, wrist)
            < GestureRecognizer.distance(pinky_pip, wrist)
        )
        return (
            middle_closed
            and ring_closed
            and pinky_closed
        )

    @staticmethod
    def is_thumb_up(hand_landmarks):
        wrist = hand_landmarks[0]

        thumb_tip = hand_landmarks[4]
        thumb_ip = hand_landmarks[3]
        thumb_mcp = hand_landmarks[2]

        fingers_closed = GestureRecognizer.fingers_closed(
            hand_landmarks
        )
        thumb_extended = (
            GestureRecognizer.distance(thumb_tip, wrist)
            > GestureRecognizer.distance(thumb_mcp, wrist)
        )
        thumb_points_up = (
            thumb_tip.y < thumb_ip.y
            and thumb_ip.y < thumb_mcp.y
        )
        return (
            fingers_closed
            and thumb_extended
            and thumb_points_up
        )

    @staticmethod
    def is_thumb_down(hand_landmarks):
        wrist = hand_landmarks[0]

        thumb_tip = hand_landmarks[4]
        thumb_ip = hand_landmarks[3]
        thumb_mcp = hand_landmarks[2]

        fingers_closed = GestureRecognizer.fingers_closed(
            hand_landmarks
        )
        thumb_extended = (
            GestureRecognizer.distance(thumb_tip, wrist)
            > GestureRecognizer.distance(thumb_mcp, wrist)
        )
        thumb_points_down = (
            thumb_tip.y > thumb_ip.y
            and thumb_ip.y > thumb_mcp.y
        )
        return (
            fingers_closed
            and thumb_extended
            and thumb_points_down
        )

    #Presencia de persona
    def update_person_presence(self, pose_landmarks):
        if pose_landmarks is not None and len(pose_landmarks) > 0:
            self.person_detected_frames += 1
            self.person_missing_frames = 0

            # Necesitamos varios frames consecutivos antes de confirmar la presencia.
            if self.person_detected_frames >= 5:
                self.person_present = True

        else:
            self.person_missing_frames += 1
            self.person_detected_frames = 0

            # No declaramos ausencia inmediatamente.
            if self.person_missing_frames >= 10:
                self.person_present = False

        return self.person_present


    def update_proximity(self, pose_landmarks):
        if pose_landmarks is None:
            self.proximity_missing_frames += 1
            # No cambiamos inmediatamente a UNKNOWN.
            if self.proximity_missing_frames < 5:
                return self.proximity
            self.proximity = "UNKNOWN"
            self.proximity_history.clear()

            return self.proximity

        if len(pose_landmarks) < 17:
            return self.proximity

        # Se recuperó la detección.
        self.proximity_missing_frames = 0

        left_shoulder = pose_landmarks[11]
        right_shoulder = pose_landmarks[12]

        shoulder_width = abs(
            left_shoulder.x - right_shoulder.x
        )

        if shoulder_width >= 0.30:
            current_proximity = "NEAR"

        elif shoulder_width >= 0.18:
            current_proximity = "MEDIUM"

        else:
            current_proximity = "FAR"

        self.proximity_history.append(
            current_proximity
        )

        counts = {}

        for value in self.proximity_history:
            counts[value] = counts.get(value, 0) + 1

        self.proximity = max(
            counts,
            key=counts.get
        )

        return self.proximity

    #Captura de cuerpo con brasos cruzados
    def is_arms_crossed(self, pose_landmarks):
        if pose_landmarks is None:
            return False

        if len(pose_landmarks) < 17:
            return False

        left_shoulder = pose_landmarks[11]
        right_shoulder = pose_landmarks[12]

        left_elbow = pose_landmarks[13]
        right_elbow = pose_landmarks[14]

        left_wrist = pose_landmarks[15]
        right_wrist = pose_landmarks[16]

        # Centro horizontal aproximado del torso
        center_x = (
            left_shoulder.x + right_shoulder.x
        ) / 2

        # Las muñecas deben acercarse al centro del torso
        wrists_near_center = (
            abs(left_wrist.x - center_x) < 0.25
            and
            abs(right_wrist.x - center_x) < 0.25
        )

        # Cada muñeca debe encontrarse hacia el lado
        # contrario respecto al centro del cuerpo.
        left_arm_crossed = (
            left_wrist.x < center_x
        )

        right_arm_crossed = (
            right_wrist.x > center_x
        )

        # Los codos normalmente quedan debajo
        # de los hombros cuando los brazos están cruzados.
        elbows_below_shoulders = (
            left_elbow.y > left_shoulder.y
            and
            right_elbow.y > right_shoulder.y
        )

        # Las muñecas deben estar debajo de los hombros.
        wrists_reasonable_height = (
            left_wrist.y > left_shoulder.y
            and
            right_wrist.y > right_shoulder.y
        )

        return (
            wrists_near_center
            and
            left_arm_crossed
            and
            right_arm_crossed
            and
            elbows_below_shoulders
            and
            wrists_reasonable_height
        )

    @staticmethod
    def is_hand_raised(hand_landmarks):
        """
        Detecta una mano abierta y levantada.
        """

        thumb_tip = hand_landmarks[4]
        thumb_ip = hand_landmarks[3]

        fingers_extended = GestureRecognizer.fingers_extended(
            hand_landmarks
        )

        thumb_extended = (
            GestureRecognizer.distance(
                thumb_tip,
                hand_landmarks[0]
            )
            > GestureRecognizer.distance(
                thumb_ip,
                hand_landmarks[0]
            )
        )

        return fingers_extended and thumb_extended

    #Funcion de escritura
    def update_write_gesture(self, hand_landmarks):
        if hand_landmarks is None:
            self.index_history.clear()
            self.write_detected = False
            return False

        if len(hand_landmarks) < 9:
            self.index_history.clear()
            self.write_detected = False
            return False

        index_tip = hand_landmarks[8]
        self.index_history.append(
            (index_tip.x, index_tip.y)
        )
        if len(self.index_history) < 5:
            return False
        movements = []

        for i in range(1, len(self.index_history)):
            previous = self.index_history[i - 1]
            current = self.index_history[i]

            dx = current[0] - previous[0]
            dy = current[1] - previous[1]
            movements.append((dx, dy))
        total_movement = sum(
            abs(dx) + abs(dy)
            for dx, dy in movements
        )
        if total_movement < 0.10:
            return False

        direction_changes = 0
        previous_dx = None

        for dx, dy in movements:
            if abs(dx) < 0.01:
                continue

            if previous_dx is not None:
                if (
                    dx > 0 and previous_dx < 0
                ) or (
                    dx < 0 and previous_dx > 0
                ):
                    direction_changes += 1
            previous_dx = dx

        if direction_changes >= 1:
            if not self.write_detected:
                self.write_detected = True
                return True
        return False


    @staticmethod
    def is_point_left(hand_landmarks):
        """
        Detecta un señalamiento claramente horizontal
        hacia la izquierda.
        """

        index_tip = hand_landmarks[8]
        index_pip = hand_landmarks[6]

        dx = index_tip.x - index_pip.x
        dy = index_tip.y - index_pip.y

        horizontal_direction = (
            dx < 0
            and abs(dx) > abs(dy) * 1.2
        )

        return (
            GestureRecognizer.index_extended(hand_landmarks)
            and GestureRecognizer.other_fingers_closed(hand_landmarks)
            and horizontal_direction
        )

    @staticmethod
    def is_point_right(hand_landmarks):
        """
        Detecta un señalamiento claramente horizontal
        hacia la derecha.
        """

        index_tip = hand_landmarks[8]
        index_pip = hand_landmarks[6]

        dx = index_tip.x - index_pip.x
        dy = index_tip.y - index_pip.y

        horizontal_direction = (
            dx > 0
            and abs(dx) > abs(dy) * 1.2
        )

        return (
            GestureRecognizer.index_extended(hand_landmarks)
            and GestureRecognizer.other_fingers_closed(hand_landmarks)
            and horizontal_direction
        )

    @staticmethod
    def is_index_up(hand_landmarks):
        """
        Detecta el gesto INDEX_UP.

        El índice apunta claramente hacia arriba.
        """

        index_tip = hand_landmarks[8]
        index_pip = hand_landmarks[6]

        dx = index_tip.x - index_pip.x
        dy = index_tip.y - index_pip.y

        vertical_direction = (
            dy < 0
            and abs(dy) > abs(dx) * 1.2
        )

        return (
            GestureRecognizer.index_extended(hand_landmarks)
            and GestureRecognizer.other_fingers_closed(hand_landmarks)
            and vertical_direction
        )

    @staticmethod
    def is_index_down(hand_landmarks):
        """
        Detecta el gesto INDEX_DOWN.

        El índice apunta claramente hacia abajo.
        """

        index_tip = hand_landmarks[8]
        index_pip = hand_landmarks[6]

        dx = index_tip.x - index_pip.x
        dy = index_tip.y - index_pip.y

        vertical_direction = (
            dy > 0
            and abs(dy) > abs(dx) * 1.2
        )

        return (
            GestureRecognizer.index_extended(hand_landmarks)
            and GestureRecognizer.other_fingers_closed(hand_landmarks)
            and vertical_direction
        )


    def recognize(self, hand_landmarks):
        """
        Reconocemos el gesto realizado por una mano.
        """

        if self.is_thumb_up(hand_landmarks):
            return {
                "gesture": "THUMBS_UP",
                "confidence": 1.0
            }

        if self.is_thumb_down(hand_landmarks):
            return {
                "gesture": "THUMBS_DOWN",
                "confidence": 1.0
            }

        if self.is_hand_raised(hand_landmarks):
            return {
                "gesture": "HAND_RAISED",
                "confidence": 1.0
            }

        if self.is_point_left(hand_landmarks):
            return {
                "gesture": "POINT_LEFT",
                "confidence": 1.0
            }

        if self.is_point_right(hand_landmarks):
            return {
                "gesture": "POINT_RIGHT",
                "confidence": 1.0
            }

        if self.is_index_up(hand_landmarks):
            return {
                "gesture": "INDEX_UP",
                "confidence": 1.0
            }

        if self.is_index_down(hand_landmarks):
            return {
                "gesture": "INDEX_DOWN",
                "confidence": 1.0
            }

        return {
            "gesture": "UNKNOWN",
            "confidence": 0.0
        }