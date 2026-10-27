import mysql.connector


def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="forgesight_admin",
        password="admin",
        database="forgesight",
    )

def update_inspection_action(
    inspection_id: str,
    action: str,
):
    connection = get_connection()
    cursor = connection.cursor()

    if action == "HUMAN_REVIEW":
        review_status = "PENDING"
    else:
        review_status = "NOT_REQUIRED"

    query = """
        UPDATE inspections
        SET final_action = %s,
            review_status = %s
        WHERE inspection_id = %s
    """

    try:
        cursor.execute(
            query,
            (action, review_status, inspection_id),
        )

        if cursor.rowcount != 1:
            raise ValueError(
                f"Expected one inspection record for {inspection_id}"
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

def create_inspection(inspection_id : str , sample_id : str , image_path : str):

    connection = get_connection()
    cursor = connection.cursor()

    query = """

    INSERT INTO inspections (
        inspection_id,
        sample_id,
        image_path
    )

    VALUES(%s , %s , %s)

    """

    cursor.execute(
        query , (inspection_id , sample_id , image_path) ,
    )

    connection.commit()

    cursor.close()
    connection.close()


def save_detection(
    inspection_id: str,
    class_name: str,
    confidence: float,
    bbox: list[float],
):
    connection = get_connection()
    cursor = connection.cursor()

    query = """
        INSERT INTO detections (
            inspection_id,
            class_name,
            confidence,
            x1,
            y1,
            x2,
            y2
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    cursor.execute(
        query,
        (
            inspection_id,
            class_name,
            confidence,
            bbox[0],
            bbox[1],
            bbox[2],
            bbox[3],
        ),
    )

    connection.commit()

    cursor.close()
    connection.close()


def get_defect_history(class_name: str):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            class_name,
            COUNT(*) AS occurrence_count,
            AVG(confidence) AS average_confidence
        FROM detections
        WHERE class_name = %s
        GROUP BY class_name
    """

    cursor.execute(query, (class_name,))

    result = cursor.fetchone()

    cursor.close()
    connection.close()

    return result

def get_all_defect_history():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            class_name,
            COUNT(DISTINCT inspection_id) AS inspection_count,
            AVG(confidence) AS average_confidence
        FROM detections
        GROUP BY class_name
        ORDER BY inspection_count DESC
    """

    cursor.execute(query)

    results = cursor.fetchall()

    cursor.close()
    connection.close()

    return results

def get_inspection_history():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            inspection_id,
            sample_id,
            image_path,
            created_at,
            final_action,
            review_status,
            reviewer_decision,
            reviewer_comments,
            reviewed_at
        FROM inspections
        ORDER BY created_at DESC
    """

    cursor.execute(query)

    results = cursor.fetchall()

    cursor.close()
    connection.close()

    return results