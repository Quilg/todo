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
                db.execute('INSERT INTO users(username, password, role, status) VALUES (?, ?, ?, ?)', (username, password, 'free', 'active')) 
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
    if g.user[3] == 'admin':
        db = get_connection()
        users = db.execute('SELECT * FROM users WHERE role != "admin"').fetchall()
        return render_template('dashboard.html', users=users)
    return redirect(url_for('profile'))

@app.route('/dashboard/upgrade/<int:user_id>', methods=['POST'])
def upgrade_user(user_id):

    db = get_connection()
    db.execute('UPDATE users SET role = "premium" WHERE id = ?', (user_id,))
    db.commit()

    return redirect(url_for('dashboard'))


@app.route('/dashboard/terminate/<int:user_id>', methods=['POST'])
def terminate_user(user_id):

    db = get_connection()
    db.execute('UPDATE users SET status = "terminated" WHERE id = ?', (user_id,))
    db.commit()

    return redirect(url_for('dashboard'))

@app.route('/dashboard/downgrade/<int:user_id>', methods=['POST'])
def downgrade_user(user_id):
    
    db = get_connection()
    db.execute('UPDATE users SET role = "free" WHERE id = ?', (user_id,))
    db.commit()

    return redirect(url_for('dashboard'))

@app.route('/dashboard/activate/<int:user_id>', methods=['POST'])
def activate_user(user_id):

    db = get_connection()
    db.execute('UPDATE users SET status = "active" WHERE id = ?', (user_id,))
    db.commit()

    return redirect(url_for('dashboard'))

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

        # Filter tasks by date
        if request.form.get('date'):
            date = request.form['date']
            status = request.form['status']
            if status == 'today':
                tasks = db.execute('SELECT * FROM tasks WHERE project_id IN (SELECT id FROM projects WHERE user_id = ?) AND date = ? AND completed = 0', (g.user[0], date)).fetchall()
            elif status == 'past':
                tasks = db.execute('SELECT * FROM tasks WHERE project_id IN (SELECT id FROM projects WHERE user_id = ?) AND date < ? AND completed = 0', (g.user[0], date)).fetchall()
            else: tasks = db.execute('SELECT * FROM tasks WHERE project_id IN (SELECT id FROM projects WHERE user_id = ?) AND date > ? AND completed = 0', (g.user[0], date)).fetchall()

    # Get all projects and tasks for the current user
    projects = db.execute('SELECT * FROM projects WHERE user_id = ?', (g.user[0],)).fetchall()
    tasks = db.execute('SELECT * FROM tasks WHERE project_id IN (SELECT id FROM projects WHERE user_id = ?) AND completed = 0', (g.user[0],)).fetchall()

    return render_template('todo.html', user=g.user, projects=projects, tasks=tasks)

@app.route('/create_project', methods=['POST'])
def create_project():
    check_user()

    db = get_connection()

    # Get the project name from the form
    project_name = request.form['project_name']

    # Insert the new project into the database
    db.execute('INSERT INTO projects (name, user_id) VALUES (?, ?)', (project_name, g.user[0]))
    db.commit()

    # Redirect the user back to the todo page
    return redirect(url_for('todo'))

@app.route('/create_task', methods=['POST'])
def create_task():
    check_user()
    db = get_connection()
    task_name = request.form['task_name']
    project_id = request.form['project']
    user_id = g.user[0]
    
    # Check if project has reached the maximum number of tasks
    tasks = db.execute('SELECT * FROM tasks WHERE project_id = ? AND user_id = ?', (project_id, user_id)).fetchall()
    if len(tasks) >= MAX_TASKS_PER_PROJECT:
        projects = db.execute('SELECT * FROM projects WHERE user_id = ?', (user_id,)).fetchall()
        tasks = db.execute('SELECT t.id, t.name, t.project_id, t.completed FROM tasks t JOIN projects p ON t.project_id = p.id WHERE t.user_id = ? AND p.user_id = ?', (user_id, user_id)).fetchall()
        return render_template('todo.html', error='You have reached the maximum number of incomplete tasks for this project.', user=g.user, projects=projects, tasks=tasks)

    db.execute('INSERT INTO tasks (name, project_id, user_id) VALUES (?, ?, ?)', (task_name, project_id, user_id))
    db.commit()
    
    return redirect(url_for('todo'))



@app.route('/delete_task/<int:task_id>', methods=['GET'])
def delete_task():
    check_user()

    if g.user is None:
        return redirect(url_for('login'))

    db = get_connection()
    
    # Get the task_id from the form
    task_id = request.form.get('task_id')

    # Delete the task
    db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    
    # Commit changes to the database
    db.commit()

    return redirect(url_for('todo'))



@app.route('/delete_project/<int:project_id>', methods=['GET'])
def delete_project(project_id):
    check_user()
    db = get_connection()
    db.execute('DELETE FROM projects WHERE id = ? AND user_id = ?', (project_id, g.user[0]))
    db.execute('DELETE FROM tasks WHERE project_id = ? AND user_id = ?', (project_id, g.user[0]))
    db.commit()
    flash('Project deleted successfully!', 'success')
    return redirect(url_for('todo'))

@app.route('/upgrade', methods=['GET'])
def upgrade():
    db = get_connection()
    check_user()
    user_id = g.user[0]
    db.execute('UPDATE users SET role = "premium" WHERE id = ?', (user_id,))
    db.commit()
    flash('Your account has been upgraded to premium!', 'success')
    return redirect(url_for('profile'))





