import gc
import keyring
import MySQLdb
import wtforms
from contextlib import closing
from flask import Flask, request, session, g, redirect, url_for, \
	abort, render_template, flash
from flaskext.mysql import MySQL
from flask_wtf import Form
from functools import wraps
from MySQLdb import escape_string as thwart
from MySQLdb.cursors import DictCursor
from passlib.hash import sha256_crypt
from wtforms import Form, BooleanField, PasswordField, StringField, validators

#create app
app = Flask(__name__)
app.config['SECRET_KEY'] = keyring.get_password("budget_calculator", "SECRET_KEY")

db_conf = {'name':'budget_calculator','user':'root',
		   'pw':keyring.get_password("mysql_budget_calculator","root"), 'host':'localhost'}
#
#
#   Database functions
#
#
'''
Executes {statement} to the database specified in db_conf
Returns number of rows affected unless fetchall=True in which
this will return the remaining rows of the query result set
'''
def db_execute(statement, fetchall=False):
    data = []
    try:
        with closing(MySQLdb.connect(db_conf['host'], db_conf['user'], db_conf['pw'],
            db_conf['name'])) as conn:
            with closing(conn.cursor(MySQLdb.cursors.DictCursor)) as cur:
                print(statement)
                if fetchall:
                    cur.execute(statement)
                    data = cur.fetchall()[0]
                else:
                    data = cur.execute(statement)
                print(data)
    except Exception as e:
        print( "Error: %s" % e)
    return data

'''
   conn = mysql.connect()           # connect to the database
   cursor = conn.cursor             # used to query a stored procedure
   cursor.execute(op, param=None, )
   rows = cursor.fetchall()         # grabs all (or remaining) rows of a query result set
   rows = cursor.fetchmany(size=x)  # grabs the next x rows of a query result set
   cursor.close()                   # close when done with the cursor
'''
#
#
#   Template navigation
#
#
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("You need to be logged in to do that!")
            return redirect(url_for('login'))
    return wrap
    

@app.route('/homepage')
def homepage():
    '''
        TODO: Make pretty homepage
    '''
    return render_template('main.html')

@app.route('/test')
def test():
    return render_template('month design.html')    
    
#display user's profile information
@app.route('/myprofile')
@login_required
def myprofile():
    return render_template('profile.html')
	
#display budget for a single month
@app.route('/monthview')
@login_required
def monthview():
    return render_template('month.html')
	
#display overview for a year
@app.route('/yearview')
@login_required
def yearview():
    return render_template('year.html')


#display login form
@app.route('/login', methods = ["GET", "POST"])
def login():
    error = ''
    try:
        if request.method == "POST":
            data = db_execute("SELECT * FROM users WHERE username = \"{}\"".format(
                thwart(request.form['username'])), fetchall=True)
            print("Hello {}".format(data))
            if data:
                #data = c.fetchone()
                if sha256_crypt.verify(request.form['password'], data['password']):
                    session['logged_in'] = True
                    session['username'] = request.form['username']
                    flash("You're now logged in")
                    return redirect(url_for('homepage'))
                else:
                    error = "Invalid Credentials. Try Again"
            else: #username not found in database
                error = "Invalid Credentials. Try Again"
        gc.collect
        return render_template("login.html", error=error)
        
    except Exception as e:
        flash(e) #used for debugging
        return render_template('login.html', error=e)

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash("You have been logged out")
    gc.collect()
    return redirect(url_for('homepage'))

class RegistrationForm(Form):
    username = StringField('Username', validators = [validators.Length(min=4, max=20)])
    email = StringField('Email Address', validators = [validators.Email()])
    password = PasswordField('Password', validators = [validators.InputRequired(), 
        validators.EqualTo('confirm', message="Passwords must match")])
    confirm = PasswordField('Repeat Password') 
    accept_tos = BooleanField('''I accept the <a href="/tos/">Terms of Service</a>
     and the <a href="/privacy/">Privacy Notice</a>.''', validators = [validators.InputRequired()])


#display registration
@app.route('/register', methods = ["GET", "POST"])
def register():
    try:
        form = RegistrationForm(request.form)
        if request.method == "POST" and form.validate():
            username = form.username.data
            email = form.email.data
            password = sha256_crypt.encrypt(str(form.password.data))

            data = db_execute("SELECT * FROM users WHERE username = \"{}\"".format(
                (thwart(username))))
            if int(data) > 0:
                flash("That username is already taken")
                return render_template("register.html", form=form)
            else:
                flash("Username not taken") 
                db_execute("INSERT INTO users (username, password, email) VALUES({}, {}, {})".format( 
                    thwart(username), thwart(password), thwart(email)))
                flash("Thank you for registering")
                session['logged_in'] = True
                session['username'] = username

                return redirect(url_for('homepage'))
    except Exception as e:
        flash(str(e))

    return render_template('register.html', form=form)

#
#
#   Error handling
#
#
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html')

@app.errorhandler(500)
def internal_server_error(e):
    try:
        return render_template('500.html', error = e)
    except Exception as e:
        return ("Something went really wrong here: " + e)

#
#
#   Main
#
#
if __name__ == '__main__':
    app.run(host='0.0.0.0')