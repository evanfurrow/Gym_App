import requests

def get_exercises_list():
    """Returns a static list of common gym exercises/machines."""
    exercises = [
        {"id": 1, "name": "Barbell Bench Press", "equipment": "Barbell"},
        {"id": 2, "name": "Squat Rack Squat", "equipment": "Squat Rack"},
        {"id": 3, "name": "Leg Press Machine", "equipment": "Leg Press Machine"},
        {"id": 4, "name": "Dumbbell Curl", "equipment": "Dumbbell"},
        {"id": 5, "name": "Lat Pulldown Machine", "equipment": "Lat Pulldown Machine"},
        {"id": 6, "name": "Deadlift", "equipment": "Barbell"},
        # --- Add new exercises below here ---
        {"id": 7, "name": "Overhead Press (OHP)", "equipment": "Barbell"},
        {"id": 8, "name": "Cable Tricep Pushdown", "equipment": "Cable Machine"},
        {"id": 9, "name": "Leg Extension Machine", "equipment": "Leg Extension Machine"},
        {"id": 10, "name": "T-Bar Row", "equipment": "T-Bar Row Machine"},
    ]
    return exercises


# The function you were trying to import now just calls the local list
def get_exercises_by_equipment(equipment_name):
    """Filters exercises by specific equipment name (simple local filtering)."""
    all_exercises = get_exercises_list()
    if equipment_name == "all":
        return all_exercises
    return [e for e in all_exercises if e['equipment'].lower() == equipment_name.lower()]