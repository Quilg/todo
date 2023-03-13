from flask import Flask, render_template, request, redirect, url_for, session, g
import sqlite3

app = Flask(__name__)
app.secret_key = 'kahsfhkj3hk24hhk235asd324jasdjgjfdh'
app.config['SESSION_TYPE'] = 'filesystem'


def get_connection():
    conn = sqlite3.connect("todo.db")
    return conn

def create_tables():
    db = get_connection()  
    db.execute("""
        CREATE TABLE IF NOT EXISTS users
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT)
    """)
    
@app.route("/")
def home():
    return render_template('index.html')