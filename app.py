import decimal
import os
from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from bson import ObjectId
import datetime
import random


app = Flask(__name__)
client = MongoClient(os.getenv("MONGO_URI"))
# client = MongoClient('mongodb://localhost:27017/')
db = client.hospitalManagementDb
admin_collection = db['admin']
patients_collection = db['patients']
doctors_collection = db['doctors']
appointments_collection = db['appointments']
prescriptions_collection = db['prescription']
cancelledappointments = db['cancelledappointments']
doctorSchedule =db['doctorSchedule']
billing_collection =db['billing']
app.secret_key = 'whekjrherlwjerlkwejrkwensmend'

@app.route('/home')
def main():
    specialities = ["Cardiology", "Neurology", "Orthopaedics", "Paediatrics", "General Surgery"]
    return render_template('home.html', specialities=specialities)

@app.route('/')
def index():
    if 'username' in session:
        return render_template('login.html')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))
@app.route('/adminlogout')
def adminlogout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['role']
        username = request.form['username']
        password = request.form['password']
        
        # Check credentials based on role
        if role == 'admin':
            user = admin_collection.find_one({'username': username, 'password': password})
            if user:
                session['username'] = username
                return jsonify({'success': True, 'message': 'Login successful', 'role': role})
        
        elif role == 'doctor':
            user = doctors_collection.find_one({'username': username, 'password': password})
            if user:
                session['username'] = username
                session['doctor_id'] = str(user['_id'])
                session['DoctorID'] = user['DoctorID']
                session['FirstName'] = user['FirstName']
                session['Phone'] = user['Phone']
                first_login = user.get('firstLogin', True)
                return jsonify({'success': True, 'message': 'Login successful', 'role': role, 'firstLogin': first_login})
        
        elif role == 'patient':
            user = patients_collection.find_one({'username': username, 'password': password})
            if user:
                session['username'] = username
                session['patient_id'] = str(user['_id'])
                session['firstname'] = user['firstname']
                session['contactno'] = user['contactno']
                return jsonify({'success': True, 'message': 'Login successful', 'role': role})
        
        return jsonify({'success': False, 'message': 'Invalid username or password'})
    else:
        return render_template('login.html')

@app.route('/change_password', methods=['GET'])
def change_password_page():
    if 'doctor_id' not in session:
        return redirect(url_for('login'))
    return render_template('change_password.html')

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'doctor_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 401

    data = request.json
    new_password = data.get('newPassword')

    doctor_id = session['doctor_id']
    doctors_collection.update_one({'_id': ObjectId(doctor_id)}, {'$set': {'password': new_password, 'firstLogin': False}})
    session.pop('username', None)
    session.pop('doctor_id', None)
    return jsonify({'success': True, 'message': 'Password changed successfully'})

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        username = request.form['username']
        password = request.form['password']
        contactno = request.form['contactno']
        address = request.form['address']
        city = request.form['city']
        state = request.form['state']
        zipcode = request.form['zipcode']
        dob = request.form['dob']
        gender = request.form['gender']
        
        user = patients_collection.find_one({'username': username})
        if user:
            return jsonify({'success': False, 'message': 'Username already exists'})
        else:
            patient_id = 'P' + str(random.randint(100000, 999999))
            new_user = {
                'patientId': patient_id,
                'firstname': firstname,
                'lastname': lastname,
                'username': username,
                'password': password,
                'contactno': contactno,
                'address': address,
                'city': city,
                'state': state,
                'zipcode': zipcode,
                'dob': dob,
                'gender': gender
            }
            patients_collection.insert_one(new_user)
            return jsonify({'success': True, 'message': 'User created successfully'})
    return render_template('signup.html')

@app.route('/myappointments')
def my_appointments():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    patientId = session.get('patient_id')
    appointments = list(appointments_collection.find({'patientId': patientId}).sort('appointmentDate', 1))

    for appointment in appointments:
        # Assuming the appointmentDate is stored as a string in 'YYYY-MM-DD' format
        appointment_date = datetime.datetime.strptime(appointment['appointmentDate'], '%Y-%m-%d')
        appointment['formattedDate'] = appointment_date.strftime('%m-%d-%Y')
    
    return render_template('appointment.html', appointments=appointments)

@app.route('/cancelled_appointments/<doctorId>', methods=['GET'])
def get_cancelled_appointments(doctorId):
    try:
        # Query to find cancelled appointments for the given doctorId
        appointments = list(cancelledappointments.find({'doctorId': doctorId}))
        
        # Preparing the response data
        response_data = []
        for appointment in appointments:
            response_data.append({
                'appointmentId': appointment.get('appointmentId'),
                'patientName': appointment.get('patientName'),
                'patientEmail': appointment.get('patientEmail'),
                'patientPhone': appointment.get('patientPhone'),
                'doctorName': appointment.get('doctorName'),
                'appointmentDate': appointment.get('appointmentDate'),
                'appointmentTime': appointment.get('appointmentTime'),
                'status': appointment.get('status')
            })
        
        return jsonify(response_data), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/about')
def about():
    return render_template('about.html')
@app.route('/request_reschedule', methods=['POST'])
def request_reschedule():
    appointmentId = request.form['appointmentId']
    newDate = request.form['newDate']
    newTime = request.form['newTime']

    appointments_collection.update_one(
        {'_id': ObjectId(appointmentId)},
        {'$set': {
            'rescheduleRequest': True,
            'rescheduleDetails': f"New Date: {newDate}, New Time: {newTime}",
            'cancelRequest': False
        }}
    )
    return redirect(url_for('my_appointments'))

@app.route('/request_cancel', methods=['POST'])
def request_cancel():
    appointmentId = request.form['appointmentId']
    reason = request.form['reason']

    appointments_collection.update_one(
        {'_id': ObjectId(appointmentId)},
        {'$set': {
            'cancelRequest': True,
            'cancelReason': reason,
            'rescheduleRequest': False
        }}
    )
    return redirect(url_for('my_appointments'))

@app.route('/admin_requests', methods=['GET'])
def admin_requests():
    requests = list(appointments_collection.find({'$or': [{'rescheduleRequest': True}, {'cancelRequest': True}]}))
    for req in requests:
        req['_id'] = str(req['_id'])
        req['type'] = 'reschedule' if req.get('rescheduleRequest') else 'cancel'
        req['details'] = req.get('rescheduleDetails') or req.get('cancelReason')
        req['doctorId'] = req.get('DoctorID')
        req['patientId'] = req.get('patientId')
    return jsonify(requests)

@app.route('/approve_request', methods=['POST'])
def approve_request():
    data = request.json
    requestId = data['requestId']
    req_type = data['type']

    appointment = appointments_collection.find_one({'_id': ObjectId(requestId)})
    if appointment:
        if req_type == 'reschedule':
            details = appointment['rescheduleDetails'].split(', ')
            newDate = details[0].split(': ')[1]
            newTime = details[1].split(': ')[1]
            appointments_collection.update_one(
                {'_id': ObjectId(requestId)},
                {'$set': {
                    'appointmentDate': newDate,
                    'appointmentTime': newTime,
                    'status': 'rescheduled',
                    'rescheduleRequest': False,
                    'rescheduleDetails': None
                }}
            )
        elif req_type == 'cancel':
            appointments_collection.update_one(
                {'_id': ObjectId(requestId)},
                {'$set': {
                    'status': 'cancelled'
                }}
            )
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/reject_request', methods=['POST'])
def reject_request():
    data = request.json
    requestId = data['requestId']
    req_type = data['type']

    if req_type == 'reschedule':
        appointments_collection.update_one(
            {'_id': ObjectId(requestId)},
            {'$set': {'rescheduleRequest': False, 'rescheduleDetails': None}}
        )
    elif req_type == 'cancel':
        appointments_collection.update_one(
            {'_id': ObjectId(requestId)},
            {'$set': {'cancelRequest': False, 'cancelReason': None}}
        )
    return jsonify({'success': True})

@app.route('/specialities', methods=['GET'])
def specialities():
    specialization = request.args.get('speciality')
    if specialization:
        doctors = list(doctors_collection.find({'Specialization': specialization}))
        return render_template('speciality.html', doctors=doctors, specialization=specialization)
    return render_template('speciality.html', doctors=[], specialization=None)

@app.route('/get_patient_info', methods=['GET'])
def get_patient_info():
    patient_info = {
        'firstname': session.get('firstname'),
        'username': session.get('username'),
        'contactno': session.get('contactno')
    }
    return jsonify(patient_info)

@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    data = request.json

    patientId = session.get('patient_id')
    patientName = session.get('firstname')
    patientEmail = session.get('username')
    patientPhone = session.get('contactno')
    appointmentDate = data['appointmentDate']
    appointmentTime = data['appointmentTime']
    medications = data['medications']
    medicalHistory = data['medicalHistory']

    doctorName = data['doctorName']
    doctorSpecialization = data['doctorSpecialization']
    doctorID = data['DoctorID']

    appointmentDate = datetime.datetime.strptime(appointmentDate, '%Y-%m-%d').strftime('%Y-%m-%d')

    appointment = {
        'DoctorID': doctorID,
        'appointmentId': str(ObjectId()),
        'patientId': patientId,
        'patientName': patientName,
        'patientEmail': patientEmail,
        'patientPhone': patientPhone,
        'doctorName': doctorName,
        'appointmentDate': appointmentDate,
        'appointmentTime': appointmentTime,
        'medications': medications,
        'medicalHistory': medicalHistory,
        'status': 'scheduled'
    }

    existing_appointment = appointments_collection.find_one({'DoctorID': doctorID, 'appointmentDate': appointmentDate, 'appointmentTime': appointmentTime})
    if existing_appointment:
        return jsonify({'success': False, 'message': 'Time slot already booked'}), 400

    appointments_collection.insert_one(appointment)
    return jsonify({'success': True})


@app.route('/doctor_details')
def doctor_dashboard():
    if 'doctor_id' not in session:
        return redirect(url_for('home'))
    return render_template('doctor_details.html')
@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')
@app.route('/doctors', methods=['GET'])
def get_doctors():
    doctors = list(doctors_collection.find({}, {'_id': 0}))  # Exclude the _id field from the result
    return jsonify(doctors)

@app.route('/add_doctor', methods=['POST'])
def add_doctor():
    data = request.json
    doctor = {
        'DoctorID': data['DoctorID'],
        'FirstName': data['FirstName'],
        'LastName': data['LastName'],
        'Specialization': data['Specialization'],
        'Phone': data['Phone'],
        'username': data['username'],
        'password': data['password'],
        'email': data['email'],
        'address': data['address'],
        'city': data['city'],
        'state': data['state'],
        'zipcode': data['zipcode'],
        'firstLogin': True
    }
    doctors_collection.insert_one(doctor)
    return jsonify({'success': True, 'message': 'Doctor added successfully'})
@app.route('/patients', methods=['GET'])
def get_patients():
    patients = list(patients_collection.find({}, {'_id': 0}))  # Exclude the _id field from the result
    return jsonify(patients)

@app.route('/add_patient', methods=['POST'])
def add_patient():
    data = request.json
    patient_id = 'P' + str(random.randint(100000, 999999))
    patient = {
        'patientId': patient_id,
        'firstname': data['firstname'],
        'lastname': data['lastname'],
        'username': data['username'],
        'password': data['password'],
        'contactno': data['contactno'],
        'address': data['address'],
        'dob': data['dob'],
        'gender': data['gender']
    }
    patients_collection.insert_one(patient)
    return jsonify({'success': True, 'message': 'Patient added successfully'})
@app.route('/admin_appointments', methods=['GET'])
def get_adminappointments():
    appointments = list(appointments_collection.find({}, {'_id': 0}))  # Exclude the _id field from the result
    return jsonify(appointments)

@app.route('/appointments/<doctor_id>', methods=['GET'])
def get_appointments(doctor_id):
    appointments = appointments_collection.find({"DoctorID": doctor_id})
    result = []
    for appointment in appointments:
        result.append({
            "patientName": appointment["patientName"],
            "patientEmail": appointment["patientEmail"],
            "patientId": appointment["patientId"],
             "appointmentId": appointment["appointmentId"],
            "patientPhone": appointment["patientPhone"],
            "appointmentDate": appointment["appointmentDate"],
            "appointmentTime": appointment["appointmentTime"],
              "medications": appointment["medications"],
 "medicalHistory": appointment["medicalHistory"],
            "status": appointment["status"]
          
        })
    return jsonify(result)

@app.route('/cancelled_appointments', methods=['GET'])
def get_cancelled_appointmentspatient():
    patient_id = session.get('patient_id')
    if not patient_id:
        return jsonify({'success': False, 'message': 'Not logged in as a patient'}), 401

    cancelled_appointments = cancelledappointments.find({"patientId": patient_id})
    result = []
    for appointment in cancelled_appointments:
        result.append({
            "appointmentId": appointment["appointmentId"],
            "patientName": appointment["patientName"],
            "patientEmail": appointment["patientEmail"],
            "patientPhone": appointment["patientPhone"],
            "doctorName": appointment["doctorName"],
            "appointmentDate": appointment["appointmentDate"],
            "appointmentTime": appointment["appointmentTime"],
            "status": appointment["status"]
        })
    return jsonify(result)
@app.route('/add_prescription', methods=['POST'])
def add_prescription():
    try:
        data = request.json
        print("Received data:", data)  # Debug print
        
        # Validate the data
        if not data or 'medications' not in data or 'doctorId' not in data or 'appointmentId' not in data or 'patientId' not in data:
            return jsonify({'success': False, 'message': 'Invalid data'}), 400
        
        medications = data['medications']
        if not isinstance(medications, list) or len(medications) == 0:
            return jsonify({'success': False, 'message': 'No medications provided'}), 400
        
        for medication in medications:
            if 'medicationName' not in medication or 'dosage' not in medication or 'frequency' not in medication or 'instructions' not in medication or 'date' not in medication:
                return jsonify({'success': False, 'message': 'Incomplete medication details'}), 400
        
        prescription = {
            '_id': ObjectId(),
            'PrescriptionID': 'PRESC' + str(ObjectId()),
            'PatientID': data['patientId'],
            'DoctorID': data['doctorId'],
            'AppointmentID': data['appointmentId'],
            'Medications': medications
        }
        
        prescriptions_collection.insert_one(prescription)
        return jsonify({'success': True})
    except Exception as e:
        print("Error in add_prescription:", e)  # Debug print
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/patientprescription')
def patientprescription():
    if 'patient_id' in session:
        return render_template('prescription.html', patient_id=session['patient_id'])
    return render_template('login.html')
@app.route('/myprescription')
def myprescription():
    if 'patient_id' in session:
        patient_id = session['patient_id']
        prescriptions = prescriptions_collection.find({"PatientID": patient_id})
        prescriptions_list = []
        for prescription in prescriptions:
            prescription['_id'] = str(prescription['_id'])  # Convert ObjectId to string
            prescriptions_list.append(prescription)
        return jsonify(prescriptions_list)
    return jsonify({'success': False, 'message': 'Unauthorized access'}), 401
@app.route('/userdetails')
def userdetails():
    if 'username' in session and 'patient_id' in session:
        user = patients_collection.find_one({'_id': ObjectId(session['patient_id'])})
        if user:
            user_details = {
                'patientId': user.get('patientId'),
                'firstname': user.get('firstname'),
                'lastname': user.get('lastname'),
                'username': user.get('username'),
                'contactno': user.get('contactno'),
                'address': user.get('address'),
                'dob': user.get('dob')
            }
            return jsonify(user_details)
    return jsonify({'error': 'User not found'}), 404

@app.route('/fetch_appointments', methods=['GET'])
def fetch_appointments():
    doctorID = request.args.get('doctorID')
    date = request.args.get('date')
    date = datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')

    appointments = appointments_collection.find({'DoctorID': doctorID, 'appointmentDate': date})
    bookedSlots = [appointment['appointmentTime'] for appointment in appointments]

    return jsonify({'bookedSlots': bookedSlots})
@app.route('/set_availability', methods=['POST'])
def set_availability():
    data = request.json
    doctor_id = data['doctorId']
    days = data['days']
    time_slots = data['timeSlots']

    availability = {
        'DoctorID': doctor_id,
        'Days': days,
        'TimeSlots': time_slots
    }

    # Upsert the availability for the doctor
    doctorSchedule.update_one(
        {'DoctorID': doctor_id},
        {'$set': availability},
        upsert=True
    )

    return jsonify({'success': True})
@app.route('/get_available_slots', methods=['GET'])
def get_available_slots():
    doctor_id = request.args.get('doctorID')
    date = request.args.get('date')
    date = datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')

    # Fetch doctor's availability for the week
    doctor_schedule = doctorSchedule.find_one({'DoctorID': doctor_id})
    available_days = doctor_schedule['Days']
    available_time_slots = doctor_schedule['TimeSlots']

    # Check if the selected date is in the available days
    day_of_week = datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%A')
    if day_of_week in available_days:
        # Fetch booked slots for the selected date
        appointments = appointments_collection.find({'DoctorID': doctor_id, 'appointmentDate': date})
        booked_slots = [appointment['appointmentTime'] for appointment in appointments if appointment.get('status') != 'cancelled']
        available_slots = [slot for slot in available_time_slots if slot not in booked_slots]
    else:
        available_slots = []

    return jsonify({'availableSlots': available_slots})

@app.route('/get_doctor_schedule', methods=['GET'])
def get_doctor_schedule():
    doctor_id = request.args.get('doctorID')
    doctor_schedule = doctorSchedule.find_one({'DoctorID': doctor_id}, {'_id': 0, 'Days': 1, 'TimeSlots': 1})

    if doctor_schedule:
        return jsonify(doctor_schedule)
    else:
        return jsonify({'error': 'No schedule found for the given DoctorID'}), 404
@app.route('/update_appointment_status', methods=['POST'])
def update_appointment_status():
    try:
        data = request.json
        appointmentId = data.get('appointmentId')
        status = data.get('status')

        if not appointmentId or not status:
            return jsonify({'success': False, 'message': 'Invalid data'}), 400

        result = appointments_collection.update_one(
            {'appointmentId': appointmentId},
            {'$set': {'status': status}}
        )

        if result.modified_count == 0:
            return jsonify({'success': False, 'message': 'Appointment not found or status unchanged'}), 400

        return jsonify({'success': True})
    except Exception as e:
        print("Error in update_appointment_status:", e)
        return jsonify({'success': False, 'message': 'Internal server error'}), 500
@app.route('/get_prescriptions/<doctor_id>/<patient_id>', methods=['GET'])
def get_prescriptions(doctor_id, patient_id):
    prescriptions = prescriptions_collection.find({'DoctorID': doctor_id, 'PatientID': patient_id})
    result = []
    for prescription in prescriptions:
        result.append({
            "PrescriptionID": prescription["PrescriptionID"],
            "Medications": prescription["Medications"]
        })
    return jsonify(result)
@app.route('/billing', methods=['POST'])
def billing():
    billing_data = request.json
    app.logger.debug("Received billing data: %s", billing_data)
    
    try:
        billing_collection.insert_one(billing_data)
        return jsonify({"status": "success", "data": billing_data}), 201
    except Exception as e:
        app.logger.error("Error inserting billing data: %s", e)
        return jsonify({"status": "fail", "message": str(e)}), 500
if __name__ == '__main__':
    app.run(debug=True)
