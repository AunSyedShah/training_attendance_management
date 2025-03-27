import streamlit as st
import pymongo
import pandas as pd
from datetime import datetime
import os

# MongoDB Connection based on environment
PRODUCTION = os.getenv("PRODUCTION", "FALSE").upper() == "TRUE"

if PRODUCTION:
    mongo_url = os.getenv("MONGODB_URL")  # Load from environment
else:
    mongo_url = "mongodb://localhost:27017/"

client = pymongo.MongoClient(mongo_url)
db = client["faculty_training"]
trainings_col = db["trainings"]
participants_col = db["participants"]
attendance_col = db["attendance"]

st.title("Faculty Training Management System")

# Sidebar navigation
menu = st.sidebar.radio("Navigation", [
                        "Add Training", "Manage Participants", "Track Attendance", "View Training Status"])

# Function to fetch trainings
def get_trainings():
    return list(trainings_col.find({}, {"_id": 0, "name": 1}))

# 1. Add Training
if menu == "Add Training":
    st.header("Add New Training")

    name = st.text_input("Training Name")
    description = st.text_area("Description")
    start_date = st.date_input("Start Date")

    if st.button("Add Training"):
        training_data = {
            "name": name,
            "description": description,
            "start_date": str(start_date),
            "created_at": datetime.now()
        }
        trainings_col.insert_one(training_data)
        st.success(f"Training '{name}' added successfully!")

# 2. Manage Participants
elif menu == "Manage Participants":
    st.header("Manage Participants")

    trainings = get_trainings()
    training_names = [t["name"] for t in trainings] if trainings else []

    selected_training = st.selectbox("Select Training", training_names)

    if selected_training:
        action = st.radio("Action", ["Add Participant", "Remove Participant"])

        if action == "Add Participant":
            participant_name = st.text_input("Participant Name")

            if st.button("Add Participant"):
                participant_data = {
                    "training_name": selected_training,
                    "name": participant_name,
                    "date_added": datetime.now(),
                    "status": "active"
                }
                participants_col.insert_one(participant_data)
                st.success(f"Added {participant_name} to {selected_training}")

        elif action == "Remove Participant":
            # Fetch currently enrolled participants
            enrolled_participants = list(participants_col.find(
                {"training_name": selected_training, "status": "active"},
                {"_id": 0, "name": 1}
            ))
            participant_names = [p["name"] for p in enrolled_participants]

            if participant_names:
                participant_to_remove = st.selectbox("Select Participant to Remove", participant_names)
                removal_reason = st.text_area("Reason for Removal")

                if st.button("Remove Participant"):
                    if removal_reason:
                        participants_col.update_one(
                            {"training_name": selected_training, "name": participant_to_remove},
                            {"$set": {
                                "status": "removed",
                                "date_removed": datetime.now(),
                                "removal_reason": removal_reason
                            }}
                        )
                        st.success(f"Removed {participant_to_remove} from {selected_training} for reason: {removal_reason}")
                    else:
                        st.warning("Please provide a reason for removal.")
            else:
                st.warning("No active participants in this training.")

# 3. Track Attendance
elif menu == "Track Attendance":
    st.header("Track Attendance")

    trainings = get_trainings()
    training_names = [t["name"] for t in trainings] if trainings else []

    selected_training = st.selectbox("Select Training", training_names)
    attendance_date = st.date_input("Select Date")

    if selected_training:
        participants = list(participants_col.find(
            {"training_name": selected_training, "status": "active"}, {"_id": 0, "name": 1}))
        participant_names = [p["name"] for p in participants]

        attendance_marked = st.multiselect("Mark Attendance", participant_names)

        if st.button("Save Attendance"):
            attendance_data = {
                "training_name": selected_training,
                "date": str(attendance_date),
                "present_participants": attendance_marked
            }
            attendance_col.insert_one(attendance_data)
            st.success("Attendance recorded successfully!")

# 4. View Training Status with Attendance Summary and Removed Participants
elif menu == "View Training Status":
    st.header("Training Status & Attendance Summary")

    trainings = get_trainings()
    training_names = [t["name"] for t in trainings] if trainings else []

    selected_training = st.selectbox("Select Training", training_names)
    start_date = st.date_input("Start Date")
    end_date = st.date_input("End Date")

    if selected_training and start_date <= end_date:
        # Fetch all participants (active + removed)
        participants = list(participants_col.find(
            {"training_name": selected_training},
            {"_id": 0, "name": 1, "status": 1, "date_removed": 1}
        ))

        participant_names = [p["name"] for p in participants]
        removed_participants = {p["name"]: p["date_removed"]
                                for p in participants if p["status"] == "removed"}

        # Fetch attendance records for the selected date range
        attendance_records = list(attendance_col.find(
            {"training_name": selected_training, "date": {"$gte": str(start_date), "$lte": str(end_date)}},
            {"_id": 0, "date": 1, "present_participants": 1}
        ))

        # Process attendance data
        attendance_summary = {name: {} for name in participant_names}
        date_list = pd.date_range(start=start_date, end=end_date).strftime('%Y-%m-%d').tolist()

        for record in attendance_records:
            record_date = record["date"]
            for name in participant_names:
                # If participant was removed, only show attendance before removal date
                if name in removed_participants and record_date > str(removed_participants[name].date()):
                    attendance_summary[name][record_date] = "-"
                else:
                    attendance_summary[name][record_date] = "P" if name in record["present_participants"] else "A"

        # Convert to DataFrame for display
        df_data = {"Faculty Name": participant_names}
        for date in date_list:
            df_data[date] = [attendance_summary[name].get(date, "-") for name in participant_names]

        attendance_df = pd.DataFrame(df_data)

        st.subheader("Attendance Summary")
        st.write(attendance_df)

        # Show removed participants with removal reason
        removed_participants_list = list(participants_col.find(
            {"training_name": selected_training, "status": "removed"},
            {"_id": 0, "name": 1, "date_removed": 1, "removal_reason": 1}
        ))

        if removed_participants_list:
            st.subheader("Removed Participants")
            removed_df = pd.DataFrame(removed_participants_list)
            removed_df.rename(columns={"name": "Faculty Name", "date_removed": "Date Removed", "removal_reason": "Reason"}, inplace=True)
            st.write(removed_df)
        else:
            st.info("No participants were removed from this training.")
    else:
        st.warning("Please select a valid training and date range.")


