import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import pandas as pd
import os

# Read MongoDB URL from environment variable
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")

# MongoDB Connection
client = MongoClient(MONGODB_URL)
db = client["training_db"]
trainings_collection = db["trainings"]
participants_collection = db["participants"]
attendance_collection = db["attendance"]

# Streamlit App
st.title("Training Attendance Management")

# Sidebar Navigation
menu = [
    "Manage Trainings",
    "Manage Participants",
    "Assign Participants to Training",
    "Track Attendance",
    "Training Status"
]
choice = st.sidebar.selectbox("Menu", menu)

# --- TRAINING MANAGEMENT ---
if choice == "Manage Trainings":
    st.subheader("Training Management")

    action = st.radio("Select Action", ["Create", "View", "Edit", "Delete"])

    if action == "Create":
        st.subheader("Start New Training")
        training_name = st.text_input("Training Name")
        trainer_name = st.text_input("Trainer Name")
        start_date = st.date_input("Start Date", datetime.today())
        training_days = st.multiselect(
            "Select Training Days",
            ["Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday"]
        )

        if st.button("Save Training"):
            if training_name and trainer_name and training_days:
                training = {
                    "training_name": training_name,
                    "trainer_name": trainer_name,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "training_days": training_days,
                    "participants": []  # Empty list for participants
                }
                trainings_collection.insert_one(training)
                st.success("Training Added Successfully")
            else:
                st.warning("Please fill all fields")

    elif action == "View":
        st.subheader("List of Trainings")
        trainings = list(trainings_collection.find())

        if not trainings:
            st.write("No trainings found.")

        for training in trainings:
            st.write(
                f"**Training Name:** {training.get('training_name', 'N/A')}")
            st.write(f"**Trainer:** {training.get('trainer_name', 'N/A')}")
            st.write(f"**Start Date:** {training.get('start_date', 'N/A')}")
            st.write(
                f"**Days:** {', '.join(training.get('training_days', []))}")
            st.write(
                f"**Participants:** {', '.join(training.get('participants', []))}")
            st.write("---")

    elif action == "Edit":
        st.subheader("Edit Training")
        training_list = list(trainings_collection.find())
        training_names = [t['training_name'] for t in training_list]

        selected_training = st.selectbox("Select Training", training_names)

        if selected_training:
            training_data = trainings_collection.find_one(
                {"training_name": selected_training})

            new_training_name = st.text_input(
                "Training Name", training_data["training_name"])
            new_trainer_name = st.text_input(
                "Trainer Name", training_data["trainer_name"])
            new_start_date = st.date_input("Start Date", datetime.strptime(
                training_data["start_date"], "%Y-%m-%d"))
            new_training_days = st.multiselect(
                "Training Days",
                ["Monday", "Tuesday", "Wednesday", "Thursday",
                    "Friday", "Saturday", "Sunday"],
                default=training_data["training_days"]
            )

            if st.button("Update Training"):
                trainings_collection.update_one(
                    {"training_name": selected_training},
                    {"$set": {
                        "training_name": new_training_name,
                        "trainer_name": new_trainer_name,
                        "start_date": new_start_date.strftime("%Y-%m-%d"),
                        "training_days": new_training_days
                    }}
                )
                st.success("Training Updated Successfully")

    elif action == "Delete":
        st.subheader("Delete Training")
        training_list = list(trainings_collection.find())
        training_names = [t['training_name'] for t in training_list]

        selected_training = st.selectbox("Select Training", training_names)

        if st.button("Delete Training"):
            trainings_collection.delete_one(
                {"training_name": selected_training})
            st.warning("Training Deleted")

# --- PARTICIPANT MANAGEMENT ---
elif choice == "Manage Participants":
    st.subheader("Participant Management")

    action = st.radio("Select Action", ["Add", "View", "Edit", "Remove"])

    if action == "Add":
        st.subheader("Add Participant")
        participant_name = st.text_input("Participant Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone Number")

        if st.button("Save Participant"):
            if participant_name and email and phone:
                participant = {
                    "participant_name": participant_name,
                    "email": email,
                    "phone": phone
                }
                participants_collection.insert_one(participant)
                st.success("Participant Added Successfully")
            else:
                st.warning("Please fill all fields")

    elif action == "View":
        st.subheader("List of Participants")
        participants = list(participants_collection.find())

        if not participants:
            st.write("No participants found.")

        for participant in participants:
            st.write(f"**Name:** {participant.get('participant_name', 'N/A')}")
            st.write(f"**Email:** {participant.get('email', 'N/A')}")
            st.write(f"**Phone:** {participant.get('phone', 'N/A')}")
            st.write("---")

    elif action == "Edit":
        st.subheader("Edit Participant")
        participant_list = list(participants_collection.find())
        participant_names = [p['participant_name'] for p in participant_list]

        selected_participant = st.selectbox(
            "Select Participant", participant_names)

        if selected_participant:
            participant_data = participants_collection.find_one(
                {"participant_name": selected_participant})

            new_name = st.text_input(
                "Participant Name", participant_data["participant_name"])
            new_email = st.text_input("Email", participant_data["email"])
            new_phone = st.text_input(
                "Phone Number", participant_data["phone"])

            if st.button("Update Participant"):
                participants_collection.update_one(
                    {"participant_name": selected_participant},
                    {"$set": {
                        "participant_name": new_name,
                        "email": new_email,
                        "phone": new_phone
                    }}
                )
                st.success("Participant Updated Successfully")

    elif action == "Remove":
        st.subheader("Remove Participant")
        participant_list = list(participants_collection.find())
        participant_names = [p['participant_name'] for p in participant_list]

        selected_participant = st.selectbox(
            "Select Participant", participant_names)

        if st.button("Remove Participant"):
            participants_collection.delete_one(
                {"participant_name": selected_participant})
            st.warning("Participant Removed")

# --- ASSIGN PARTICIPANTS TO TRAININGS ---
elif choice == "Assign Participants to Training":
    st.subheader("Assign Participants")

    training_list = list(trainings_collection.find())
    training_names = [t['training_name'] for t in training_list]

    participant_list = list(participants_collection.find())
    participant_names = [p['participant_name'] for p in participant_list]

    selected_training = st.selectbox("Select Training", training_names)
    selected_participants = st.multiselect(
        "Select Participants", participant_names)

    if st.button("Assign"):
        trainings_collection.update_one(
            {"training_name": selected_training},
            {"$addToSet": {"participants": {"$each": selected_participants}}}
        )
        st.success("Participants Assigned Successfully")


# --- TRACK ATTENDANCE ---
if choice == "Track Attendance":
    st.subheader("Mark Attendance")

    training_list = list(trainings_collection.find())
    training_names = [t['training_name'] for t in training_list]

    selected_training = st.selectbox("Select Training", training_names)

    if selected_training:
        training_data = trainings_collection.find_one(
            {"training_name": selected_training})
        participant_names = training_data.get("participants", [])

        selected_date = st.date_input("Select Date", datetime.today())

        if participant_names:
            attendance_status = {}
            for participant in participant_names:
                attendance_status[participant] = st.checkbox(
                    f"Present: {participant}", value=True)

            if st.button("Save Attendance"):
                attendance_record = {
                    "training_name": selected_training,
                    "date": selected_date.strftime("%Y-%m-%d"),
                    "attendance": attendance_status
                }
                attendance_collection.insert_one(attendance_record)
                st.success("Attendance Saved Successfully")
        else:
            st.warning("No participants assigned to this training.")

# --- TRAINING STATUS PAGE ---
if choice == "Training Status":
    st.subheader("Training Status Overview")

    training_list = list(trainings_collection.find())
    training_names = [t['training_name'] for t in training_list]

    if training_names:
        selected_training = st.selectbox("Select Training", training_names)

        if selected_training:
            training_data = trainings_collection.find_one({"training_name": selected_training})
            participant_names = training_data.get("participants", [])

            st.write(f"**Training Name:** {training_data.get('training_name', 'N/A')}")
            st.write(f"**Trainer:** {training_data.get('trainer_name', 'N/A')}")
            st.write(f"**Days:** {', '.join(training_data.get('training_days', []))}")

            # Fetch attendance records for the selected training
            attendance_records = list(attendance_collection.find({"training_name": selected_training}))

            if attendance_records:
                # Extract unique dates
                dates = sorted(set(record["date"] for record in attendance_records))

                # Create a dictionary to store attendance in table format
                attendance_data = {participant: {date: "A" for date in dates} for participant in participant_names}

                for record in attendance_records:
                    date = record["date"]
                    for participant, status in record["attendance"].items():
                        attendance_data[participant][date] = "P" if status else "A"

                # Convert dictionary to DataFrame
                attendance_df = pd.DataFrame.from_dict(attendance_data, orient="index", columns=dates)
                attendance_df.index.name = "Participant Name"

                # Display the table
                st.write("### Attendance Records")
                st.dataframe(attendance_df)
            else:
                st.write("No attendance records available.")
    else:
        st.write("No trainings available.")
