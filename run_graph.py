from app.graph import graph
import uuid 
from langgraph.types import Command 

thread_id = str(uuid.uuid4())

config = {
    "configurable": {
        "thread_id": thread_id
    }
}

result = graph.invoke(
    {
        "image_path": "data/NEU-DET/train/images/crazing/crazing_240.jpg",
        "detections": [],
        "inspection_history": [],
        "inspection_id": "",
        "defect_analysis": {},
        "quality_assessment": {},
        "decision": {},
        "policy_decision": {},
        "pattern_analysis": {},
    } , 
    config = config,
)

if result.get("__interrupt__"):

    print("Human review required!")

    for interruption in result["__interrupt__"]:
        print(interruption.value)

    # 3. Ask the reviewer for a decision
    decision = input("Enter ACCEPT or REJECT: ").strip().upper()
    comments = input("Enter comments: ").strip()

    # 4. Resume the interrupted graph
    result = graph.invoke(
        Command(
            resume={
                "decision": decision,
                "comments": comments or None,
            }
        ),
        config=config,
    )

    print("Review completed.")
    print(result.get("reviewer_decision"))

else:
    print("Inspection completed.")
    print(result.get("policy_decision"))



print("\n=== INSPECTION ID ===")
print(result["inspection_id"])

print("\n=== YOLO DETECTIONS ===")
print(result["detections"])

print("\n=== INSPECTION HISTORY ===")
print(result["inspection_history"])

print("\n=== DEFECT ANALYSIS ===")
print(result["defect_analysis"])

print("\n=== QUALITY ASSESSMENT ===")
print(result["quality_assessment"])

print("\n=== PATTERN ANALYSIS ===")
print(result["pattern_analysis"])

print("\n=== DECISION RECOMMENDATION ===")
print(result["decision"])

print("\n=== FINAL POLICY DECISION ===")
print(result["policy_decision"])