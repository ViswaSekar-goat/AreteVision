from ultralytics import YOLO


model = YOLO("yolo26m.pt")




model.train(
    data="data/NEU-DET/data.yaml",

    epochs=30,
    imgsz=640,
    batch=8,

    device=0,
    workers=2,

    patience=10,
    amp=True,

    project="runs/forgeSight",
    name="yolo26m_v1",
)