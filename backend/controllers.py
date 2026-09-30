from flask import render_template, redirect, request, url_for
from flask import current_app as app 

from .models import *
from .database import db 
from datetime import date, timedelta, time, datetime
import calendar
from sqlalchemy import or_, and_

# HELPER FUNCTIONS 
def get_next_seven_days():
    """Returns a list of datetime.date objects for the next 7 days (including today)."""
    today = date.today()
    return [today + timedelta(days=i) for i in range(7)]

def parse_time_slot(slot_str):
    """Parses time string like 'HH:MM - HH:MM' into (start_time, end_time) objects."""
    start_str, end_str = slot_str.split(' - ')
    start_time = time.fromisoformat(start_str.strip())
    end_time = time.fromisoformat(end_str.strip())
    return start_time, end_time

# =============================================================
# CORE ROUTES: LOGIN & REGISTER
# =============================================================
@app.route("/", methods=["GET"])   #view page
def home():
    return render_template("index.html")

@app.route("/login", methods = ["GET", "POST"])  #view and submit form
def login():
    if request.method == "POST":
        username = request.form["username"]
        pwd = request.form.get("pwd")
        this_user = User.query.filter_by(username = username).first() 
        if this_user:
            if this_user.password_hash == pwd:
                
                # Blacklist thing
                if not this_user.is_active:
                    return "Your account has been suspended by an administrator."
                
                # Seperation of users
                if this_user.role.lower() == "admin":
                    return redirect(url_for('admin_dashboard')) 
                elif this_user.role.lower() == "doctor":
                    return redirect(url_for('doctor_dashboard', user_id=this_user.id))
                else:
                    return redirect(url_for('patient_dashboard', user_id=this_user.id)) 
            else:
                return "password is wrong"  
        else:
            return "user does not exist"
        
    return render_template("login.html")

@app.route("/register", methods = ["GET", "POST"]) #view and submit form
def register():
    if request.method == "POST":
        username = request.form["username"]
        pwd = request.form["pwd"]
        email = request.form["email"]
        user_name = User.query.filter_by(username=username).first()   #check if user already exists
        user_email = User.query.filter_by(email=email).first()
        if user_name or user_email:
            return "user already exists"
        else:
            user = User(username=username, email=email, password_hash=pwd)
            db.session.add(user)
            db.session.commit()
            
            patient = Patient(user_id=user.id, full_name=username)  #add new registraation as patient
            db.session.add(patient)                                     
            db.session.commit()
        return redirect(url_for('login'))
    return render_template("register.html")

# =============================================================
#  ADMIN FUNCTIONALITY ROUTES 
# =============================================================
@app.route("/admin", methods=["GET"])     #to read data and fetch info
def admin_dashboard():
    all_doctors = Doctor.query.join(User).all()  #doc, patient and user table which are connected by user_id
    all_patients = Patient.query.join(User).all()
    
    admin_user = User.query.filter_by(role='Admin').first()
    
    total_doctors = Doctor.query.count() #stats on admin dashboard
    total_patients = Patient.query.count()
    total_appointments = Appointment.query.count() 
    
    upcoming_appointments = Appointment.query.filter(    #check date on which doc is available
        Appointment.status == 'Booked',
        Appointment.date >= date.today()  #checks upcoming appointments from todays date
    ).order_by(Appointment.date, Appointment.time).all()

    past_appointments = Appointment.query.filter(         #past appointments
        or_(
            Appointment.status == 'Completed',      #completed appointments
            and_(Appointment.status == 'Booked', Appointment.date < date.today())    #appointmnets that were missed(booked but missed)
        )
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).all()   #newest first

    return render_template(
        "admin.html", 
        all_doctors=all_doctors,   #render template to create new/edit template with given info using jinja
        all_patients=all_patients, 
        this_user=admin_user,
        
        upcoming_appointments=upcoming_appointments,
        past_appointments=past_appointments,
        total_doctors=total_doctors,
        total_patients=total_patients,
        total_appointments=total_appointments
    )

@app.route("/admin-search", methods=["GET"]) #to read data and fetch info
def admin_search():
    admin_user = User.query.filter_by(role='Admin').first()
    if not admin_user:
        return "Unauthorized", 403

    query = request.args.get("query", "").strip()
    
    doctor_results = []
    patient_results = []  #empty list to search and store the results
    
    if query:
        search_pattern = f"%{query}%"  #%"any charcter"%
        doctor_results = Doctor.query.join(Department).join(User).filter(   #search query for doctor connecting doctor,dept and user table
            (Doctor.full_name.ilike(search_pattern)) |  #"|" or 
            (Department.name.ilike(search_pattern))    #search either by department or doctors name
        ).all()
        patient_results = Patient.query.join(User).filter(     #search query for patient connectng user table 
            Patient.full_name.ilike(search_pattern)            #serch by patient name
        ).all()
        
    all_doctors = doctor_results if query else Doctor.query.join(User).all()  #if query is true set 'all_doctors' to 'doctor_results(filtered list)
                                                                             #if false set all_doctors to the full list of all doctors

    all_patients = patient_results if query else Patient.query.join(User).all() #if query is true set 'all_patients' to 'patient_results'
    
    total_doctors = len(all_doctors) 
    total_patients = len(all_patients)  #total count
    
    upcoming_appointments = Appointment.query.filter(   #check date on which doc is available
        Appointment.status == 'Booked',
        Appointment.date >= date.today()             #checks upcoming appointments from todays date
    ).order_by(Appointment.date, Appointment.time).all()
    
    past_appointments = Appointment.query.filter(      #past appointments
        or_(
            Appointment.status == 'Completed',          #completed appointments
            and_(Appointment.status == 'Booked', Appointment.date < date.today())        #appointmnets that were missed(booked but missed)
        )
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).all()  #newest first

    return render_template(
        "admin.html", 
        all_doctors=all_doctors, 
        all_patients=all_patients,
        this_user=admin_user,       #render template to create new/edit template with given info using jinja after 
        search_query=query,        # searching and reloading page
        
        upcoming_appointments=upcoming_appointments, 
        past_appointments=past_appointments,
        total_doctors=total_doctors,
        total_patients=total_patients,
        total_appointments=Appointment.query.count() 
    )

@app.route("/add-doc", methods=["GET", "POST"])   #view/fetch data and submit/overwrite the previous data when the form is submitted
def add_doctor():                                 #create new data entry in user and doctor section connecting it with user id
    admin_user = User.query.filter_by(role='Admin').first()   #validation check for admin
    if not admin_user:
        return "Unauthorized", 403

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        full_name = request.form.get("full_name")         #enter all the asked info
        qualification = request.form.get("qualification")
        experience = request.form.get("experience")
        department_name = request.form.get("department_name")

        if not all([username, email, password, full_name, department_name]):
            return "Missing required fields.", 400                #if something is empty/missing give error

        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            return "Username or Email already exists."            #if username and email is same then give error

        try:
            dept = Department.get_or_create(department_name)  #find Department with same name ELSE creates a new one
            
            new_user = User(username=username, email=email, password_hash=password, role='Doctor')
            db.session.add(new_user)         #Create new user with role doctor
            db.session.flush()               #tempory change (open for any changes later on) 

            new_doctor = Doctor(
                user_id=new_user.id,
                full_name=full_name,
                qualification=qualification,
                experience_years=int(experience) if experience and experience.isdigit() else 0,
                dept_id=dept.id
            )
            db.session.add(new_doctor)
            db.session.commit()     #save new user in the databse as doctor with all info
            
            return redirect(url_for('admin_dashboard'))  #back to admin dash

        except Exception as e:
            db.session.rollback()
            return f"An error occurred: {e}", 500     #if any part of try block fail give error

    return render_template("add_doc.html", admin_user=admin_user)   #create new/edit template with adding doctor using jinja after reloading
 

@app.route("/admin/edit-patient/<int:patient_id>", methods=["GET", "POST"]) #view/fetch data and submit/overwrite the previous data when the form is submitted 
def admin_edit_patient(patient_id):                            #admin to change/edit patient details
    admin_user = User.query.filter_by(role='Admin').first()    #admin check validation
    if not admin_user:
        return "Unauthorized", 403

    patient = Patient.query.get_or_404(patient_id)       #check if patient is there or not
    user = patient.user 
    
    if request.method == "POST":   #Checks if the user is saving the form(only when clicked on save button)
        patient.full_name = request.form.get("full_name")  #the new name that admin typed in full name
        
        try:
            db.session.commit()   #save the new full name given by admin
            return redirect(url_for('admin_dashboard'))  #redirect admin back to dashboard
        except Exception as e:
            db.session.rollback()
            return f"An error occurred: {e}", 500

    return render_template(
        "admin_edit_patient.html",    #create new/edit template with new name of patient using jinja after reloading
        patient=patient, 
        user=user
    )

@app.route("/edit-doc/<int:doc_id>", methods=["GET", "POST"])  #view/fetch data and make chnages to info in database table
def edit_doctor(doc_id):
    admin_user = User.query.filter_by(role='Admin').first() #admin validation check
    if not admin_user:
        return "Unauthorized", 403

    doctor = Doctor.query.get_or_404(doc_id)   #check if doctor exist or not
    user = doctor.user 
    current_dept_name = doctor.department.name if doctor.department else ''   #empty sting (' ') to prevent error if dept does not exist

    if request.method == "POST":   #run only if user submitted the form
        full_name = request.form.get("full_name")
        qualification = request.form.get("qualification")       
        experience = request.form.get("experience")
        department_name = request.form.get("department_name")  #updates info that admin edited
        
        doctor.full_name = full_name
        doctor.qualification = qualification
        
        if experience and experience.isdigit(): #enters only numbers
            doctor.experience_years = int(experience) 

        if department_name:
            dept = Department.get_or_create(department_name)  #if dept is present then return the same if not create it in table
            doctor.dept_id = dept.id

        try:
            db.session.commit()   #save the changes in database
            return redirect(url_for('admin_dashboard'))  #back to admin dash
        except Exception as e:
            db.session.rollback()
            return f"An error occurred: {e}", 500

    return render_template(
        "edit_doc.html", 
        doctor=doctor,       #update new doctor info using jinja after reloading page
        user=user,
        current_dept_name=current_dept_name
    )
@app.route("/delete-doc/<int:doc_id>", methods=["POST"])  #makes irreversible changes in dataset
def delete_doctor(doc_id):   
    admin_user = User.query.filter_by(role='Admin').first()  #admin validation
    if not admin_user:
        return "Unauthorized", 403
    
    doctor = Doctor.query.get(doc_id)  #searches for doctor by doc_id is database
    if not doctor:
        return "Doctor not found.", 404
    
    user_to_delete = doctor.user    #finding User object that is linked to this doctor
    
    try:     
        # 1. Find all appointments linked to this doctor
        appts_to_delete = Appointment.query.filter_by(doctor_id=doc_id).all()
        for appt in appts_to_delete:
            # 2. Delete linked treatments first (one-by-one)
            if appt.treatment:
                db.session.delete(appt.treatment)
        
        # 3. Bulk delete all appointments for this doctor
        Appointment.query.filter_by(doctor_id=doc_id).delete()
        
        # 4. Bulk delete all availability slots for this doctor
        DoctorAvailability.query.filter_by(doctor_id=doc_id).delete()

        # 5. Now it's safe to delete the doctor
        db.session.delete(doctor)
        
        # 6. Delete the user login
        if user_to_delete:
            db.session.delete(user_to_delete)   #deletes doctor from user object
            
        db.session.commit()  #deletes permanently from database
        return redirect(url_for('admin_dashboard'))  #if commit succesful back to admin dashboard
        
    except Exception as e:
        db.session.rollback()     #if any error in session.delete doctor will still be present in database
        return f"An error occurred during deletion: {e}", 500


@app.route("/delete-patient/<int:patient_id>", methods=["POST"])   #makes irreversible changes in dataset
def delete_patient(patient_id):
    admin_user = User.query.filter_by(role='Admin').first()  #admin validation
    if not admin_user:
        return "Unauthorized", 403
    
    patient = Patient.query.get(patient_id)   #searches for patient by patient_id in dataset
    if not patient:
        return "Patient not found.", 404
    
    user_to_delete = patient.user       #finding User object that is linked to this patient
    
    try:
        # 1. Find all appointments linked to this patient
        appts_to_delete = Appointment.query.filter_by(patient_id=patient_id).all()
        for appt in appts_to_delete:
            # 2. Delete linked treatments first (one-by-one)
            if appt.treatment:
                db.session.delete(appt.treatment)
        
        # 3. Bulk delete all appointments for this patient
        Appointment.query.filter_by(patient_id=patient_id).delete()

        # 4. Now it's safe to delete the patient
        db.session.delete(patient)
        
        # 5. Delete the user login
        if user_to_delete:
            db.session.delete(user_to_delete)
            
        db.session.commit()   #confirm and delete
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        db.session.rollback()   #if any error in session.delete patient will still be present in database
        return f"An error occurred during deletion: {e}", 500


# BLACKLIST ROUTES
@app.route("/admin/toggle-blacklist-doctor/<int:doc_id>", methods=["POST"])  #makes changes in dataset
def toggle_blacklist_doctor(doc_id):
    admin_user = User.query.filter_by(role='Admin').first()  #admin validation
    if not admin_user:
        return "Unauthorized", 403
    
    doctor = Doctor.query.get(doc_id) #fetch doc it from databse matching doc_id
    if doctor and doctor.user:
        # Flip the boolean
        doctor.user.is_active = not doctor.user.is_active  #user is currently active(True),then make inactive(False). If user currently inactive(False), makes them active(True)
        db.session.commit() #save changes
        
    return redirect(url_for('admin_dashboard')) #after saving back to admin dashboard

@app.route("/admin/toggle-blacklist-patient/<int:patient_id>", methods=["POST"]) #changes in database(is_active)
def toggle_blacklist_patient(patient_id):
    admin_user = User.query.filter_by(role='Admin').first() #admin validation
    if not admin_user:
        return "Unauthorized", 403
    
    patient = Patient.query.get(patient_id) #fetch patient_id from database
    if patient and patient.user:
        # Flip the boolean
        patient.user.is_active = not patient.user.is_active #if active(True) then make inactive(False), if inactive(False) then make them active(False)
        db.session.commit()  #save changes
        
    return redirect(url_for('admin_dashboard')) #after saving back to admin dash


# =========================================================
#  DOCTOR FUNCTIONALITY ROUTES 
# =============================================================
@app.route("/doctor-dashboard/<int:user_id>", methods=["GET"])  #to read data and fetch info
def doctor_dashboard(user_id):
    this_user = User.query.get_or_404(user_id) #find user in the database with the matching user_id
    doctor = this_user.doctor  #doc profile linked to user
    
    if not doctor:
        return "Doctor profile not found.", 404
    
    upcoming_appointments = Appointment.query.filter(  #find all relevant appointments
        Appointment.doctor_id == doctor.id,
        Appointment.status == 'Booked', #show only booked appointments
        Appointment.date >= date.today()  #appointment lined up from toady onwards
    ).order_by(Appointment.date, Appointment.time).all()  #sort(earliet first)

    assigned_patients = Patient.query.join(Appointment).filter( #new query for patients table linking to appointment table
        Appointment.doctor_id == doctor.id  #find patient witth appointment with this doc
    ).distinct().all() #e.g(if a patient has 10 appointments with this doctor still only show them once)
    
    return render_template(
        "doctor_dasboard.html", 
        this_user=this_user, 
        doctor=doctor,                    #update doctor dash with required info using jinja after reloading page
        appointments=upcoming_appointments,
        patients=assigned_patients
    )

@app.route("/doctor/availability/<int:user_id>", methods=["GET", "POST"]) #view and save data(doctors schedule)
def doctor_availability(user_id):
    this_user = User.query.get_or_404(user_id)
    doctor = this_user.doctor  #check if this_user is doctor
    
    if not doctor:
        return "Doctor profile not found.", 404

    next_seven_days = get_next_seven_days() #HELPER FUNCTION 
    
    if request.method == "POST":  #if user clicked 'save' then go ahead
        try:
            DoctorAvailability.query.filter(                   #clear the slate(finds all existing availability 
                DoctorAvailability.doctor_id == doctor.id,     #slots for this doctor within the next 7 days 
                DoctorAvailability.date.in_(next_seven_days)   #and deletes them from the database)
            ).delete(synchronize_session=False)

            for day in next_seven_days:
                date_key = day.strftime("%Y-%m-%d") #Converts date object to string
                
                if request.form.get(f"slot_{date_key}_morning"): #e.g(request.form.get("slot_2025-11-15_morning"), if checkbox is ticked, this is true.
                    start_t, end_t = parse_time_slot("08:00 - 12:00") #call helper to get time
                    new_slot = DoctorAvailability(  
                        doctor_id=doctor.id, date=day, slot_type='Morning', 
                        start_time=start_t, end_time=end_t, is_available=True  #Create new DoctorAvailability in memory
                    )  
                    db.session.add(new_slot) #add new slot

                if request.form.get(f"slot_{date_key}_evening"):  #e.g(request.form.get("slot_2025-11-15_morning"), if checkbox is ticked, this is true.
                    start_t, end_t = parse_time_slot("16:00 - 21:00")  #call helper to get time
                    new_slot = DoctorAvailability(
                        doctor_id=doctor.id, date=day, slot_type='Evening', 
                        start_time=start_t, end_time=end_t, is_available=True   #Create new DoctorAvailability in memory
                    )
                    db.session.add(new_slot) #add new slot
            
            db.session.commit()  #save 
            return redirect(url_for('doctor_dashboard', user_id=user_id)) #back to doctor dashboard
        
        except Exception as e:
            db.session.rollback() #if faced error in any step undo the change
            return f"Error saving availability: {e}", 500
    
    current_slots = DoctorAvailability.query.filter( #find all the doctor's currently saved slots for the next 7 days(using GET)
        DoctorAvailability.doctor_id == doctor.id,
        DoctorAvailability.date.in_(next_seven_days)
    ).all()

    schedule = {}  #create empty dictionary
    for day in next_seven_days:
        date_key = day.strftime("%Y-%m-%d") 
        schedule[date_key] = {'morning': False, 'evening': False} #Pre-fill schedule dictionary with False for all slots

    for slot in current_slots:
        date_key = slot.date.strftime("%Y-%m-%d") #e.g(If a "Morning" slot for 17th nov exist, set the value to True)
        if slot.slot_type == 'Morning':
            schedule[date_key]['morning'] = True
        elif slot.slot_type == 'Evening':
            schedule[date_key]['evening'] = True
            
    return render_template(
        "doc_dates.html", 
        this_user=this_user, 
        next_seven_days=next_seven_days,  #update doctor dates with required info using jinja after reloading page
        schedule=schedule,
        calendar=calendar
    )

@app.route("/appointment/status/<int:app_id>/<string:status>", methods=["POST"]) #makes changes in the data
def update_appointment_status(app_id, status):  
    if status not in ['Completed', 'Cancelled']: #validation check for status(only one of the allowed values 'cancelled' or 'completed')
        return "Invalid status update.", 400
        
    appointment = Appointment.query.get_or_404(app_id)  #find Appointment in the database using its ID
    appointment.status = status   #core logic(updates the status as 'completed' or 'cancelled')
    
    try:
        db.session.commit() #save changes
        return redirect(url_for('doctor_dashboard', user_id=appointment.doctor_details.user_id))  #is saved then back to doctor dash
    except:
        db.session.rollback()  #if any step shows error undo all the changes
        return "Failed to update appointment status.", 500

@app.route("/update-treatment/<int:app_id>", methods=["GET", "POST"]) #view the page and save the form info
def update_treatment_history(app_id):   #app_id from url
    appointment = Appointment.query.get_or_404(app_id)  #find appontment in databse
    
    treatment = appointment.treatment  #Treatment record that is already linked to this appointment

    if request.method == "POST": #run block when doctor clicks 'save'
        
        if not treatment:  #checks if this is first time
            treatment = Treatment(appointment_id=app_id)  #if first time craete new and empty treatment in memory
            db.session.add(treatment)  #insert treatment to database
        
        diagnosis = request.form.get("diagnosis") 
        prescription = request.form.get("prescription")  #gets doctos typed text(entered in form)
        
        if not diagnosis or not prescription:   #validation check(make sure diagnosis or prescription are not empty)
            return "Error: Diagnosis and Prescription are required fields.", 400

        treatment.diagnosis = diagnosis
        treatment.prescription = prescription
        treatment.visit_type = request.form.get("visitType")
        treatment.test_done = request.form.get("testDone")
        treatment.notes = request.form.get("medicines")   #updates treatment table with data from the form
                                                         #(either the new one or the one we found)
        try:
            appointment.status = 'Completed'  #update appointment to complete
            
            db.session.commit() #save cahnges
            return redirect(url_for('doctor_dashboard', user_id=appointment.doctor_details.user_id)) #if info saved back to doc dash
        except Exception as e:
            db.session.rollback()  #any error occours undo all the chnages
            return f"Error updating treatment: {e}", 500

    if not treatment:   #if no tratment record found
        treatment = Treatment(appointment_id=app_id) #create temporary and empty row in tratment table so render temp does not crash

    return render_template(
        "update_patient.html", 
        appointment=appointment, 
        patient=appointment.patient_details,
        doctor=appointment.doctor_details,
        treatment=treatment    #update page with new info using jinja
    )


# =============================================================
# === PATIENT FUNCTIONALITY ROUTES ===
# =============================================================
@app.route("/patient-dashboard/<int:user_id>")
def patient_dashboard(user_id):   
    this_user = User.query.get_or_404(user_id) #find user in databse with same user_id
    patient = this_user.patient  #get patient profile linked to that user_id
    
    all_departments = Department.query.all() #fetch all departments

    upcoming_appointments = Appointment.query.filter( 
        Appointment.patient_id == patient.id,  #find appointment_id that matches patient_id
        Appointment.status == 'Booked',         #filter only booked ones
        Appointment.date >= date.today()         #date is today onwards
    ).order_by(Appointment.date, Appointment.time).all()  #order all appointments by date and time

    return render_template(
        "patient_dash.html", 
        this_user=this_user, 
        all_departments=all_departments,     #show updated info using jinja
        upcoming_appointments=upcoming_appointments,
    )

@app.route("/edit-patient-profile/<int:user_id>", methods=["GET", "POST"])  #view and save info in database
def edit_patient_profile(user_id): #fetch user_id from url
    user = User.query.get_or_404(user_id)  #find in users if not show error
    patient = user.patient         #patient profile linked to this user
    
    if request.method == "POST":  #run only if patient has submitted the form
        full_name = request.form.get("full_name")  
        patient.full_name = full_name #overwrite/edit full name
        
        try:
            db.session.commit() #save changes in database
            return redirect(url_for('patient_dashboard', user_id=user_id)) #if saved back to patient dash
        except Exception as e:
            db.session.rollback()  #undo all changes if any error occurs
            return f"An error occurred during update: {e}", 500

    return render_template(
        "patient_profile.html", 
        user=user,           #update databse with new info and display same upadated info using jinja
        patient=patient
    )

@app.route("/patient-history/<int:user_id>", methods=["GET"])   #to read data and fetch info
def patient_history(user_id):  #fetch user_id from url
    user = User.query.get_or_404(user_id)  #search user_id in users table
    patient = user.patient      #match user to patient using user_id
    
    history_records = Appointment.query.outerjoin(Treatment).filter( #links appointment to treatment table.
        Appointment.patient_id == patient.id,              # outerjoin means it "get all appointments, and if treatment record exists include it"
        Appointment.status == 'Completed'                  #If not, still include the appointment.
    ).order_by(Appointment.date.desc()).all()     #finds appointments that are completed and belongs to that patient
    
    return render_template(
        "patient_history.html", 
        this_user=user,         #update patient history with saved info in database using jinja
        patient=patient,
        history=history_records
    )

@app.route("/search-doctors/<int:user_id>/<string:dept_name>", methods=["GET"])  #to read data and fetch info
def search_doctors(user_id, dept_name):  #fetch dept_name and user_id from url
    user = User.query.get_or_404(user_id)   #search user id in users table
    patient = user.patient                  #match user to patient using user_id
    
    department = Department.query.filter_by(name=dept_name).first_or_404()   #find dept by its name
    
    seven_days = get_next_seven_days() #call helper function
    available_doctor_ids = db.session.query(DoctorAvailability.doctor_id).filter(  #Finds availability record that falls in next 7 days
        DoctorAvailability.date.in_(seven_days)
    ).distinct().subquery() #doctor_id apperas only once in list with temporary query
    
    doctors = Doctor.query.filter(   #main query
        Doctor.dept_id == department.id,
        Doctor.id.in_(available_doctor_ids)   #doctors of specific dept with doc_id in avaivlable doc_id
    ).all()

    return render_template(
        "department_details.html", 
        this_user=user,       
        department=department,      
        doctors_in_dept=doctors,                #update deapt_details page with saved info using jinja
    )

@app.route("/book-appointment/<int:user_id>/<int:doctor_id>", methods=["GET", "POST"])  #view data and make changes
def book_appointment(user_id, doctor_id): #fetch user_id and doc_id from url
    patient = Patient.query.filter_by(user_id=user_id).first_or_404()   #Patient profile for the user who is booking
    doctor = Doctor.query.get_or_404(doctor_id)               #doc profile that is being booked

    if request.method == "POST":    #run only when booked button is clicked
        slot_data = request.form.get("selected_slot").split('|')  #select value from form
        if len(slot_data) != 2:   #validation check for format
            return "Invalid slot selection.", 400
        
        appt_date_str, slot_type = slot_data   #Unpack list in two separate variables
        appt_date = datetime.strptime(appt_date_str, "%Y-%m-%d").date() #convert string to python date object

        available_slot = DoctorAvailability.query.filter(  # check DoctorAvailability table(If this doctor supposed is available on this date and slot)
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.date == appt_date,
            DoctorAvailability.slot_type == slot_type   #check all filters
        ).first()

        if not available_slot:
            return "Error: Slot is no longer available.", 400

        existing_appt = Appointment.query.filter(
            Appointment.doctor_id == doctor.id,
            Appointment.date == appt_date,                #check if someone else has booked this slot and date
            Appointment.time == available_slot.start_time, 
            Appointment.status == 'Booked'
        ).first()

        if existing_appt:
             return "Error: This time slot was just booked by another patient. Please choose another.", 409

        try:         #save new operation
            new_appt = Appointment(     #Create new Appointment object in memory with all info
                patient_id=patient.id,
                doctor_id=doctor_id,
                date=appt_date,
                time=available_slot.start_time, 
                status='Booked'
            )
            db.session.add(new_appt) #insert new appointment 
            db.session.commit()  #save changes
            return redirect(url_for('patient_dashboard', user_id=user_id))  #back to patient dash
        except Exception as e:
            db.session.rollback()   #if any error undo changes
            return f"Error during appointment booking: {e}", 500

    #GET REQUEST LOGIC
    seven_days = get_next_seven_days()  #next 7 days
    
    potential_slots = DoctorAvailability.query.filter(    #fetch doc's entire schedule for next 7 days from doctorAvailability table
        DoctorAvailability.doctor_id == doctor_id,
        DoctorAvailability.date.in_(seven_days)
    ).order_by(DoctorAvailability.date, DoctorAvailability.start_time).all()

    booked_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,       #fetch Booked appointments for doctor for next 7 days
        Appointment.date.in_(seven_days),
        Appointment.status == 'Booked'
    ).all()

    booked_slots_set = set() #create empty set for slots
    for appt in booked_appointments:
        booked_slots_set.add((appt.date, appt.time))   #Fill the set with (date, time) tuples for every Booked appointment

    truly_available_slots = []  #create empty list for final results
    for slot in potential_slots:  #fetch doc's available slots
        if (slot.date, slot.start_time) not in booked_slots_set:
            truly_available_slots.append(slot)    #if the slot is free and not booked by other patients, add it to final list

    return render_template(
        "book_appointment.html", 
        this_user=patient.user,    #update new info using jinja when page is reloaded
        patient=patient,
        doctor=doctor,
        available_slots=truly_available_slots  #Pass only filtered list of available slots to the template
    )

@app.route("/cancel-appointment/<int:app_id>", methods=["POST"]) #make changes to data set in appointment table
def cancel_appointment(app_id): #fetch app_id from url
    appointment = Appointment.query.get_or_404(app_id)  #find appointment by app_id
    user_id = appointment.patient_details.user_id       #find user_id of patient with this appointment
    appointment.status = 'Cancelled'        #change the value of the status column to Cancelled for the app_id provided
    
    try:
        db.session.commit() #save changes in datset
        return redirect(url_for('patient_dashboard', user_id=user_id)) #back to patient_dashboard after saving
    except:
        db.session.rollback()  #if any error undo all changes
        return "Failed to cancel appointment.", 500
    
@app.route("/doctor-profile/<int:user_id>/<int:doctor_id>", methods=["GET"])  #to read data and fetch info
def doctor_profile(user_id, doctor_id):  #fetch user_id and doc_id from url
    this_user = User.query.get_or_404(user_id) #find User who is currently logged in
    doctor = Doctor.query.get_or_404(doctor_id)   #find octor profile that the user want to see
    
    return render_template(
        "doctor_profile.html", 
        this_user=this_user,    #upadte new info using jinja when doc_profile is visisted
        doctor=doctor
    )