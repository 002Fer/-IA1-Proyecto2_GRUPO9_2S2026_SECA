import cv2

from vision.camera import Camera


def main():
    camera = Camera(camera_index=0)

    try:
        camera.open()

        print("Cámara abierta correctamente.")
        print("Presiona Q para salir.")

        while True:
            frame = camera.read()

            cv2.imshow("AURA - Prueba de camara", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

# import cv2

# def main():
#     camera_index = 0

#     camera = cv2.VideoCapture(camera_index)

#     if not camera.isOpened():
#         print(f"No se pudo abrir la cámara con índice {camera_index}")
#         return

#     print(f"Cámara {camera_index} abierta correctamente.")
#     print("Presiona Q para salir.")

#     while True:
#         success, frame = camera.read()

#         if not success:
#             print("No se pudo obtener un frame.")
#             break

#         cv2.imshow("AURA - Prueba de camara", frame)

#         key = cv2.waitKey(1) & 0xFF

#         if key == ord("q"):
#             break

#     camera.release()
#     cv2.destroyAllWindows()

# if __name__ == "__main__":
#     main()

