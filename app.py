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
users_collection = db["users"]
trainings_collection = db["trainings"]
participants_collection = db["participants"]
attendance_collection = db["attendance"]

st.set_page_config(page_title="Training Management System", layout="wide")

# Initialize session state for authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- CHECK CREDENTIALS FROM DATABASE ---


def authenticate(username, password):
    user = users_collection.find_one(
        {"username": username, "password": password})
    return user is not None

# --- LOGIN PAGE ---


def login_page():
    st.title("Login to Training Management System")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if authenticate(username, password):
            st.session_state.authenticated = True
            st.session_state.username = username  # Store username
            st.rerun()
        else:
            st.error("Invalid username or password")


# --- MAIN APPLICATION ---
if not st.session_state.authenticated:
    login_page()
else:
    # Streamlit App
    st.title("Training Attendance Management")

    # Sidebar Navigation
    menu = [
        "Manage Trainings",
        "Manage Participants",
        "Assign/Remove Participants to Training",
        "Track Attendance",
        "Training Status"
    ]
    choice = st.sidebar.selectbox("Menu", menu)
    # --- LOGOUT BUTTON ---
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.pop("username", None)  # Remove stored username
        st.rerun()


    # --- TRAINING MANAGEMENT ---
    if choice == "Manage Trainings":
        st.subheader("Training Management")

        action = st.radio("Select Action", [
                          "Create", "View", "Edit", "Delete"])

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
                st.write(
                    f"**Start Date:** {training.get('start_date', 'N/A')}")
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

        action = st.radio("Select Action", ["Add", "View", "Edit", "Remove", "Bulk Upload"])

        # --- ADD BULK UPLOAD OPTION ---
        if action == "Bulk Upload":
            st.subheader("Upload Participants (Bulk Upload)")

            # Display the expected column headers for the uploaded file
            st.write("### Expected Column Headers for the File:")
            st.write("1. **participant_name**: Name of the participant")
            st.write("2. **email**: Email of the participant")
            st.write("3. **phone**: Phone number of the participant")

            file = st.file_uploader("Upload an Excel/CSV file", type=["csv", "xlsx"])

            if file:
                try:
                    # Reading the file content with pandas
                    if file.name.endswith(".csv"):
                        df = pd.read_csv(file)
                    elif file.name.endswith(".xlsx"):
                        df = pd.read_excel(file)

                    # Check if the required columns exist
                    if 'participant_name' in df.columns and 'email' in df.columns and 'phone' in df.columns:
                        # Insert participants into the MongoDB database
                        for _, row in df.iterrows():
                            participant = {
                                "participant_name": row["participant_name"],
                                "email": row["email"],
                                "phone": row["phone"]
                            }
                            participants_collection.insert_one(participant)

                        st.success("Participants uploaded and added successfully!")
                    else:
                        st.error("The file must contain 'participant_name', 'email', and 'phone' columns.")

                except Exception as e:
                    st.error(f"Error processing file: {e}")

        elif action == "Add":
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
                st.write(
                    f"**Name:** {participant.get('participant_name', 'N/A')}")
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
    elif choice == "Assign/Remove Participants to Training":
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
        
        st.markdown("---")
        st.subheader("Remove Participants from Training")

        participants_in_training = trainings_collection.find_one(
            {"training_name": selected_training}
        ).get("participants", [])

        participants_to_remove = st.multiselect("Select Participants to Remove", participants_in_training)
        removal_reason = st.text_input("Reason for Removal")

        if st.button("Remove Selected Participants"):
            if participants_to_remove and removal_reason:
                # Remove from training
                trainings_collection.update_one(
                    {"training_name": selected_training},
                    {"$pull": {"participants": {"$in": participants_to_remove}}}
                )

                # Record the removals with reason and timestamp
                removal_records = [{
                    "training_name": selected_training,
                    "participant_name": name,
                    "reason": removal_reason,
                    "removed_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                } for name in participants_to_remove]

                db["removals"].insert_many(removal_records)

                st.success("Participants removed and recorded successfully.")
            elif not removal_reason:
                st.warning("Please enter a reason for removal.")
            else:
                st.warning("Please select participants to remove.")
        
        st.markdown("---")
        st.subheader("Past Removals")

        removal_logs = list(db["removals"].find({"training_name": selected_training}))

        if removal_logs:
            removal_df = pd.DataFrame(removal_logs)
            removal_df.drop(columns=["_id"], inplace=True, errors="ignore")
            st.dataframe(removal_df, use_container_width=True)
        else:
            st.write("No removals recorded for this training.")




    # --- TRACK ATTENDANCE ---
    if choice == "Track Attendance":
        st.subheader("Mark Attendance")

        # Fetch the list of trainings and participants
        training_list = list(trainings_collection.find())
        training_names = [t['training_name'] for t in training_list]

        selected_training = st.selectbox("Select Training", training_names)

        if selected_training:
            # Fetch training data and participants for the selected training
            training_data = trainings_collection.find_one({"training_name": selected_training})
            # Get currently assigned participants
            participant_names = training_data.get("participants", [])

            # Get names of previously removed participants
            removed_participants = db["removals"].find(
                {"training_name": selected_training}, {"participant_name": 1}
            )
            removed_names = {entry["participant_name"] for entry in removed_participants}

            # Filter out removed ones
            participant_names = [p for p in participant_names if p not in removed_names]


            # Select the date for attendance marking
            selected_date = st.date_input("Select Date", datetime.today())

            # Input for the topic of the day
            topic_of_the_day = st.text_input("Topic for the Day")

            if participant_names:
                attendance_status = {}
                # Record the attendance status for each participant
                for participant in participant_names:
                    attendance_status[participant] = st.checkbox(f"Present: {participant}", value=True)

                if st.button("Save Attendance"):
                    if topic_of_the_day:  # Ensure that topic is provided
                        # Create attendance record to store in the database
                        attendance_record = {
                            "training_name": selected_training,
                            "date": selected_date.strftime("%Y-%m-%d"),
                            "topic": topic_of_the_day,
                            "attendance": attendance_status
                        }
                        # Insert the record into the attendance collection
                        attendance_collection.insert_one(attendance_record)
                        st.success("Attendance and Topic Saved Successfully")
                    else:
                        st.warning("Please provide a topic for the day.")
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
                training_data = trainings_collection.find_one(
                    {"training_name": selected_training})
                participant_names = training_data.get("participants", [])

                st.write(
                    f"**Training Name:** {training_data.get('training_name', 'N/A')}")
                st.write(
                    f"**Trainer:** {training_data.get('trainer_name', 'N/A')}")
                st.write(
                    f"**Days:** {', '.join(training_data.get('training_days', []))}")

                # Fetch attendance records for the selected training
                attendance_records = list(attendance_collection.find(
                    {"training_name": selected_training}))

                if attendance_records:
                    # Map each date to its topic
                    date_topic_map = {}
                    for record in attendance_records:
                        date = record["date"]
                        topic = record.get("topic", "")
                        date_topic_map[date] = topic

                    # Sort dates
                    dates = sorted(date_topic_map.keys())

                    # Create attendance matrix with raw dates as keys
                    attendance_data = {
                        participant: {date: "A" for date in dates} for participant in participant_names
                    }

                    for record in attendance_records:
                        date = record["date"]
                        for participant, status in record["attendance"].items():
                            attendance_data[participant][date] = "P" if status else "A"

                    # Create DataFrame using raw date keys first
                    attendance_df = pd.DataFrame.from_dict(
                        attendance_data, orient="index"
                    )
                    attendance_df = attendance_df[dates]  # Ensure column order

                    # Rename columns to include topics
                    columns_with_topics = {
                        date: f"{date}\n({date_topic_map[date]})" if date_topic_map[date] else date
                        for date in dates
                    }
                    attendance_df.rename(columns=columns_with_topics, inplace=True)

                    attendance_df.index.name = "Participant Name"
                    # Function to highlight absentees
                    def highlight_absentees(val):
                        if val == "A":
                            return 'background-color: #ffcccc; color: red; font-weight: bold;'
                        return ''

                    # Apply the style
                    styled_df = attendance_df.style.applymap(highlight_absentees)

                    # Display the styled DataFrame
                    st.write("### Attendance Records")
                    st.dataframe(styled_df, use_container_width=True)
                else:
                    st.write("No attendance records available.")
        else:
            st.write("No trainings available.")
