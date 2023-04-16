from flask import Flask, render_template, request, redirect, url_for, session, g, send_from_directory
import sqlite3

app = Flask(__name__)
app.secret_key = 'kahsfhkj3hk24hhk235asd324jasdjgjfdh'
app.config['SESSION_TYPE'] = 'filesystem'


def get_connection():
    conn = sqlite3.connect("todo.db")
    return conn

def check_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        db = get_connection()
        g.user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

def create_tables():
    db = get_connection()  
    db.execute("""
        CREATE TABLE IF NOT EXISTS users
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT)
    """)
create_tables()
    
@app.route("/")
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        db = get_connection()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        error = None

        if user is None:
            error = "User does not exist"
        elif password != user[2]:
            error = "Wrong credentials!"
        else:
            session.clear()
            session['user_id'] = user[0]
            if user[3] == 'admin':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('profile'))
        print(error)

    return render_template('auth/login.html')


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        error = None

        if password != confirm_password:
            error = "Passwords do not match" 
        else:
            db = get_connection()
            user = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()

            if user is not None:
                error = "Username already exists"
            else:
                db.execute('INSERT INTO users(username, password, role) VALUES (?, ?, ?)', (username, password, 'free')) 
                db.commit()
                return redirect(url_for('login'))
        
        print(error)

    return render_template('auth/register.html')

@app.route('/profile')
def profile():
    check_user()
    if g.user is None:
        return redirect(url_for('login'))
    return render_template('profile.html')

@app.route('/dashboard')
def dashboard():
    check_user()
    if g.user is None or g.user[3] != 'admin':
        return redirect(url_for('login'))
    return render_template('dashboard.html')

