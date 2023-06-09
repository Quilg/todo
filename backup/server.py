import datetime
from flask import Flask, flash, render_template, request, redirect, url_for, session, g, send_from_directory
import sqlite3

app = Flask(__name__)
app.secret_key = 'kahsfhkj3hk24hhk235asd324jasdjgjfdh'
app.config['SESSION_TYPE'] = 'filesystem'
MAX_TASKS_PER_PROJECT = 15
MAX_PROJECTS = 5

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

def get_project_count():
    db = get_connection()
    project_count = db.execute('SELECT COUNT(*) FROM porjects WHERE user_id = ?', (g.user[0],)).fetchone()[0]
    return project_count

def get_task_count(project_id):
    db = get_connection()
    task_count = db.execute('SELECT COUNT(*) FROM tasks WHERE project_id = ?', (project_id,)).fetchone()[0]
    return task_count

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
        role TEXT,
        status TEXT,
        task_count INTEGER DEFAULT 0)
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS projects
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        user_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (id))
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS tasks
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        project_id INTEGER,
        completed INTEGER,
        due_date DATE,
        user_id INTEGER,
        FOREIGN KEY (project_id) REFERENCES projects (id),
        FOREIGN KEY (user_id) REFERENCES users (id))
    """)
    db.commit()

create_tables()
    
@app.route("/")
def home():
    check_user()
    return render_template('index.html', user=g.user)

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
            flash('You were successfully logged in')
            return redirect(url_for('home'))

        flash(error)

    return render_template('login.html')

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        role = request.form['role']

        db = get_connection()

        error = None
        user = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()

        if not username:
            error = 'Username is required'
        elif not password:
            error = 'Password is required'
        elif user is not None:
            error = f"User {username} is already registered."
        else:
            db.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username, password, role))
            db.commit()
            flash('You were successfully registered')
            return redirect(url_for('login'))

        flash(error)

    return render_template('register.html')

@app.route('/create_project', methods=['POST'])
def create_project():
    check_user()

    if g.user is None:
        return redirect(url_for('login'))
    
    if g.user[3] == 'free':
        project_count = get_project_count()
        if project_count >= MAX_PROJECTS:
            flash("You have reached the maximum number of projects.")
            return redirect(url_for('todo'))

    name = request.form['project_name']
    db = get_connection()
    db.execute('INSERT INTO projects (name, user_id) VALUES (?, ?)', (name, g.user[0]))
    db.commit()
    
    return redirect(url_for('todo'))

@app.route('/delete_project/<int:project_id>')
def delete_project(project_id):
    check_user()
    if g.user is None:
        return redirect(url_for('login'))
    db = get_connection()
    db.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    db.execute('DELETE FROM tasks WHERE project_id = ?', (project_id,))
    db.commit()

    return redirect(url_for('todo'))

@app.route('/create_task', methods=['POST'])
def create_task():
    check_user()
    if g.user is None:
        return redirect(url_for('login'))
    project_id = int(request.form['project'])
    if g.user[3] == 'free':
        task_count = get_task_count(project_id)
        if task_count >= MAX_TASKS_PER_PROJECT:
            flash("You have reached the maximum number of tasks for this project.")
            return redirect(url_for('todo'))

    name = request.form['task_name']
    db = get_connection()
    db.execute('INSERT INTO tasks (name, project_id, completed, user_id) VALUES (?, ?, ?, ?)', (name, project_id, 0, g.user[0]))
    db.commit()

    return redirect(url_for('todo'))

@app.route('/complete_task/<int:task_id>')
def complete_task(task_id):
    check_user()
    if g.user is None:
        return redirect(url_for('login'))
    db = get_connection()
    db.execute('UPDATE tasks SET completed = 1 WHERE id = ?', (task_id,))
    db.commit()

    return redirect(url_for('todo'))

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    check_user()
    if g.user is None:
        return redirect(url_for('login'))
    db = get_connection()
    db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    db.commit()

    return redirect(url_for('todo'))

@app.route('/todo', methods=['POST', 'GET'])
def todo():
    check_user()

    if g.user is None:
        return redirect(url_for('login'))

    db = get_connection()

    if request.method == 'POST':
        # Create a new project
        if request.form.get('project_name'):
            project_name = request.form['project_name']
            project_count = db.execute('SELECT COUNT(*) FROM projects WHERE user_id = ?', (g.user[0],)).fetchone()[0]
            if project_count >= 5:
                return render_template('todo.html', error='You have reached the maximum number of projects for your account.')
            else:
                db.execute('INSERT INTO projects (name, user_id) VALUES (?, ?)', (project_name, g.user[0]))
                db.commit()
    elif request.method == 'GET':

        # Create a new task
        if request.form.get('task_name'):
            task_name = request.form['task_name']
            project_id = request.form['project']
            incomplete_task_count = db.execute('SELECT COUNT(*) FROM tasks WHERE project_id = ? AND completed = 0', (project_id,)).fetchone()[0]
            if incomplete_task_count >= 15:
                return render_template('todo.html', error='You have reached the maximum number of incomplete tasks for this project.')
            else:
                db.execute('INSERT INTO tasks (name, project_id, date) VALUES (?, ?, ?)', (task_name, project_id, request.form['date']))
                db.commit()

    # Get all projects and tasks for the current user
    projects = db.execute('SELECT * FROM projects WHERE user_id = ?', (g.user[0],)).fetchall()
    tasks = db.execute('SELECT * FROM tasks WHERE project_id IN (SELECT id FROM projects WHERE user_id = ?) AND completed = 0', (g.user[0],)).fetchall()

    return render_template('todo.html', user=g.user, projects=projects, tasks=tasks)