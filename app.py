import sqlite3
import os
from datetime import datetime # Import the date class
from flask import Flask, render_template, request, g, session, redirect, url_for
from api_utils import get_exercises_list 

# 2. App Initialization & Configuration
app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here'
basedir = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(basedir, 'gym.db')

# 3. Helper Functions (moved up here)
def get_db():
    """Opens a new database connection..."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.route('/add_exercise', methods=['GET', 'POST'])
def add_exercise():
    if 'user_name' not in session:
        return redirect(url_for('user_details'))

    user_name = session['user_name']
    error_message = None
    success_message = None

    if request.method == 'POST':
        exercise_name = request.form.get('exercise_name')
        equipment = request.form.get('equipment')

        if exercise_name:
            db = get_db()
            cursor = db.cursor()
            try:
                cursor.execute("INSERT INTO custom_exercises (user_name, exercise_name, equipment) VALUES (?, ?, ?)",
                               (user_name, exercise_name, equipment))
                db.commit()
                success_message = f"'{exercise_name}' added successfully!"
            except sqlite3.IntegrityError:
                error_message = f"'{exercise_name}' is already in your list."
        else:
            error_message = "Please enter an exercise name."

    # Fetch existing custom exercises for display on the page
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM custom_exercises WHERE user_name = ? ORDER BY exercise_name", (user_name,))
    user_exercises = cursor.fetchall()

    return render_template('add_exercise.html', 
                           user_exercises=user_exercises, 
                           error=error_message, 
                           success=success_message)

@app.template_filter('formatdate')
def format_date_filter(iso_date_or_datetime_string):
    """Converts an ISO date string (YYYY-MM-DD) to Day Month, Year format."""
    try:
        date_obj = datetime.fromisoformat(iso_date_or_datetime_string).date()
        return date_obj.strftime('%B %d, %Y') # Format: 20 November, 2025
    except ValueError:
        date_obj = datetime.strptime(iso_date_or_datetime_string, '%Y-%m-%d').date()
        return date_obj.strftime('%B %d, %Y')
    except ValueError:
        # Return original string if parsing still fails
        return iso_date_or_datetime_string 
@app.teardown_appcontext
def close_connection(exception):
    """Closes the database connection..."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Creates the database tables if they don't exist."""
    print("DEBUG: init_db() function is running...") 
    with app.app_context():
        db = get_db() 
        cursor = db.cursor()
        
        # New table to track user sessions/workouts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workouts (
                workout_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                workout_date TEXT NOT NULL
            )
        ''')

        # Updated lifts table: note the added workout_id foreign key
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_id INTEGER NOT NULL,
                exercise TEXT NOT NULL,
                weight REAL NOT NULL,
                reps INTEGER NOT NULL,
                FOREIGN KEY (workout_id) REFERENCES workouts(workout_id)
            )
        ''')

        # New table to store custom exercises added by users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_exercises (
                exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                exercise_name TEXT NOT NULL,
                equipment TEXT,
                UNIQUE(user_name, exercise_name) -- Prevents duplicate entries
            )
        ''')
        
        db.commit()
# 4. Route Handlers (using the helper functions)
@app.route('/', methods=['GET', 'POST'])
def user_details():
    """First step: Prompts user for name and date."""
    if request.method == 'POST':
        user_name = request.form.get('user_name')
        workout_date = datetime.today().isoformat()

        if user_name and workout_date:
            # Store the name and date in the session
            session['user_name'] = user_name
            session['workout_date'] = workout_date
            
            # Redirect to the second step (log lifts page)
            return redirect(url_for('log_lifts'))
        else:
            # If data is missing in a POST request, return the template again
            # Optionally pass an error message to the template here
            return render_template('user_details.html', error="Please fill out both fields.")

    # This line handles the initial GET request when visiting the URL
    session.clear() 
    return render_template('user_details.html')

@app.route('/log_lifts', methods=['GET', 'POST'])
def log_lifts():
    """Second step: Prompts for exercises, weights, and reps."""
    # Ensure user_name and workout_date are in the session (basic check)
    if 'user_name' not in session or 'workout_date' not in session:
        return redirect(url_for('user_details')) # Redirects if session expired

    # Retrieve info from session
    user_name = session['user_name']
    workout_date = session['workout_date']
    
    db = get_db()
    workout_id = None
    error_message = None # Variable to store potential errors

    if request.method == 'POST':
        # 1. Get or create the workout session ID
        cursor = db.cursor()
        # Note: The lookup here still uses both user and date to find the CORRECT workout session ID
        cursor.execute("SELECT workout_id FROM workouts WHERE user_name = ? AND workout_date = ?", 
                       (user_name, workout_date))
        workout_entry = cursor.fetchone()

        if workout_entry is None:
            cursor.execute("INSERT INTO workouts (user_name, workout_date) VALUES (?, ?)", 
                           (user_name, workout_date))
            db.commit()
            workout_id = cursor.lastrowid
        else:
            workout_id = workout_entry['workout_id']

        # 2. Try to log the lift
        exercise = request.form.get('exercise')
        weight = request.form.get('weight')
        reps = request.form.get('reps')

        if exercise and weight and reps and workout_id is not None:
            cursor.execute("INSERT INTO lifts (workout_id, exercise, weight, reps) VALUES (?, ?, ?, ?)",
                           (workout_id, exercise, weight, reps))
            db.commit()
            # The function continues down to the render_template below
        else:
            error_message = "Please fill out all lift details."
            # The function continues down to the render_template below

    # 3. Retrieve all previous 20 lifts for *this user only* to display
    cursor = db.cursor()
    cursor.execute("""
        SELECT w.workout_date, w.user_name, l.* FROM lifts l
        JOIN workouts w ON l.workout_id = w.workout_id
        WHERE w.user_name = ? -- MODIFICATION: Removed 'AND w.workout_date = ?' filter
        ORDER BY l.id DESC
        LIMIT 20 
    """, (user_name,)) # MODIFICATION: Only pass 'user_name' to the query tuple
    
    current_lifts = cursor.fetchall()
    
    # ... (code continues to fetch exercises and return the render_template) ...
    # Make sure the rest of the function is present below this block

    # Fetch exercises list for the dropdown
    exercises_list = get_exercises_list()
    
    # 4. ALWAYS RETURN A RESPONSE AT THE END OF THE FUNCTION
    return render_template('log_lifts.html', 
                           lifts=current_lifts, 
                           exercises=exercises_list,
                           user_name=user_name,
                           workout_date=workout_date,
                           error=error_message) # Pass the error message
# 5. Main execution block
if __name__ == '__main__':
    print("DEBUG: Executing __main__ block, calling init_db()") # ADD THIS LINE
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)

