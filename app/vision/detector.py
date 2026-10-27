from ultralytics import YOLO


model = YOLO("models/AreteVision_yolo.pt")


def detect(image_path: str):

    results = model(image_path)

    return results