import streamlit as st
import plotly.express as px
from langgraph.types import Command
from app.graph import graph
from app.database import (
    get_inspection_summary,
    get_defect_analytics,
    get_review_analytics,
    get_inspection_trends,
    get_inspection_history,
    get_detections_for_inspection,
    get_thread_id_for_inspection,
)


# --------------------------------------------------
# 1. Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="ForgeSight | Quality Analytics",
    page_icon="🚀",
    layout="wide",
)

st.title("🚀 ForgeSight")
st.subheader("Industrial Visual Inspection & Quality Analytics")

st.caption(
    "Monitor inspection decisions, defect detections, "
    "model confidence, and human-review activity."
)

st.divider()


# --------------------------------------------------
# 2. Load analytics from MySQL
# --------------------------------------------------

try:
    summary = get_inspection_summary()
    defect_data = get_defect_analytics()
    review_data = get_review_analytics()
    trend_data = get_inspection_trends()

except Exception as error:
    st.error("Unable to load analytics from the database.")
    st.exception(error)
    st.stop()


# --------------------------------------------------
# 3. Inspection overview
# --------------------------------------------------

st.header("Inspection Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Inspections",
        value=summary["total_inspections"],
    )

with col2:
    st.metric(
        label="Accepted",
        value=summary["accepted_inspections"],
    )

with col3:
    st.metric(
        label="Rejected",
        value=summary["rejected_inspections"],
    )

with col4:
    st.metric(
        label="Human Review",
        value=summary["inspections_sent_for_review"],
    )


# --------------------------------------------------
# 4. Human-review summary
# --------------------------------------------------

st.divider()
st.header("Human Review")

col1, col2 = st.columns(2)

with col1:
    st.metric(
        label="Pending Reviews",
        value=summary["pending_reviews"],
    )

with col2:
    st.metric(
        label="Completed Reviews",
        value=summary["completed_reviews"],
    )


# --------------------------------------------------
# 5. Defect analytics
# --------------------------------------------------

st.divider()
st.header("Defect Analytics")

if defect_data:
    import pandas as pd

    defect_df = pd.DataFrame(defect_data)

    left, right = st.columns(2)

    with left:
        st.subheader("Detections by Defect Class")

        fig_counts = px.bar(
            defect_df,
            x="class_name",
            y="detection_count",
            title="Number of Detected Defects",
            labels={
                "class_name": "Defect Class",
                "detection_count": "Detections",
            },
        )

        fig_counts.update_layout(
            xaxis_title="Defect Class",
            yaxis_title="Number of Detections",
        )

        st.plotly_chart(fig_counts, use_container_width=True)

    with right:
        st.subheader("Average Detection Confidence")

        fig_confidence = px.bar(
            defect_df,
            x="class_name",
            y="average_confidence",
            title="Average Confidence by Defect Class",
            labels={
                "class_name": "Defect Class",
                "average_confidence": "Average Confidence",
            },
        )

        fig_confidence.update_layout(
            xaxis_title="Defect Class",
            yaxis_title="Average Confidence",
            yaxis_range=[0, 1],
        )

        st.plotly_chart(
            fig_confidence,
            use_container_width=True,
        )

    st.subheader("Defect Statistics")
    st.dataframe(defect_df, use_container_width=True)

else:
    st.info(
        "No detections are stored in the database yet. "
        "Run an inspection to populate defect analytics."
    )

# --------------------------------------------------
# 7. Human-review analytics
# --------------------------------------------------

st.divider()
st.header("Human-Review Analytics")

if review_data:
    import pandas as pd

    review_df = pd.DataFrame(review_data)

    review_df["reviewer_decision"] = (
        review_df["reviewer_decision"]
        .fillna("Awaiting decision")
    )

    fig_reviews = px.bar(
        review_df,
        x="review_status",
        y="inspection_count",
        color="reviewer_decision",
        barmode="stack",
        title="Human-Review Status and Outcomes",
        labels={
            "review_status": "Review Status",
            "inspection_count": "Inspections",
            "reviewer_decision": "Reviewer Decision",
        },
    )

    st.plotly_chart(fig_reviews, use_container_width=True)

    st.subheader("Review Statistics")
    st.dataframe(review_df, use_container_width=True)

else:
    st.info("No human-review records are available yet.")


# --------------------------------------------------
# 8. Footer
# --------------------------------------------------

st.divider()
st.caption(
    "ForgeSight | YOLO-based defect detection, "
    "agentic inspection, and human-in-the-loop quality control"
)


st.divider()
st.header("Pending Human Reviews")

inspection_history = get_inspection_history()

pending_inspections = [
    inspection
    for inspection in inspection_history
    if inspection["review_status"] == "PENDING"
]

if not pending_inspections:
    st.success("No inspections are waiting for human review.")

else:
    st.write(f"Pending inspections: {len(pending_inspections)}")

    for inspection in pending_inspections:
        with st.expander(
            f"Sample: {inspection['sample_id']} | "
            f"Inspection: {inspection['inspection_id'][:8]}"
        ):
            st.write("**Inspection ID:**", inspection["inspection_id"])
            st.write("**Created at:**", inspection["created_at"])

            image_path = inspection["image_path"]

            if image_path:
                try:
                    st.image(image_path, caption="Inspection Image")
                except Exception:
                    st.warning(f"Could not display image: {image_path}")

            detections = get_detections_for_inspection(
                inspection["inspection_id"]
            )

            if detections:
                st.subheader("Detected Defects")
                st.dataframe(detections, use_container_width=True)
            else:
                st.info("No detections recorded for this inspection.")

            st.divider()
            st.subheader("Human Review")

            comments = st.text_area(
                "Reviewer comments",
                key=f"comments_{inspection['inspection_id']}",
            )

            col_accept, col_reject = st.columns(2)

            with col_accept:
                if st.button(
                    "Accept",
                    key=f"accept_{inspection['inspection_id']}",
                ):
                    thread_id = get_thread_id_for_inspection(
                        inspection["inspection_id"]
                    )

                    if not thread_id:
                        st.error("Workflow thread ID not found.")
                    else:
                        config = {
                            "configurable": {
                                "thread_id": thread_id
                            }
                        }

                        try:
                            graph.invoke(
                                Command(
                                    resume={
                                        "decision": "ACCEPT",
                                        "comments": comments or None,
                                    }
                                ),
                                config=config,
                            )

                            st.success("Inspection accepted.")
                            st.rerun()

                        except Exception as error:
                            st.error(
                                f"Failed to accept inspection: {error}"
                            )

            with col_reject:
                if st.button(
                    "Reject",
                    key=f"reject_{inspection['inspection_id']}",
                ):
                    thread_id = get_thread_id_for_inspection(
                        inspection["inspection_id"]
                    )

                    if not thread_id:
                        st.error("Workflow thread ID not found.")
                    else:
                        config = {
                            "configurable": {
                                "thread_id": thread_id
                            }
                        }

                        try:
                            graph.invoke(
                                Command(
                                    resume={
                                        "decision": "REJECT",
                                        "comments": comments or None,
                                    }
                                ),
                                config=config,
                            )

                            st.success("Inspection rejected.")
                            st.rerun()

                        except Exception as error:
                            st.error(
                                f"Failed to reject inspection: {error}"
                            )

