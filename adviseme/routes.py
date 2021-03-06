import os
import math
import secrets
from datetime import date
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from adviseme import app, bcrypt, db
from adviseme.forms import *
from adviseme.models import *
from flask_login import login_user, current_user, logout_user, login_required
from sqlalchemy import func
from sqlalchemy.sql.operators import Operators
import itertools
import csv 
import math
import pandas as pd

@app.route('/')
def landing():
    return render_template('index.html', title="Welcome!")


@app.route('/home')
def home():
    return render_template('home.html', title='Home')


@app.route('/about/')
def about():
    return render_template("about.html", title="About")


# Can register both students and faulties (only ccny or citymail email can sign up.)
@app.route('/register/', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        if ('@citymail.cuny.edu' in form.email.data) or ('@ccny.cuny.edu' in form.email.data):
            if '@citymail.cuny.edu' in form.email.data:
                role = 'Student'
            else:
                role = 'Faculty'
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(email=form.email.data, password=hashed_password, role=role)
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created! You are now able to log in', 'success')
            return redirect(url_for('login'))
        else:
            flash(f'Enter your citymail Please!', 'danger')
    return render_template('register.html', title='Register', form=form)


# Can login both students and faulties, if '@ccny.cuny.edu' would be faculty account, and '@citymail.cuny.edu' should be student account.
@app.route('/login/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('studentinfo_fill'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            if current_user.role == 'Student' and current_user.EMPLID == None:
                next_page = request.args.get('next')
                flash('Login Successful. Welcome to AdviseMe', 'success')
                return redirect(next_page) if next_page else redirect(url_for('studentinfo_fill'))

            elif current_user.role == 'Faculty' and current_user.EMPLID == None:
                next_page = request.args.get('next')
                flash('Login Successful. Welcome to AdviseMe', 'success')
                return redirect(next_page) if next_page else redirect(url_for('facultyinfo_fill'))
            elif current_user.role == 'Student':
                next_page = request.args.get('next')
                flash('Login Successful. Welcome to AdviseMe', 'success')
                return redirect(next_page) if next_page else redirect(url_for('student_profile'))
            elif current_user.role == 'Faculty':
                next_page = request.args.get('next')
                flash('Login Successful. Welcome to AdviseMe', 'success')
                return redirect(next_page) if next_page else redirect(url_for('faculty'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')

    return render_template('login.html', title='Login', form=form)



def save_picture(form_picture):
    random_hex = secrets.token_hex(8)                                               # We don't want to make this too large trust me!
    _, f_ext = os.path.splitext(form_picture.filename)                              # the os module allows us to extract a file's extension
    picture_fn = random_hex + f_ext                                                 # filename = hex value + file extension (.jpg, .png)
    picture_path = os.path.join(app.root_path, 'static/Profile_Pics', picture_fn)   # File/path/to/save/picture! with specified file name!

    # This entire section of the code below just compresses the image to save space on our devices/the hosting sever (once deployed)!
    #-----------------------------------------------
    output_size = (125, 125)
    image_compressed = Image.open(form_picture)
    image_compressed.thumbnail(output_size)
    #-----------------------------------------------

    image_compressed.save(picture_path)                                             # Save the compressed picture to the: 'static/Profile_Pics/'
    # Add the cloudinary API here for deployment

    return picture_fn

def save_transcript(form_transcript, semester, year, student_id):
    pdf = form_transcript
    random_hex = secrets.token_hex(8)                                                   # We don't want to make this too large trust me!
    _, f_ext = os.path.splitext(form_transcript.filename)                               # the os module allows us to extract a file's extension

    transcript_fn = str(student_id) + '_' + str(semester) + '_' + str(year) +  '_' + random_hex + f_ext
    # Example -- filename = "student_id_Fall_2021_sdsdf799w7e98797ed.pdf"

    transcript_path = os.path.join(app.root_path, f'static/Transcripts/', transcript_fn)  # File/path/to/save/transcript!
    pdf.save(transcript_path)                                             # Save the compressed picture to the: 'static/Profile_Pics/'

    return transcript_fn


# Student fill out the basic info on the first time once they signed in
@app.route('/studentinfo_fill', methods=['GET', 'POST'])
@login_required
def studentinfo_fill():
    if current_user.role == "Faculty":
        abort(403)

    form = StudentInfoForm()
    profile_image = url_for('static', filename='Profile_Pics/'+ current_user.profile_image)

    if form.validate_on_submit():
        if form.picture.data:                                   # If there exists valid form picture data (i.e .png, .jpg file)
            picture_file = save_picture(form.picture.data)      # Save the image!
            current_user.profile_image = picture_file           # Update the current user profile photo in the database!
            print("Execution Complete!")

        student = Student(EMPLID=form.EMPLID.data,
                          firstname=form.firstname.data,
                          lastname=form.lastname.data,
                          graduating=form.graduating.data)
        current_user.EMPLID=form.EMPLID.data
        current_user.bio=form.bio.data
        db.session.add(student)
        db.session.commit()
        flash('Info Updated', 'success')
        return redirect(url_for('courseinfo_fill'))

    return render_template('studentinfo_fill.html', title='Student Form', profile_image=profile_image, form=form)


@app.route('/student/course/info', methods=['GET', 'POST'])
@login_required
def student_course_info():
    if current_user.role == "Student":
        abort(403)

    form = Cirriculum_Form()  
    courses = Course.query.all()
    course_count = db.session.query(Course.id).count()
    print(course_count)

    # NOTE: This Not the most optimal but this prevents the overflow issue from arising! 
    for i in range(course_count):   
        form.courses.append_entry()

    if request.method == 'POST':
        for course in courses:
            course.serial = form.courses[int(course.id - 1)].serial.data
            course.name = form.courses[int(course.id - 1)].course_name.data
            course.dept = form.courses[int(course.id - 1)].dept.data
            course.description = form.courses[int(course.id - 1)].course_description.data
            course.designation = form.courses[int(course.id - 1)].designation.data
            course.credits = form.courses[int(course.id - 1)].credits.data
        
        db.session.commit()         # Update courses! 
        
        flash("Changes Saved!", "success")
        return redirect(url_for('student_course_info'))
    elif request.method == 'GET':
        for course in courses:
            form.courses[int(course.id - 1)].serial.data = course.serial
            form.courses[int(course.id - 1)].course_name.data = course.name
            form.courses[int(course.id - 1)].dept.data = course.dept
            form.courses[int(course.id - 1)].course_description.data = course.description
            form.courses[int(course.id - 1)].designation.data = course.designation
            form.courses[int(course.id - 1)].credits.data = course.credits
        
    return render_template('student_course_info.html', courses=courses, form=form)


@app.route('/faculty/cirriculum/edit', methods=['GET', 'POST'])
@login_required
def add_remove_course():
    if current_user.role == "Student":
        abort(403)

    form = CourseForm()  
    courses = Course.query.all()

    if request.method == 'POST':
        course = Course(    serial=form.serial.data,
                            name=form.course_name.data,
                            dept=form.dept.data,
                            description=form.course_description.data,
                            designation=form.designation.data,
                            credits=form.credits.data)
        db.session.add(course)
        db.session.commit()
        flash('Your course has been created!', 'success')
        return redirect(url_for('add_remove_course'))

    return render_template('faculty_add_remove_course.html', courses=courses, form=form)


@app.route('/cirriculum/course/delete/<int:course_id>', methods=['GET', 'POST'])
@login_required
def delete_course(course_id):    
    if current_user.role == 'Student':
        abort(403)

    course = Course.query.get_or_404(course_id)

    db.session.delete(course)
    db.session.commit()
    flash('The course has been successfully deleted!', 'success')
    
    return redirect(url_for('add_remove_course'))


all_grade=[]
def stored_grade(alist):
    all_grade.append(alist)
    return all_grade

def remove_list():
    for tup in list(all_grade):
        if tup[2] == current_user.EMPLID:
            all_grade.remove(tup)                                        # Clear the list when all data store into db



all_pathway = []
def stored_pathway(alist):
    all_pathway.append(alist)
    return all_pathway

def pathway_check():
    student_info = Enrollement.query.filter_by(student_id=current_user.EMPLID)
    for tup in list(all_pathway):
        if tup[1] == True:
            for flexible_course in student_info:
                if flexible_course.course_id == tup[0]:
                    flexible_course.component = True
                    db.session.commit()
        elif tup[1] == False:
            for free_course in student_info:
                if free_course.course_id == tup[0]:
                    free_course.component = False
                    db.session.commit()
        else:
            print("Null Case!")


def GPA_QPA():
    num_of_courses = Enrollement.query.filter_by(student_id=current_user.EMPLID).count()
    student = Student.query.filter_by(EMPLID=current_user.EMPLID).first()
    scores = Enrollement.query.filter_by(student_id=current_user.EMPLID).all()
    student.GPA = 0     # This is the default initial value in the DB anyway

    for score in scores:
        if score.GPA_point:
            student.GPA += int(score.GPA_point)

    if student.credit_earned == 0:             # divide by zero error check!
        print("No classes added yet!")
    else:
        print("The GPA should be: ", student.GPA, "/", student.credit_earned, " = ", student.GPA/student.credit_earned )
        student.GPA /= student.credit_earned
        # print("Raw Score >> ", student.GPA)
        student.GPA = round(student.GPA, 3)
        # print("Rounded >> ", student.GPA)
        db.session.commit()

    student.QPA = 0
    for value in scores:
        if value.QPA_point:
            if value.course.dept == "CSC":     # The department = "CSC" will give you all CS courses, [required, Group A/B/C, and technical]
                student.QPA += int(value.QPA_point)  
            else:
                student.QPA += 0

    print("The QPA should be: ", student.QPA)
    db.session.commit()


@app.route('/course/info', methods=['GET', 'POST'])
@login_required
def courseinfo_fill():
    if current_user.role == "Faculty":
        return redirect(url_for('faculty'))

    form = SubmitForm()
    course_form = ElectiveForm()
    courses = Course.query.all()
    student = Student.query.filter_by(EMPLID=current_user.EMPLID).first()

    # course_form.elective.choices = [(option.serial) for option in Course.query.filter_by(designation="Liberal Art")]

    if form.validate_on_submit():
        for course_id,grade,EMPLID in all_grade:
            if EMPLID == current_user.EMPLID:
                course = Course.query.get_or_404(course_id)
                print(course_id,grade)
                enrollement = Enrollement.query.filter_by(
                                        student_id=current_user.EMPLID,
                                        course_id = course_id).first()

                if not enrollement:         # if enrollement object (course) does not exist!
                    enrollement = Enrollement(student_id=current_user.EMPLID,
                                            course_id = course_id,
                                            grade = grade)
                    if grade == '':
                        pass
                    elif grade =='IP':
                        student.credit_taken += course.credits
                        enrollement.grade = grade
                        enrollement.GPA_point = None
                        enrollement.QPA_point = None
                        enrollement.attempt = True
                    else:
                        enrollement.GPA_point = int(course.credits*evaluate_GPA(grade))
                        if course.dept == "CSC":        # QPA only applies to CS courses! 
                            enrollement.QPA_point = evaluate_QPA(grade)
                        else:
                            enrollement.QPA_point = None

                        if grade == "F":
                            student.credit_earned += 0
                            enrollement.attempt = True
                            enrollement.passed = False
                        else:
                            student.credit_earned += course.credits
                            enrollement.attempt = True
                            enrollement.passed = True

                    db.session.add(enrollement)
                    db.session.commit()
                elif enrollement.grade == grade:                              # Skip the case of course grade remains the same
                    continue
                else:                           # if enrollement object (course) already does exist!
                    if grade == '':
                        pass
                    elif enrollement.passed == False and grade == "IP":   # Failed the course the first time, retake currently in progress
                        student.credit_earned += 0
                        student.credit_taken += course.credits
                        enrollement.grade = grade
                        enrollement.GPA_point = None
                        enrollement.QPA_point = None
                        enrollement.attempt = True
                        enrollement.passed = False
                    elif enrollement.passed == True and grade == "IP":    # Passed the course the first time, retake currently in progress
                        student.credit_earned -= course.credits           # The first passing grade could have been added by user error! 
                        student.credit_taken += course.credits
                        enrollement.grade = grade
                        enrollement.GPA_point = None
                        enrollement.QPA_point = None
                        enrollement.passed = False
                        enrollement.attempt = True
                    else:
                        if enrollement.attempt == True:
                            if enrollement.passed == False and grade == "F":      # Failed the course the first time, retook it and failed again! (FF)
                                student.credit_earned += 0
                                enrollement.attempt = True
                            elif enrollement.passed == True and grade == "F":     # Passed the course the first time, retook it and got an "F"    (PF)
                                student.credit_earned -= course.credits           # The first passing grade could have been added by user error!
                                enrollement.passed = False
                                enrollement.attempt = True
                            elif enrollement.passed == False and grade != "F":    # Failed the course the first time, retook it and passed!       (FP)
                                student.credit_earned += course.credits
                                student.credit_taken -= course.credits
                                enrollement.passed = True
                            elif enrollement.passed == True and grade != "F":     # Passed the course the first time, retook it and passed again! (PP)
                                student.credit_earned += 0
                            else:
                                student.credit_earned += 0

                    if grade != "IP":
                        enrollement.grade = grade
                        evaluation_score = int(course.credits*evaluate_GPA(grade))
                        enrollement.GPA_point = evaluation_score
                        if course.dept == "CSC":                  # QPA only applies to CS courses 
                            enrollement.QPA_point = evaluate_QPA(grade)
                    else:
                        enrollement.GPA_point = None
                        enrollement.QPA_point = None
                    db.session.commit()
        pathway_check()
        remove_list()
        return redirect(url_for('student_profile'))



    profile_image = url_for('static', filename='Profile_Pics/'+ current_user.profile_image)
    return render_template('course_info_fill.html', title='Course Information',
                            profile_image=profile_image,
                            courses=courses,
                            student=student,
                            all_grade=all_grade,
                            form=form)

# 1000 level Liberal Arts
@app.route('/course/info/elective/1000', methods=['GET', 'POST'])
@login_required
def Liberal_Art_1000():
    if current_user.role == "Faculty":
        abort(403)

    form = ElectiveForm()
    student = Student.query.filter_by(EMPLID=current_user.EMPLID).first()
    student_info = Enrollement.query.filter_by(student_id=current_user.EMPLID)
    courses = Course.query.all()

    form.elective.choices = [(course_option.serial) for course_option in Course.query.filter_by(designation="[CE](1000)")]
    form.elective.choices += [(course_option.serial) for course_option in Course.query.filter_by(designation="[WCGI](1000)")]
    form.elective.choices += [(course_option.serial) for course_option in Course.query.filter_by(designation="[IS](1000)")]
    form.elective.choices += [(course_option.serial) for course_option in Course.query.filter_by(designation="[US](1000)")]

    form.grade.choices = [(grade_option.value) for grade_option in Grade.query.all()]

    if form.validate_on_submit():

        for course in courses:
            # print(course.serial)
            if course.serial == form.elective.data:
                id = course.id
                print(course.id)
                for courseid, grade,EMPLID in all_grade:
                    if courseid == id:                          # removes duplicates from the array!
                        all_grade.remove((id,grade,EMPLID))

        pathway=(id, True, current_user.EMPLID)
        stored_pathway(pathway)

        grades=(id, form.grade.data, current_user.EMPLID)       # This goes into the enrollements table!
        stored_grade(grades)

        return redirect(url_for('courseinfo_fill'))

    return render_template('Elective_Grade_Form.html', title='Course Information', student=student, form=form)


# 2000 level Liberal Arts
@app.route('/course/info/elective/2000', methods=['GET', 'POST'])
@login_required
def Liberal_Art_2000():
    if current_user.role == "Faculty":
        abort(403)

    form = ElectiveForm()
    student = Student.query.filter_by(EMPLID=current_user.EMPLID).first()
    student_info = Enrollement.query.filter_by(student_id=current_user.EMPLID)
    courses = Course.query.all()

    form.elective.choices = [(course_option.serial) for course_option in Course.query.filter_by(designation="[CE](2000)")]
    form.elective.choices += [(course_option.serial) for course_option in Course.query.filter_by(designation="[WCGI](2000)")]
    form.elective.choices += [(course_option.serial) for course_option in Course.query.filter_by(designation="[IS](2000)")]
    form.elective.choices += [(course_option.serial) for course_option in Course.query.filter_by(designation="[US](2000)")]

    form.grade.choices = [(grade_option.value) for grade_option in Grade.query.all()]

    if form.validate_on_submit():

        for course in courses:
            # print(course.serial)
            if course.serial == form.elective.data:
                id = course.id
                print(course.id)
                for courseid, grade, EMPLID in all_grade:
                    if courseid == id:
                        all_grade.remove((id,grade,EMPLID))

        pathway=(id, True, current_user.EMPLID)
        stored_pathway(pathway)

        grades=(id,form.grade.data,current_user.EMPLID)
        stored_grade(grades)

        return redirect(url_for('courseinfo_fill'))

    return render_template('Elective_Grade_Form.html', title='Course Information', student=student, form=form)



# Free Electives:
@app.route('/course/info/elective/generic', methods=['GET', 'POST'])
@login_required
def Free_Electives():
    if current_user.role == "Faculty":
        abort(403)

    form = ElectiveForm()
    student = Student.query.filter_by(EMPLID=current_user.EMPLID).first()
    student_info = Enrollement.query.filter_by(student_id=current_user.EMPLID)
    courses = Course.query.all()

    form.elective.choices = [(course_option.serial) for course_option in Course.query.filter_by(designation="[CE](1000)")]
    form.elective.choices += [(course_option.serial) for course_option in Course.query.filter_by(designation="[WCGI](1000)")]
    form.elective.choices += [(course_option.serial) for course_option in Course.query.filter_by(designation="[IS](1000)")]
    form.elective.choices += [(course_option.serial) for course_option in Course.query.filter_by(designation="[US](1000)")]
    form.elective.choices += [(course_option.serial) for course_option in Course.query.filter_by(designation="[CE](2000)")]
    form.elective.choices += [(course_option.serial) for course_option in Course.query.filter_by(designation="[WCGI](2000)")]
    form.elective.choices += [(course_option.serial) for course_option in Course.query.filter_by(designation="[IS](2000)")]
    form.elective.choices += [(course_option.serial) for course_option in Course.query.filter_by(designation="[US](2000)")]

    # There is overlap between Technical and Free Electives.


    form.grade.choices = [(grade_option.value) for grade_option in Grade.query.all()]

    if form.validate_on_submit():

        for course in courses:
            # print(course.serial)
            if course.serial == form.elective.data:
                id = course.id
                print(course.id)
                for courseid, grade,EMPLID in all_grade:        # removes duplicate courses!
                    if courseid == id:
                        all_grade.remove((id,grade,EMPLID))

        pathway=(id, False, current_user.EMPLID)
        stored_pathway(pathway)

        grades=(id,form.grade.data,current_user.EMPLID)
        stored_grade(grades)

        return redirect(url_for('courseinfo_fill'))

    return render_template('Elective_Grade_Form.html', title='Course Information', student=student, form=form)


# Technical_Electives
@app.route('/course/info/elective/technical', methods=['GET', 'POST'])
@login_required
def Technical_Electives():
    if current_user.role == "Faculty":
        abort(403)

    form = ElectiveForm()
    student = Student.query.filter_by(EMPLID=current_user.EMPLID).first()
    courses = Course.query.all()

    form.elective.choices = [(course_option.serial) for course_option in Course.query.filter_by(serial='ENGR 27600')]      # Engineering Economics counts as a Tech elective, Eco 10400 doesn't
    form.elective.choices += [(course_option.serial) for course_option in Course.query.filter_by(designation="Technical Elective")]

    # NOTE: CS courses will not be displayed if they are selected using this route. [X] - Priority: LOW

    form.grade.choices = [(grade_option.value) for grade_option in Grade.query.all()]

    if form.validate_on_submit():

        for course in courses:
            # print(course.serial)
            if course.serial == form.elective.data:
                id = course.id
                print(course.id)
                for courseid, grade,EMPLID in all_grade:
                    if courseid == id:
                        all_grade.remove((id,grade,EMPLID))

        grades=(id,form.grade.data,current_user.EMPLID)
        stored_grade(grades)

        return redirect(url_for('courseinfo_fill'))

    return render_template('Elective_Grade_Form.html', title='Course Information', student=student, form=form)



def evaluate_QPA(grade):
    switcher = {
        "A+": 2.0,
        "A": 2.0,
        "A-": 2.0,
        "B+": 1.0,
        "B": 1.0,
        "B-": 1.0,
        "C+": 0.0,
        "IP": 0.0,
        "C": 0.0,
        "C-": 0.0,
        "D+": -1.0,
        "D": -1.0,
        "F": -2.0,
    }

    # get() method of dictionary data type returns
    # value of passed argument if it is present
    # in dictionary otherwise second argument will
    # be assigned as default value of passed argument
    return switcher.get(grade, 0)


def evaluate_GPA(grade):

    if grade == "IP":
        return None 
    
    switcher = {
        "A+": 4.0,
        "A": 4.0,
        "A-": 3.7,
        "B+": 3.3,
        "B": 3.0,
        "B-": 2.7,
        "C+": 2.3,
        "C": 2.0,
        "C-": 1.7,
        "D+": 1.3,
        "D": 1.0,
        "F": 0.0,
    }

    # get() method of dictionary data type returns
    # value of passed argument if it is present
    # in dictionary otherwise second argument will
    # be assigned as default value of passed argument
    return switcher.get(grade, None)


@app.route('/course/info/edit/<int:course_id>', methods=['GET', 'POST'])
@login_required
def courseinfo_edit(course_id):
    if current_user.role == "Faculty":
        abort(403)

    form = CourseInfoForm()
    student = Student.query.filter_by(EMPLID=current_user.EMPLID).first()
    course = Course.query.get_or_404(course_id)

    form.grade.choices = [(option.value) for option in Grade.query.all()]

    if form.validate_on_submit():
        grades=(course_id,form.grade.data,current_user.EMPLID)
        for id, grade,EMPLID in all_grade:
            if course_id == id and EMPLID == current_user.EMPLID :
                all_grade.remove((id,grade,EMPLID))
        stored_grade(grades)

        return redirect(url_for('courseinfo_fill'))

    return render_template('course_info_edit.html', title='Course Information', student=student,course=course, form=form)


# Faculty fill out the basic info on the first time once they signed in
@app.route('/facultyinfo_fill/', methods=['GET', 'POST'])
def facultyinfo_fill():
    if current_user.role == "Student":
        abort(403)
    
    form = FacultyInfoForm()
    profile_image = url_for('static', filename='Profile_Pics/'+ current_user.profile_image)

    if form.validate_on_submit():
        if form.picture.data:                                   # If there exists valid form picture data (i.e .png, .jpg file)
            picture_file = save_picture(form.picture.data)      # Save the image!
            current_user.profile_image = picture_file           # Update the current user profile photo in the database!
            print("Execution Complete!")

        faculty = Faculty(EMPLID=form.EMPLID.data,
                          firstname=form.firstname.data,
                          lastname=form.lastname.data,
                          staff_role=form.staff_role.data)
        db.session.add(faculty)
        current_user.EMPLID = form.EMPLID.data
        db.session.commit()
        flash('Info Updated', 'success')
        return redirect(url_for('faculty'))

    return render_template('facultyinfo_fill.html', title='Faculty Form', profile_image=profile_image, form=form)


# function for logout
@app.route('/logout')
def logout():
    remove_list()
    logout_user()
    return redirect(url_for('home'))


@app.route('/student/profile/edit', methods=['GET', 'POST'])
@login_required
def student_profile_edit():
    if current_user.role == "Faculty":
        abort(403)

    form = UpdateStudentAccountForm()
    EMPLID=current_user.EMPLID
    student = Student.query.filter_by(EMPLID=EMPLID).first()

    if form.validate_on_submit():
        if form.picture.data:                                   # If there exists valid form picture data (i.e .png, .jpg file)
            picture_file = save_picture(form.picture.data)      # Save the image!
            current_user.profile_image = picture_file           # Update the current user profile photo in the database!

        current_user.EMPLID=form.EMPLID.data
        current_user.bio=form.bio.data
        current_user.email = form.email.data
        student.firstname = form.firstname.data
        student.lastname = form.lastname.data
        db.session.commit()                                     # commit changes to the database!
        flash('Your account info has been updated successfully!', 'success')
        return redirect(url_for('student_profile'))
    elif request.method == 'GET':
        form.EMPLID.data = current_user.EMPLID
        form.email.data = current_user.email
        form.bio.data = current_user.bio
        form.firstname.data = student.firstname
        form.lastname.data = student.lastname

    profile_image = url_for('static', filename='Profile_Pics/'+ current_user.profile_image)
    return render_template("student_profile_edit.html", title="Student Profile Edit", profile_image=profile_image, form=form)


@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    if current_user.role == "Faculty":
        abort(403)

    GPA_QPA()
    form = UpdateStudentAccountForm()
    remove_list()

    if form.validate_on_submit():
        if form.picture.data:                                   # If there exists valid form picture data (i.e .png, .jpg file)
            picture_file = save_picture(form.picture.data)      # Save the image!
            current_user.profile_image = picture_file           # Update the current user profile photo in the database!

        current_user.EMPLID = form.EMPLID.data
        current_user.email = form.email.data
        db.session.commit()  # commit changes to the database!
        flash('Your account info has been updated successfully!', 'success')
        return redirect(url_for('student_profile'))
    elif request.method == 'GET':
        form.EMPLID.data = current_user.EMPLID
        form.email.data = current_user.email

    profile_image = url_for('static', filename='Profile_Pics/'+ current_user.profile_image)
    return render_template("student_profile.html", title="Student Profile", profile_image=profile_image, form=form)

def get_Free_Electives():
    free_electives  = [ (course_option) for course_option in Course.query.filter_by(designation="[CE](1000)") ]
    free_electives += [ (course_option) for course_option in Course.query.filter_by(designation="[WCGI](1000)") ]
    free_electives += [ (course_option) for course_option in Course.query.filter_by(designation="[IS](1000)") ]
    free_electives += [ (course_option) for course_option in Course.query.filter_by(designation="[US](1000)") ]
    free_electives += [ (course_option) for course_option in Course.query.filter_by(designation="[CE](2000)") ]
    free_electives += [ (course_option) for course_option in Course.query.filter_by(designation="[WCGI](2000)") ]
    free_electives += [ (course_option) for course_option in Course.query.filter_by(designation="[IS](2000)") ]
    free_electives += [ (course_option) for course_option in Course.query.filter_by(designation="[US](2000)") ]
    # print(free_electives[0].id, free_electives[0].serial, free_electives[0].credits)

    return free_electives


@app.route('/checklist')
@login_required
def checklist():
    if current_user.role == "Faculty":
        abort(403)

    courses = Course.query.all()
    cs_courses = Course.query.filter_by(dept='CSC').all()
    lib_req_courses = Course.query.filter_by(designation ="Required Liberal Art").all()
    science_courses = Course.query.filter_by(designation="Science Elective").all()
    math_courses = Course.query.filter_by(dept='MATH').all()
    student_info = Enrollement.query.filter_by(student_id=current_user.EMPLID)

    free_electives = get_Free_Electives()       # Gives me all the Free Electives
    # print(free_electives)

    courses_array = []
    for courseObj in student_info:
        # print(courseObj)
        courses_array += Course.query.filter_by(id=courseObj.course_id)

    pathway_courses = []
    free_courses = []
    for course in student_info:
        if course.component == True:
            pathway_courses += Course.query.filter_by(id=course.course_id)
            # print(pathway_courses)
        elif course.component == False:
            free_courses += Course.query.filter_by(id=course.course_id)
            # print(free_courses)
        else:
            pass    # This is the case when the component is NULL ...

    student = Student.query.filter_by(EMPLID=current_user.EMPLID).first()
    scores = Enrollement.query.filter_by(student_id=current_user.EMPLID).all()

    #progress bar for Computer Science
    cs_count = Course.query.filter_by(dept="CSC", designation="Core Requirement").count()
    checklistProgressInterval_CS = round(100 / cs_count, 2)   # Number of required CS courses
    print(checklistProgressInterval_CS)
    CS_width = 0
    for cs_course in cs_courses:
        for score in scores:
            if score.grade == "IP":
                pass
            elif score.grade and cs_course.id == score.course_id:
                if cs_course.dept == "CSC" and cs_course.designation == "Core Requirement":
                        CS_width = round( CS_width + checklistProgressInterval_CS, 1)
    CS_width_num = int(CS_width/100 * cs_count) 

    #progress bar for Computer Science Electives
    checklistProgressInterval_CSE = 100 / 4     # Leaving this as four since this is not counting all courses but instead a 4 out of many courses.
    CSE_width = 0
    for cs_elective in courses_array:
        if cs_elective.dept == "CSC" and cs_elective.id > 18:
            CSE_width += checklistProgressInterval_CSE
    CSE_width_num = CSE_width/100 * 4

    #progress bar for Math
    math_count = Course.query.filter_by(dept="MATH", designation="Core Requirement").count()
    checklistProgressInterval_Math = 100 / math_count
    Math_width = 0
    for math_course in courses_array:
        for score in scores:
            if score.grade == "IP":
                pass
            elif score.grade and math_course.id == score.course_id:
                if math_course.dept == "MATH" and math_course.designation == "Core Requirement":
                    Math_width += checklistProgressInterval_Math
    Math_width_num = Math_width/100 * math_count

    #progress bar for Science
    checklistProgressInterval_Science = 100 / 3
    Science_width = 0
    for science_elective in science_courses:
        for score in scores:
            if score.grade == "IP":
                pass
            elif score.grade and science_elective.id == score.course_id:
                Science_width += checklistProgressInterval_Science
    Science_width_num = Science_width/99 * 3

    #progress bar for Technical Electives
    checklistProgressInterval_TE = 100 / 2
    Tech_width = 0
    #Need to fix to cater to technical electives
    for technical_elective in courses_array:
        if technical_elective.designation == "Technical Elective":
            Tech_width += checklistProgressInterval_TE
        elif technical_elective.serial == "ENGR 27600":     # ENGR 27600: Engineering Economics can count as a Technical Elective/Eco 10400 does not count since it's 1000 level.
            Tech_width += checklistProgressInterval_TE
    Tech_width_num = Tech_width/100 * 2

    #progress bar for Flexible Pathways
    checklistProgressInterval_Art = 100 / 4
    Art_width = 0
    for liberal_art_course in pathway_courses:
        Art_width += checklistProgressInterval_Art
    Art_width_num = Art_width/100 * 4

    #progress bar for Liberal Arts
    req_lib_count = Course.query.filter_by(designation="Required Liberal Art").count()
    req_lib_count -= 1      # we decrement the count by 1 because a Student can take either ENGR Economics or Eco 104 but not both 
    checklistProgressInterval_Lib_Art = 100 / req_lib_count
    Lib_Art_width = 0
    for liberal_art_course_req in lib_req_courses:
        for score in scores:
            if score.grade == "IP":
                pass
            elif score.grade and liberal_art_course_req.id == score.course_id:
                Lib_Art_width += checklistProgressInterval_Lib_Art
    Lib_Art_width_num = Lib_Art_width/100 * req_lib_count


    #progress bar for free electives    
    checklistProgressInterval_FE = 100 / 2
    FE_width = 0
    for course in free_courses:
        FE_width += checklistProgressInterval_FE
    FE_width_num = FE_width/100 * 2
        

    if student.credit_earned >= 126: 
        if int(Math_width) == 100 and int(Science_width) == 100 and int(Tech_width) == 100 and int(CSE_width) == 100 and int(Art_width) == 100 and int(CS_width) == 100 and int(FE_width) == 100 and int(Lib_Art_width) == 100:
            student.graduating = True
            db.session.commit()


    profile_image = url_for('static', filename='Profile_Pics/'+ current_user.profile_image)
    return render_template('checklist.html', title='Checklist',
                            profile_image=profile_image,
                            courses=courses,
                            lib_req_courses = lib_req_courses,
                            student=student,
                            scores=scores,
                            cs_courses=cs_courses,
                            science_courses = science_courses,
                            courses_array=courses_array,
                            pathway_courses=pathway_courses,
                            free_courses=free_courses,
                            math_courses=math_courses,
                            math_count=math_count, 
                            cs_count=cs_count, 
                            req_lib_count=req_lib_count, 
                            CS_width_num =  int(CS_width_num),
                            CSE_width_num =  int(CSE_width_num),
                            Math_width_num =  int(Math_width_num),
                            Science_width_num = int(Science_width_num),
                            Tech_width_num = int(Tech_width_num),
                            Art_width_num = int(Art_width_num),
                            FE_width_num = int(FE_width_num),
                            Lib_Art_width_num = int(Lib_Art_width_num),
                            CS_width=int(CS_width),
                            CSE_width=CSE_width,
                            Math_width=Math_width,
                            Science_width=Science_width,
                            Tech_width=Tech_width,
                            Art_width=Art_width,
                            FE_width=FE_width,
                            Lib_Art_width=Lib_Art_width)


@app.route('/faculty/', methods=['GET', 'POST'])
@login_required
def faculty():
    form = SearchForm()

    year = str(date.year)
    semester = get_semester(date.today())

    notes = Notes.query.filter(Notes.semester==semester,
                                (Notes.be_advised == None)|(Notes.be_advised == False)).all()
    
    secondnotes = Notes.query.filter_by(be_advised=True,
                                    approval=None,
                                    semester = semester).all()

    profile_image = url_for('static', filename='Profile_Pics/' + current_user.profile_image)

    if request.method == "POST":
        search = "%{}%".format(form.search.data)
        notes = Notes.query.filter(Notes.EMPLID.like(search),Notes.semester==semester,
                                (Notes.be_advised == None)|(Notes.be_advised == False)).all()

    return render_template("faculty.html", title="Faculty Profile", profile_image=profile_image, notes=notes, semester=semester, year=year, form=form, secondnotes=secondnotes)


@app.route('/graduating/class', methods=['GET', 'POST'])
@login_required
def graduating_class():
    if current_user.role == "Student":
        abort(403)

    year = date.today().strftime("%Y")      # This is using system time, so this can be circumvented!     
    semester = get_semester(date.today())

    graduates = Student.query.filter_by(graduating=True).all()

    Transcripts = []
    for i in graduates:
        Transcripts = i.transcript

    export_csv()

    return render_template("graduating_class.html", title=f"Class of {year}", year=year, semester=semester, Transcripts=Transcripts, graduates=graduates)


@app.route('/graduating/class/export')
@login_required
def export_csv():
    if current_user.role == "Student":
        abort(403)

    f = open('./adviseme/static/export/CCNY_graduates.csv', 'w')
    out = csv.writer(f)
    out.writerow(['EMPLID', 'First Name', 'Last Name', 'GPA', 'QPA', 'Citymail address' ])

    # NOTE: Not optimal given I was passing this query into the function before and it was working fine. Scope can be a pain at times. 
    # graduates = Student.query.join(User, Student.EMPLID == User.EMPLID).filter(Student.graduating == True).all()      

    graduates = db.session.query(User, Student).outerjoin(User, User.EMPLID == Student.EMPLID).filter(Student.graduating == True).all()

    for student in graduates:
        out.writerow([student[1].EMPLID, student[1].firstname, student[1].lastname, student[1].GPA, student[1].QPA, student[0].email ])

    f.close()

    f_excel = pd.read_csv ('./adviseme/static/export/CCNY_graduates.csv')
    f_excel.to_excel('./adviseme/static/export/CCNY_graduates.xlsx')

    return f 

# function to get current semester
def get_semester(date):
    year = str(date.year)
    m = date.month

    if m in (2,3,4,5,6,7):
        semester='FALL'
    elif m in (8,9,10,11,12,1):
        semester='SPRING'
    else:
        raise IndexError("Invalid date")

    return semester

#Faculty can edit workflow:
@app.route('/EditWorkflow/', methods=['GET', 'POST'])
@login_required
def EditWorkflow():
    if current_user.role == "Student":
        abort(403)

    form = EditworkflowForm()
    editworkflow = Editworkflow.query.filter_by(id=1).first()
    if form.validate_on_submit():
        editworkflow.under_advisement=form.under_advisement.data
        editworkflow.under_faculty=form.under_faculty.data
        editworkflow.under_academic=form.under_academic.data
        editworkflow.under_enrollment=form.under_enrollment.data

        editworkflow.above_advisement=form.above_advisement.data
        editworkflow.above_academic=form.above_academic.data
        editworkflow.above_faculty=form.above_faculty.data
        editworkflow.above_enrollment=form.above_enrollment.data
        db.session.commit()

    elif request.method == 'GET':
        form.under_advisement.data=editworkflow.under_advisement
        form.under_faculty.data=editworkflow.under_faculty
        form.under_academic.data=editworkflow.under_academic
        form.under_enrollment.data=editworkflow.under_enrollment

        form.above_advisement.data=editworkflow.above_advisement
        form.above_academic.data=editworkflow.above_academic
        form.above_faculty.data=editworkflow.above_faculty
        form.above_enrollment.data=editworkflow.above_enrollment


    return render_template("EditWorkflow.html", title="Edit Workflow", form=form ,editworkflow=editworkflow)


# Student can view all notes in this advisingNotesHome route
@app.route('/advisingNotesHome/')
@login_required
def advisingNotesHome():
    EMPLID = current_user.EMPLID
    notes = Notes.query.filter_by(EMPLID=EMPLID).all()
    return render_template('advisingNotesHome.html', notes=notes)


#student can view the direct note by clicking on the note if below 45 credits only see academic notes
@app.route('/advisingNotes/<int:note_id>')
@login_required
def advisingNotes(note_id):
    #note = Notes.query.get_or_404(note_id)
    note=Notes.query.filter_by(id=note_id).first()
    return render_template('advisingNotes.html', title='advisingNotes', note=note)



# faculty can see all the advising notes from students
# if user is academic advisor, only see students' note below 45 credits.
# elif user is faculty advisor, will see students' note above 45 credits
@app.route('/AdvisingHome/')
@login_required
def AdvisingHome():
    notes = Notes.query.all()
    return render_template('AdvisingHome.html', notes=notes)

# academic advisor should review completed advising forms and notes in this page
@app.route('/noteReviewHome')
@login_required
def noteReviewHome():

    semester = get_semester(date.today())
    notes = Notes.query.filter_by(be_advised=True,
                                    approval=None,
                                    semester = semester).all()

    return render_template('noteReviewHome.html',notes=notes)


# academic advisor approve advisement then leave academic notes
@app.route('/noteReview/<int:note_id>', methods=['GET', 'POST'])
@login_required
def noteReview(note_id):
    if current_user.role == "Student":
        abort(403)

    notes=Notes.query.get_or_404(note_id)
    form = AcademicReviewForm()
    student_id = notes.Owner.EMPLID

    student = Student.query.filter_by(EMPLID=student_id).first()

    temp = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id).all()
    course = {i[0]:i[1] for i in temp}
    for i in Course.query.all():
        if i not in course:
            course[i] = None

    electives = dict()
    tech_elec = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id, Course.designation=="Technical Elective").all()
    CE = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id, (Course.designation=="[CE](1000)")|(Course.designation=="[CE](2000)")).all()
    US = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id, (Course.designation=="[US](1000)")|(Course.designation=="[US](2000)")).all()
    IS = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id, (Course.designation == "[IS](1000)")|(Course.designation == "[IS](2000)")).all()
    WCGI = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id == Course.id) \
        .filter(Enrollement.student_id == student_id,
                (Course.designation == "[WCGI](1000)")|(Course.designation == "[WCGI](2000)")).all()
    electives["Technical Elective"] = tech_elec
    electives["CE"] = CE
    electives["US"] = US
    electives["IS"] = IS
    electives["WCGI"] = WCGI


    if form.validate_on_submit():
        notes.academic_note=form.academic_note.data
        notes.additional=form.additional.data
        notes.approval=form.approval.data
        db.session.commit()
        flash('Confirmed!', 'success')
        return redirect(url_for('faculty'))
    elif request.method == 'GET':
        form.academic_note.data=notes.academic_note
        form.additional.data=notes.additional
        form.approval.data=notes.approval

    return render_template('AcademicAdvisorReview.html', title='Academic Advisor Note Review', form=form, course=course, electives=electives, student=student, notes=notes)



@app.route('/workflow/', methods=['GET', 'POST'])
@login_required
def workflow():
    todaydate = date.today()
    semester = get_semester(todaydate)
    notes = Notes.query.filter_by(
                                EMPLID=current_user.EMPLID,
                                semester = semester,
                                year =todaydate.year ).first()
    form=SubmitForm()
    editworkflow = Editworkflow.query.filter_by(id=1).first()
    if form.validate_on_submit():
        
        enrollment = Enrollement.query.filter_by( grade='',
                student_id=current_user.EMPLID).all()
    
        for enrollement in enrollment:
            db.session.delete(enrollement)
        db.session.commit()
        return redirect( url_for('Update_Advisement',note_id=notes.id ))  

    return render_template('workflow.html', title="workflow",notes=notes,editworkflow=editworkflow,form=form)

@app.route('/Preview/Under/Workflow/')
@login_required
def preview_workflow():
    todaydate = date.today()
    semester = get_semester(todaydate)
    notes = Notes.query.filter_by(
                                EMPLID=current_user.EMPLID,
                                semester = semester,
                                year =todaydate.year ).first()
    editworkflow = Editworkflow.query.filter_by(id=1).first()
    return render_template('PreviewWorkflow.html', title="preview workflow",notes=notes,editworkflow=editworkflow)

@app.route('/Preview/Above/Workflow/')
@login_required
def preview_workflow2():
    todaydate = date.today()
    semester = get_semester(todaydate)
    notes = Notes.query.filter_by(
                                EMPLID=current_user.EMPLID,
                                semester = semester,
                                year =todaydate.year ).first()
    editworkflow = Editworkflow.query.filter_by(id=1).first()
    return render_template('WorkflowPreview2.html', title="preview workflow",notes=notes,editworkflow=editworkflow)

@app.route('/workflow2/')
@login_required
def workflow2():
    todaydate = date.today()
    semester = get_semester(todaydate)
    notes = Notes.query.filter_by(
                                EMPLID=current_user.EMPLID,
                                semester = semester,
                                year =todaydate.year ).first()

    if notes:
        return redirect(url_for('workflow'))
    return render_template('workflow2.html', title="workflow")


@app.route('/Advisement', methods=['GET', 'POST'])
@login_required
def Advisement():
    if current_user.role == "Faculty":
        abort(403)

    form = AdvisementForm()
    GPA_QPA()
    student = Student.query.filter_by(EMPLID=current_user.EMPLID).first()
    transcript = url_for('static', filename='Transcript/' + student.transcript)

    enrolled = {i.course_id: i.grade for i in current_user.studentOwner.courses}
    course_obj = {i[0]: i[1] for i in form.course.iter_choices()}  # checkbox_field_id: course_object

    electives = []
    tech_elec = Course.query.join(Enrollement, Enrollement.course_id == Course.id).add_columns(Enrollement.grade) \
        .filter(Enrollement.student_id == current_user.studentOwner.EMPLID,
                Course.designation == "Technical Elective").all()
    if len(tech_elec) >= 2:
        electives.extend(tech_elec[0:2])
    elif len(tech_elec) == 1:
        electives.extend(tech_elec)  # 0
        electives.append(None)  # 1
    else:
        electives.append(None)  # 0
        electives.append(None)  # 1

    ce = Course.query.join(Enrollement, Enrollement.course_id == Course.id).add_columns(Enrollement.grade) \
        .filter((Course.designation == "[CE](1000)") | (Course.designation == "[CE](2000)"),
                Enrollement.student_id == current_user.studentOwner.EMPLID).first()
    use = Course.query.join(Enrollement, Enrollement.course_id == Course.id).add_columns(Enrollement.grade) \
        .filter((Course.designation == "[US](1000)") | (Course.designation == "[US](2000)"),
                Enrollement.student_id == current_user.studentOwner.EMPLID).first()
    is_ = Course.query.join(Enrollement, Enrollement.course_id == Course.id).add_columns(Enrollement.grade) \
        .filter((Course.designation == "[IS](1000)") | (Course.designation == "[IS](2000)"),
                Enrollement.student_id == current_user.studentOwner.EMPLID).first()
    wcgi = Course.query.join(Enrollement, Enrollement.course_id == Course.id).add_columns(Enrollement.grade) \
        .filter((Course.designation == "[WCGI](1000)") | (Course.designation == "[WCGI](2000)"),
                Enrollement.student_id == current_user.studentOwner.EMPLID).first()
    electives.append(ce)  # 2
    electives.append(use)  # 3
    electives.append(is_)  # 4
    electives.append(wcgi)  # 5

    if form.validate_on_submit():
        # return "{}".format(form.tech_elec_check2.data) #for test
        if form.transcript.data:  # If there exists valid form transcript data (i.e .pdf file)
            transcript_file = save_transcript(form.transcript.data, form.semester.data, form.year.data,
                                              current_user.EMPLID)  # Save the transcript!
            student.transcript = transcript_file  # Update the current user transcript in the database!
            student.needs_advising = True         # Set this to true upon the form being submitted for approval 
            db.session.commit()  # Commit changes to the DB
            print("Execution Complete!")

        for course in form.course.data:
            enrollement = Enrollement.query.filter_by(
                student_id=current_user.EMPLID,
                course_id=course.id).first()
            if not enrollement:
                enrollement = Enrollement(student_id=current_user.EMPLID,
                                          course_id=course.id,
                                          attempt=True)
                db.session.add(enrollement)
            else:
                enrollement.grade = ''
                enrollement.attempt = True

        if form.tech_elec_check1.data == True:
            for course in form.tech_elec1.data:
                enrollement = Enrollement.query.filter_by(
                    student_id=current_user.EMPLID,
                    course_id=course.id).first()
                if not enrollement:
                    enrollement = Enrollement(student_id=current_user.EMPLID,
                                              course_id=course.id,
                                              attempt=True)
                    db.session.add(enrollement)
                else:
                    enrollement.grade = ''
                    enrollement.attempt = True
        if form.tech_elec_check2.data == True:
            for course in form.tech_elec2.data:
                enrollement = Enrollement.query.filter_by(
                    student_id=current_user.EMPLID,
                    course_id=course.id).first()
                if not enrollement:
                    enrollement = Enrollement(student_id=current_user.EMPLID,
                                              course_id=course.id,
                                              attempt=True)
                    db.session.add(enrollement)
                else:
                    enrollement.grade = ''
                    enrollement.attempt = True
        if form.CE_check.data == True:
            for course in form.CE.data:
                enrollement = Enrollement.query.filter_by(
                    student_id=current_user.EMPLID,
                    course_id=course.id).first()
                if not enrollement:
                    enrollement = Enrollement(student_id=current_user.EMPLID,
                                              course_id=course.id,
                                              attempt=True)
                    db.session.add(enrollement)
                else:
                    enrollement.grade = ''
                    enrollement.attempt = True

        if form.USE_check.data == True:
            for course in form.USE.data:
                enrollement = Enrollement.query.filter_by(
                    student_id=current_user.EMPLID,
                    course_id=course.id).first()
                if not enrollement:
                    enrollement = Enrollement(student_id=current_user.EMPLID,
                                              course_id=course.id,
                                              attempt=True)
                    db.session.add(enrollement)
                else:
                    enrollement.grade = ''
                    enrollement.attempt = True

        if form.IS_check.data == True:
            for course in form.IS.data:
                enrollement = Enrollement.query.filter_by(
                    student_id=current_user.EMPLID,
                    course_id=course.id).first()
                if not enrollement:
                    enrollement = Enrollement(student_id=current_user.EMPLID,
                                              course_id=course.id,
                                              attempt=True)
                    db.session.add(enrollement)
                else:
                    enrollement.grade = ''
                    enrollement.attempt = True
        if form.WCGI_check.data == True:
            for course in form.WCGI.data:
                enrollement = Enrollement.query.filter_by(
                    student_id=current_user.EMPLID,
                    course_id=course.id).first()
                if not enrollement:
                    enrollement = Enrollement(student_id=current_user.EMPLID,
                                              course_id=course.id,
                                              attempt=True)
                    db.session.add(enrollement)
                else:
                    enrollement.grade = ''
                    enrollement.attempt = True

        note = Notes(EMPLID=current_user.EMPLID,year=form.year.data,semester=form.semester.data)
        db.session.add(note)
        db.session.commit()
        flash("Advisement Form Submitted!", "success")
        return redirect(url_for('student_profile'))

    return render_template('AdvisementForm.html', title="Live Advisement Form", form=form, student=student,
                           enrolled=enrolled, course_obj=course_obj, transcript=transcript, electives=electives)


@app.route('/Advisement/Transcript', methods=['GET', 'POST'])
@login_required
def View_Transcript():
    if current_user.role == "Faculty":
        abort(403)

    student = Student.query.filter_by(EMPLID=current_user.EMPLID).first()
    transcript = url_for('static', filename='Transcript/'+ student.transcript)

    return render_template('Transcript_Cirriculum.html', title="Cirriculum/Transcript", student=student, transcript=transcript)


# faculty can go editing the direct advising note in this route
@app.route('/faculty/review/<int:note_id>', methods=['GET', 'POST'])
@login_required
def faculty_review(note_id):
    if current_user.role == "Student":
        abort(403)

    notes = Notes.query.get_or_404(note_id)
    student_id = notes.Owner.EMPLID
    student = Student.query.filter_by(EMPLID=student_id).first()

    form = FacultyReviewForm()
    temp = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id).all()
    course = {i[0]:i[1] for i in temp}
    for i in Course.query.all():
        if i not in course:
            course[i] = None

    electives = dict()
    tech_elec = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id, Course.designation=="Technical Elective").all()
    CE = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id, (Course.designation=="[CE](1000)")|(Course.designation=="[CE](2000)")).all()
    US = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id, (Course.designation=="[US](1000)")|(Course.designation=="[US](2000)")).all()
    IS = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id, (Course.designation == "[IS](1000)")|(Course.designation == "[IS](2000)")).all()
    WCGI = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id == Course.id) \
        .filter(Enrollement.student_id == student_id,
                (Course.designation == "[WCGI](1000)")|(Course.designation == "[WCGI](2000)")).all()
    electives["Technical Elective"] = tech_elec
    electives["CE"] = CE
    electives["US"] = US
    electives["IS"] = IS
    electives["WCGI"] = WCGI

    if form.validate_on_submit():
        notes.academic_comment=form.q1.data
        notes.next_semester_comment=form.q2.data
        notes.q3=form.q3.data
        notes.tutorial=form.tutorial.data
        notes.counseling=form.counseling.data
        notes.consultation=form.consultation.data
        notes.career=form.career.data
        notes.scholarships=form.scholarships.data
        notes.internship=form.internship.data
        notes.followup=form.followup.data
        notes.be_advised=form.approve.data
        if notes.Owner.credit_earned <= 45 and form.approve.data == True:
            notes.approval = True
        student.needs_advising = False          # Set this to False upon approval
        db.session.commit()
        flash('Notes saved!', 'success')
        return redirect(url_for('faculty'))
    elif request.method == 'GET':
        form.q1.data=notes.academic_comment
        form.q2.data=notes.next_semester_comment
        form.q3.data=notes.q3
        form.tutorial.data=notes.tutorial
        form.counseling.data=notes.counseling
        form.consultation.data=notes.consultation
        form.career.data=notes.career
        form.scholarships.data=notes.scholarships
        form.internship.data=notes.internship
        form.followup.data=notes.followup
        form.approve.data=notes.be_advised

    return render_template('FacultyAdvisorReview.html', form=form, course=course, electives=electives, student=student, notes=notes)


@app.route('/faculty/review/transcript/<int:student_id>', methods=['GET', 'POST'])
@login_required
def Faculty_View_Transcript(student_id):
    if current_user.role == "Student":
        abort(403)
    student = Student.query.filter_by(EMPLID=student_id).first()
    transcript = url_for('static', filename='Transcript/' + student.transcript)

    return render_template('Transcript_Cirriculum.html', tittle="Cirriculum/Transcript", student=student,
                           transcript=transcript)


@app.route('/faculty/archiveHome', methods=['GET', 'POST'])
@login_required
def FacultyArchiveHome():
    if current_user.role == "Student":
        abort(403)
    notes = Notes.query.filter_by(FacultyEMPLID=current_user.FacultyOwner.EMPLID, be_advised=True).all()

    notes = Notes.query.filter_by(be_advised=True).all()
    students_with_notes = list(itertools.groupby(notes, lambda note: note.Student))
    students = list(map(lambda x: (x[0], len(x[0].advisingnote)), students_with_notes))
    students = sorted(students, key=lambda x:x[0].lastname)

    return render_template('archiveHome.html', tittle="Faculty Advisor Archive", students=students)


@app.route('/academic/archiveHome', methods=['GET', 'POST'])
@login_required
def AcademicArchiveHome():
    if current_user.role == "Student":
        abort(403)
    notes = Notes.query.filter_by(be_advised=True, approval=True).all()
    students_with_notes = list(itertools.groupby(notes, lambda note: note.Student))
    students = list(map(lambda x: (x[0], len(x[0].advisingnote)), students_with_notes))
    students = sorted(students, key=lambda x: x[0].lastname)

    return render_template('archiveHome.html', tittle="Academic Advisor Archive", students=students)


@app.route('/faculty/archiveHome/<int:note_id>', methods=['GET', 'POST'])
@login_required
def FacultyArchive(note_id):
    if current_user.role == "Student":
        abort(403)

    notes = Notes.query.get_or_404(note_id)
    student_id = notes.Owner.EMPLID
    student = Student.query.filter_by(EMPLID=student_id).first()

    form = FacultyReviewForm()
    temp = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id).all()
    course = {i[0]:i[1] for i in temp}
    for i in Course.query.all():
        if i not in course:
            course[i] = None

    electives = dict()
    tech_elec = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id, Course.designation=="Technical Elective").all()
    CE = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id, (Course.designation=="[CE](1000)")|(Course.designation=="[CE](2000)")).all()
    US = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id, (Course.designation=="[US](1000)")|(Course.designation=="[US](2000)")).all()
    IS = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id, (Course.designation == "[IS](1000)")|(Course.designation == "[IS](2000)")).all()
    WCGI = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id == Course.id) \
        .filter(Enrollement.student_id == student_id,
                (Course.designation == "[WCGI](1000)")|(Course.designation == "[WCGI](2000)")).all()
    electives["Technical Elective"] = tech_elec
    electives["CE"] = CE
    electives["US"] = US
    electives["IS"] = IS
    electives["WCGI"] = WCGI


    return render_template('FacultyArchive.html', tittle="Faculty Advisor Archive", form=form, student=student, notes=notes, course=course, electives=electives)


@app.route('/academic/archiveHome/<int:note_id>', methods=['GET', 'POST'])
@login_required
def AcademicArchive(note_id):
    if current_user.role == "Student":
        abort(403)
    
    notes = Notes.query.get_or_404(note_id)
    student_id = notes.Owner.EMPLID
    student = Student.query.filter_by(EMPLID=student_id).first()

    form = AcademicReviewForm()
    temp = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id).all()
    course = {i[0]:i[1] for i in temp}
    for i in Course.query.all():
        if i not in course:
            course[i] = None

    electives = dict()
    tech_elec = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id, Course.designation=="Technical Elective").all()
    CE = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id, (Course.designation=="[CE](1000)")|(Course.designation=="[CE](2000)")).all()
    US = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id, (Course.designation=="[US](1000)")|(Course.designation=="[US](2000)")).all()
    IS = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id==Course.id)\
        .filter(Enrollement.student_id==student_id, (Course.designation == "[IS](1000)")|(Course.designation == "[IS](2000)")).all()
    WCGI = db.session.query(Course, Enrollement).outerjoin(Enrollement, Enrollement.course_id == Course.id) \
        .filter(Enrollement.student_id == student_id,
                (Course.designation == "[WCGI](1000)")|(Course.designation == "[WCGI](2000)")).all()
    electives["Technical Elective"] = tech_elec
    electives["CE"] = CE
    electives["US"] = US
    electives["IS"] = IS
    electives["WCGI"] = WCGI


    if student.credit_earned >= 45:
        return render_template('AcademicArchive.html', tittle="Faculty Advisor Archive", form=form, student=student, notes=notes, course=course, electives=electives)
    else:
        form = form = FacultyReviewForm()
        return render_template('AcademicArchive2.html', tittle="Faculty Advisor Archive", form=form, student=student,
                               notes=notes, course=course, electives=electives)



@app.route('/Advisement/update/<int:note_id>', methods=['GET', 'POST'])
@login_required
def Update_Advisement(note_id):
    notes = Notes.query.get_or_404(note_id)
    form = UpdateAdvisementForm()
    GPA_QPA()
    student = Student.query.filter_by(EMPLID=current_user.EMPLID).first()
    transcript = url_for('static', filename='Transcript/' + student.transcript)

    enrolled = {i.course_id: i.grade for i in current_user.studentOwner.courses}
    course_obj = {i[0]: i[1] for i in form.course.iter_choices()}  # checkbox_field_id: course_object

    electives = []
    tech_elec = Course.query.join(Enrollement, Enrollement.course_id == Course.id).add_columns(Enrollement.grade) \
        .filter(Enrollement.student_id == current_user.studentOwner.EMPLID,
                Course.designation == "Technical Elective").all()
    if len(tech_elec) >= 2:
        electives.extend(tech_elec[0:2])
    elif len(tech_elec) == 1:
        electives.extend(tech_elec)  # 0
        electives.append(None)  # 1
    else:
        electives.append(None)  # 0
        electives.append(None)  # 1

    ce = Course.query.join(Enrollement, Enrollement.course_id == Course.id).add_columns(Enrollement.grade) \
        .filter((Course.designation == "[CE](1000)") | (Course.designation == "[CE](2000)"),
                Enrollement.student_id == current_user.studentOwner.EMPLID).first()
    use = Course.query.join(Enrollement, Enrollement.course_id == Course.id).add_columns(Enrollement.grade) \
        .filter((Course.designation == "[US](1000)") | (Course.designation == "[US](2000)"),
                Enrollement.student_id == current_user.studentOwner.EMPLID).first()
    is_ = Course.query.join(Enrollement, Enrollement.course_id == Course.id).add_columns(Enrollement.grade) \
        .filter((Course.designation == "[IS](1000)") | (Course.designation == "[IS](2000)"),
                Enrollement.student_id == current_user.studentOwner.EMPLID).first()
    wcgi = Course.query.join(Enrollement, Enrollement.course_id == Course.id).add_columns(Enrollement.grade) \
        .filter((Course.designation == "[WCGI](1000)") | (Course.designation == "[WCGI](2000)"),
                Enrollement.student_id == current_user.studentOwner.EMPLID).first()
    electives.append(ce)  # 2
    electives.append(use)  # 3
    electives.append(is_)  # 4
    electives.append(wcgi)  # 5


    if form.validate_on_submit():
        for course in form.course.data:
            enrollement = Enrollement.query.filter_by(
                student_id=current_user.EMPLID,
                course_id=course.id).first()
            if not enrollement:
                enrollement = Enrollement(student_id=current_user.EMPLID,
                                          course_id=course.id,
                                          attempt=True)
                db.session.add(enrollement)
            else:
                enrollement.grade = ''
                enrollement.attempt = True

        if form.tech_elec_check1.data == True:
            for course in form.tech_elec1.data:
                enrollement = Enrollement.query.filter_by(
                    student_id=current_user.EMPLID,
                    course_id=course.id).first()
                if not enrollement:
                    enrollement = Enrollement(student_id=current_user.EMPLID,
                                              course_id=course.id,
                                              attempt=True)
                    db.session.add(enrollement)
                else:
                    enrollement.grade = ''
                    enrollement.attempt = True
        if form.tech_elec_check2.data == True:
            for course in form.tech_elec2.data:
                enrollement = Enrollement.query.filter_by(
                    student_id=current_user.EMPLID,
                    course_id=course.id).first()
                if not enrollement:
                    enrollement = Enrollement(student_id=current_user.EMPLID,
                                              course_id=course.id,
                                              attempt=True)
                    db.session.add(enrollement)
                else:
                    enrollement.grade = ''
                    enrollement.attempt = True
        if form.CE_check.data == True:
            for course in form.CE.data:
                enrollement = Enrollement.query.filter_by(
                    student_id=current_user.EMPLID,
                    course_id=course.id).first()
                if not enrollement:
                    enrollement = Enrollement(student_id=current_user.EMPLID,
                                              course_id=course.id,
                                              attempt=True)
                    db.session.add(enrollement)
                else:
                    enrollement.grade = ''
                    enrollement.attempt = True

        if form.USE_check.data == True:
            for course in form.USE.data:
                enrollement = Enrollement.query.filter_by(
                    student_id=current_user.EMPLID,
                    course_id=course.id).first()
                if not enrollement:
                    enrollement = Enrollement(student_id=current_user.EMPLID,
                                              course_id=course.id,
                                              attempt=True)
                    db.session.add(enrollement)
                else:
                    enrollement.grade = ''
                    enrollement.attempt = True

        if form.IS_check.data == True:
            for course in form.IS.data:
                enrollement = Enrollement.query.filter_by(
                    student_id=current_user.EMPLID,
                    course_id=course.id).first()
                if not enrollement:
                    enrollement = Enrollement(student_id=current_user.EMPLID,
                                              course_id=course.id,
                                              attempt=True)
                    db.session.add(enrollement)
                else:
                    enrollement.grade = ''
                    enrollement.attempt = True
        if form.WCGI_check.data == True:
            for course in form.WCGI.data:
                enrollement = Enrollement.query.filter_by(
                    student_id=current_user.EMPLID,
                    course_id=course.id).first()
                if not enrollement:
                    enrollement = Enrollement(student_id=current_user.EMPLID,
                                              course_id=course.id,
                                              attempt=True)
                    db.session.add(enrollement)
                else:
                    enrollement.grade = ''
                    enrollement.attempt = True


        notes.be_advised = None
        notes.approval = None

        db.session.commit()
        return redirect(url_for('workflow'))

    return render_template('UpdateAdvisementForm.html', title="Revise Advisement Form", form=form,
                           enrolled=enrolled, course_obj=course_obj, transcript=transcript, electives=electives, notes=notes)

