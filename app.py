import streamlit as st
import pymongo
import bcrypt
import pandas as pd
from datetime import datetime
import os

# MongoDB Connection
PRODUCTION = os.getenv("PRODUCTION", "FALSE").upper() == "TRUE"
mongo_url = os.getenv("MONGODB_URL") if PRODUCTION else "mongodb://localhost:27017/"
client = pymongo.MongoClient(mongo_url)
db = client["faculty_training"]
users_col = db["users"]
trainings_col = db["trainings"]
participants_col = db["participants"]
attendance_col = db["attendance"]

# Session state for authentication
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# Function to hash passwords
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# Function to check passwords
def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed)

# Function to authenticate admin
def authenticate(username, password):
    user = users_col.find_one({"username": username})
    if user and check_password(password, user["password"]):
        st.session_state["authenticated"] = True
        return True
    return False

# Function to create an admin user (Run once)
def create_admin():
    if not users_col.find_one({"username": "admin"}):
        hashed_pw = hash_password("admin123")  # Default password
        users_col.insert_one({"username": "admin", "password": hashed_pw})
        st.success("Admin created! (Username: admin, Password: admin123)")
    else:
        st.warning("Admin already exists!")

# Login page
def login():
    st.title("🔒 Admin Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_button = st.button("Login")

    if login_button:
        if authenticate(username, password):
            st.success("✅ Login Successful! Redirecting...")
            st.rerun()
        else:
            st.error("❌ Invalid Username or Password!")

# Logout function
def logout():
    st.session_state["authenticated"] = False
    st.rerun()

# Function to fetch trainings
def get_trainings():
    return list(trainings_col.find({}, {"_id": 0, "name": 1, "trainer_name": 1, "start_date": 1}))

# Function to export training status to Excel
def export_to_excel(dataframe, filename="training_status.xlsx"):
    dataframe.to_excel(filename, index=False)
    with open(filename, "rb") as file:
        st.download_button(label="📥 Download Excel", data=file, file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Main application
if not st.session_state["authenticated"]:
    login()
else:
    st.sidebar.button("🚪 Logout", on_click=logout)
    
    st.title("🏫 Faculty Training Management System")
    
    menu = st.sidebar.radio("Navigation", [
        "Add Training", "Manage Trainings", "Manage Participants", "Track Attendance", "View Training Status"
    ])
    
    # 1. Add Training
    if menu == "Add Training":
        st.header("Add New Training")

        name = st.text_input("Training Name")
        trainer_name = st.text_input("Trainer Name")
        description = st.text_area("Description")
        start_date = st.date_input("Start Date")

        if st.button("Add Training"):
            training_data = {
                "name": name,
                "trainer_name": trainer_name,
                "description": description,
                "start_date": str(start_date),
                "created_at": datetime.now()
            }
            trainings_col.insert_one(training_data)
            st.success(f"Training '{name}' added successfully!")

    # 2. Manage Trainings (Update/Delete)
    elif menu == "Manage Trainings":
        st.header("Manage Trainings")
        trainings = get_trainings()
        training_names = [t["name"] for t in trainings] if trainings else []
        
        selected_training = st.selectbox("Select Training", training_names)
        
        if selected_training:
            training = trainings_col.find_one({"name": selected_training})
            new_name = st.text_input("Training Name", training["name"])
            new_trainer = st.text_input("Trainer Name", training.get("trainer_name", ""))
            new_description = st.text_area("Description", training.get("description", ""))
            new_start_date = st.date_input("Start Date", datetime.strptime(training["start_date"], "%Y-%m-%d"))
            
            if st.button("Update Training"):
                trainings_col.update_one(
                    {"name": selected_training},
                    {"$set": {
                        "name": new_name,
                        "trainer_name": new_trainer,
                        "description": new_description,
                        "start_date": str(new_start_date)
                    }}
                )
                st.success("Training updated successfully!")
            
            if st.button("Delete Training"):
                trainings_col.delete_one({"name": selected_training})
                st.success("Training deleted successfully!")

    # 2. Manage Participants (Add/Remove)
    elif menu == "Manage Participants":
        st.header("Manage Participants")

        trainings = get_trainings()
        training_names = [t["name"] for t in trainings] if trainings else []

        selected_training = st.selectbox("Select Training", training_names)

        if selected_training:
            st.subheader(f"Participants for {selected_training}")

            # Add Participant
            new_participant = st.text_input("New Participant Name")
            if st.button("Add Participant"):
                if new_participant:
                    participants_col.insert_one({"training_name": selected_training, "name": new_participant, "status": "active"})
                    st.success(f"Added {new_participant} to {selected_training}")
                    st.rerun()
                else:
                    st.error("Please enter a participant name!")

            # Fetch and display participants
            participants = list(participants_col.find({"training_name": selected_training}, {"_id": 0, "name": 1, "status": 1}))
            
            if participants:
                participant_names = [p["name"] for p in participants]
                selected_participant = st.selectbox("Select Participant to Remove", participant_names)
                removal_reason = st.text_area("Reason for Removal")

                if st.button("Remove Participant"):
                    if selected_participant:
                        participants_col.update_one(
                            {"training_name": selected_training, "name": selected_participant},
                            {"$set": {"status": "removed", "removal_reason": removal_reason}}
                        )
                        st.success(f"Removed {selected_participant} from {selected_training}")
                        st.rerun()
                    else:
                        st.error("Please select a participant to remove!")
            else:
                st.warning("No participants found for this training.")

    # 3. Track Attendance
    elif menu == "Track Attendance":
        st.header("Track Attendance")

        trainings = get_trainings()
        training_names = [t["name"] for t in trainings] if trainings else []

        selected_training = st.selectbox("Select Training", training_names)
        attendance_date = st.date_input("Select Date")

        if selected_training:
            participants = list(participants_col.find({"training_name": selected_training, "status": "active"}, {"_id": 0, "name": 1}))
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

    # 4. View Training Status
    elif menu == "View Training Status":
        st.header("Training Status & Attendance Summary")

        trainings = get_trainings()
        training_names = [t["name"] for t in trainings] if trainings else []

        selected_training = st.selectbox("Select Training", training_names)
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")

        if selected_training and start_date <= end_date:
            training = trainings_col.find_one({"name": selected_training})
            st.write(f"**Trainer Name:** {training.get('trainer_name', 'N/A')}")
            st.write(f"**Start Date:** {training.get('start_date', 'N/A')}")

            # Fetch attendance records
            attendance_records = list(attendance_col.find(
                {"training_name": selected_training, "date": {"$gte": str(start_date), "$lte": str(end_date)}},
                {"_id": 0, "date": 1, "present_participants": 1}
            ))

            # Fetch all participants (active & removed)
            participants = list(participants_col.find(
                {"training_name": selected_training},
                {"_id": 0, "name": 1, "status": 1, "date_removed": 1, "removal_reason": 1}
            ))

            # Separate active and removed participants
            active_participants = [p["name"] for p in participants if p.get("status") == "active"]
            removed_participants = {p["name"]: p for p in participants if p.get("status") == "removed"}

            # Create attendance dataframe
            df_data = {"Participant Name": []}
            date_list = pd.date_range(start=start_date, end=end_date).strftime('%Y-%m-%d').tolist()

            for name in active_participants + list(removed_participants.keys()):
                df_data["Participant Name"].append(name)
                
                # Get removal date (if participant was removed)
                removal_date = removed_participants.get(name, {}).get("date_removed")
                removal_date = removal_date.strftime('%Y-%m-%d') if removal_date else None

                for date in date_list:
                    if removal_date and date > removal_date:
                        df_data.setdefault(date, []).append("X")  # Mark as removed
                    else:
                        df_data.setdefault(date, []).append("P" if any(name in record["present_participants"] for record in attendance_records if record["date"] == date) else "A")

            attendance_df = pd.DataFrame(df_data)
            st.subheader("📋 Attendance Record")
            st.dataframe(attendance_df)

            # Display removed participants
            if removed_participants:
                st.subheader("🚫 Removed Participants")
                removed_df = pd.DataFrame(removed_participants.values())
                removed_df.rename(columns={"name": "Participant Name", "removal_reason": "Reason", "date_removed": "Removal Date"}, inplace=True)
                st.dataframe(removed_df)

            # Export to Excel
            export_to_excel(attendance_df)

# Uncomment to create admin user (Run once)
# create_admin()
