from .database import db
from datetime import datetime

# --- USER ---
# Handles login and role definition for Admin, Doctor, and Patient
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # Stores the role: 'Admin', 'Doctor', or 'Patient'
    role = db.Column(db.String(15), default='Patient', nullable=False) 
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    # Relationships linking to the new role-specific table names
    doctor = db.relationship('Doctor', backref='user', uselist=False)
    patient = db.relationship('Patient', backref='user', uselist=False)

# ---  DOCTOR  ---
class Doctor(db.Model):
    __tablename__ = 'doctor'  # The table name is also simplified
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key linking to the User table
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    
    # Doctor specific attributes
    full_name = db.Column(db.String(100), nullable=False)
    qualification = db.Column(db.String(100))
    experience_years = db.Column(db.Integer)
    
    # Link to their Specialization/Department
    dept_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    
    # Relationships
    appointments = db.relationship('Appointment', backref='doctor_details', lazy='dynamic')
    availability_slots = db.relationship('DoctorAvailability', backref='doctor_details', lazy='dynamic')

# --- PATIENT ---
class Patient(db.Model):
    __tablename__ = 'patient'  # The table name is also simplified
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key linking to the User table
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True)
    
    # Patient specific attributes
    full_name = db.Column(db.String(100), nullable=False)
    
    # Relationships
    appointments = db.relationship('Appointment', backref='patient_details', lazy='dynamic')

# --- DEPARTMENT ---
class Department(db.Model):
    __tablename__ = 'department'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    
    # Relationship to view all doctors in this department
    doctors_registered = db.relationship('Doctor', backref='department', lazy='dynamic')

    @classmethod
    def get_or_create(cls, department_name):
        """Fetches a department by name or creates it if it doesn't exist."""
        dept = cls.query.filter_by(name=department_name).first()
        if not dept:
            dept = cls(name=department_name)
            db.session.add(dept)
            db.session.commit()
        return dept
# --- APPOINTMENT ---
class Appointment(db.Model):
    __tablename__ = 'appointment'
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys linking to the Doctor and Patient (IDs now come from the 'doctor'/'patient' tables)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    
    # Appointment Attributes
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    
    # Status: Booked, Completed, Cancelled
    status = db.Column(db.String(20), default='Booked', nullable=False)
    
    # Relationship to Treatment (One Appointment can have One Treatment record)
    treatment = db.relationship('Treatment', backref='appointment', uselist=False)

# --- TREATMENT ---
class Treatment(db.Model):
    __tablename__ = 'treatment'
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key linking to the Appointment
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), unique=True)
    
    # Treatment/Diagnosis/Prescription Details
    diagnosis = db.Column(db.Text, nullable=False)
    prescription = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text)
    visit_type = db.Column(db.String(50))
    test_done = db.Column(db.String(100))
    
# --- DOCTOR AVAILABILITY MODEL ---
class DoctorAvailability(db.Model):
    __tablename__ = 'doctor_availability'
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key (linking to the 'doctor' table)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    
    # Availability details
    date = db.Column(db.Date, nullable=False)
    slot_type = db.Column(db.String(20), nullable=False) 
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_available = db.Column(db.Boolean, default=True)

    __table_args__ = (
        db.UniqueConstraint('doctor_id', 'date', 'slot_type', name='_doctor_slot_uc'),
    )