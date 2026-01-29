from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from database import Database

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')
db = Database()

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')

@app.route('/')
def index():
    return render_template('index.html', logged_in='user_id' in session)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['user_id'] = 1
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login_signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/fighters')
def fighters():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    search_term = request.args.get('search', '')
    
    if search_term:
        fighters_list = db.search_fighters(search_term, limit=per_page)
        total_fighters = len(fighters_list) if fighters_list else 0
    else:
        fighters_list = db.get_all_fighters(limit=per_page)
        total_fighters = len(fighters_list) if fighters_list else 0
    
    total_pages = (total_fighters + per_page - 1) // per_page
    
    gyms = db.get_all_gyms()
    
    return render_template('fighters.html', 
                         fighters=fighters_list, 
                         gyms=gyms,
                         page=page, 
                         total_pages=total_pages,
                         search_term=search_term)

@app.route('/gyms')
def gyms():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    search_term = request.args.get('search', '')
    
    if search_term:
        gyms_list = db.search_gyms(search_term, limit=per_page)
        total_gyms = len(gyms_list) if gyms_list else 0
    else:
        gyms_list = db.get_all_gyms(limit=per_page)
        total_gyms = len(gyms_list) if gyms_list else 0
    
    total_pages = (total_gyms + per_page - 1) // per_page
    
    return render_template('gyms.html', 
                         gyms=gyms_list,
                         page=page, 
                         total_pages=total_pages,
                         search_term=search_term)

@app.route('/trainers')
def trainers():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    search_term = request.args.get('search', '')
    
    if search_term:
        trainers_list = db.search_trainers(search_term, limit=per_page)
        total_trainers = len(trainers_list) if trainers_list else 0
    else:
        trainers_list = db.get_all_trainers(limit=per_page)
        total_trainers = len(trainers_list) if trainers_list else 0
    
    total_pages = (total_trainers + per_page - 1) // per_page
    
    gyms = db.get_all_gyms()
    
    return render_template('trainers.html', 
                         trainers=trainers_list,
                         gyms=gyms,
                         page=page, 
                         total_pages=total_pages,
                         search_term=search_term)

@app.route('/matches')
def matches():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    search_term = request.args.get('search', '')
    
    if search_term:
        matches_list = db.search_matches(search_term, limit=per_page)
        total_matches = len(matches_list) if matches_list else 0
    else:
        matches_list = db.get_all_matches(limit=per_page)
        total_matches = len(matches_list) if matches_list else 0
    
    total_pages = (total_matches + per_page - 1) // per_page
    
    fighters = db.get_all_fighters()
    
    return render_template('matches.html', 
                         matches=matches_list,
                         fighters=fighters,
                         page=page, 
                         total_pages=total_pages,
                         search_term=search_term)

@app.route('/view/fighter/<int:fighter_id>')
def view_fighter(fighter_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    fighter = db.get_fighter_with_record(fighter_id)
    if not fighter:
        return jsonify({'error': 'Fighter not found'}), 404
    
    trainers = db.get_fighter_trainers(fighter_id)
    matches = db.get_fighter_matches(fighter_id)
    gym = db.get_gym('gym_id', fighter['gym_id']) if fighter['gym_id'] else None # type: ignore
    all_trainers = db.get_all_trainers()
    gyms = db.get_all_gyms()
    
    return render_template('view_fighter.html', 
                         fighter=fighter, 
                         trainers=trainers, 
                         matches=matches, 
                         gym=gym,
                         all_trainers=all_trainers,
                         gyms=gyms)

@app.route('/view/gym/<int:gym_id>')
def view_gym(gym_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    gym = db.get_gym('gym_id', gym_id)
    if not gym:
        return jsonify({'error': 'Gym not found'}), 404
    
    fighters = db.get_gym_fighters(gym_id)
    trainers = db.get_gym_trainers(gym_id)
    all_fighters = db.get_all_fighters_without_gym()
    all_trainers = db.get_all_trainers_without_gym()
    
    return render_template('view_gym.html', 
                         gym=gym, 
                         fighters=fighters, 
                         trainers=trainers,
                         all_fighters=all_fighters,
                         all_trainers=all_trainers)

@app.route('/view/trainer/<int:trainer_id>')
def view_trainer(trainer_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    trainer = db.get_trainer('trainer_id', trainer_id)
    if not trainer:
        return jsonify({'error': 'Trainer not found'}), 404
    
    fighters = db.get_trainer_fighters(trainer_id)
    gym = db.get_gym('gym_id', trainer['gym_id']) if trainer['gym_id'] else None # type: ignore
    all_fighters = db.get_all_fighters_without_trainer(trainer_id)
    gyms = db.get_all_gyms()
    
    return render_template('view_trainer.html', 
                         trainer=trainer, 
                         fighters=fighters, 
                         gym=gym,
                         all_fighters=all_fighters,
                         gyms=gyms)

@app.route('/view/match/<int:match_id>')
def view_match(match_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    match = db.get_match_fighters(match_id)
    if not match:
        return jsonify({'error': 'Match not found'}), 404
    
    match_details = db.execute("""
        SELECT * FROM match_events WHERE match_id = %s
    """, (match_id,), fetchone=True)
    
    fighters = db.get_all_fighters()
    
    return render_template('view_match.html', 
                         match=match, 
                         match_details=match_details,
                         fighters=fighters)

@app.route('/api/add/fighter', methods=['POST'])
def add_fighter():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        name = request.form.get('name')
        nickname = request.form.get('nickname', '')
        weight_class = request.form.get('weight_class')
        height = float(request.form.get('height')) # type: ignore
        age = int(request.form.get('age')) # type: ignore
        nationality = request.form.get('nationality', '')
        status = request.form.get('status', 'active')
        gym_id = request.form.get('gym_id')
        
        if gym_id:
            gym_id = int(gym_id)
        else:
            gym_id = None
        
        fighter_id = db.create_fighter(name, nickname, weight_class, height, age, nationality, status, gym_id)
        
        if fighter_id:
            return jsonify({'success': True, 'fighter_id': fighter_id})
        else:
            return jsonify({'error': 'Failed to create fighter'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/add/gym', methods=['POST'])
def add_gym():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        name = request.form.get('name')
        location = request.form.get('location')
        owner = request.form.get('owner')
        reputation_score = int(request.form.get('reputation_score', 75))
        
        gym_id = db.create_gym(name, location, owner, reputation_score)
        
        if gym_id:
            return jsonify({'success': True, 'gym_id': gym_id})
        else:
            return jsonify({'error': 'Failed to create gym'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/add/trainer', methods=['POST'])
def add_trainer():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        name = request.form.get('name')
        specialty = request.form.get('specialty')
        gym_id = request.form.get('gym_id')
        
        if gym_id:
            gym_id = int(gym_id)
        else:
            gym_id = None
        
        trainer_id = db.create_trainer(name, specialty, gym_id)
        
        if trainer_id:
            return jsonify({'success': True, 'trainer_id': trainer_id})
        else:
            return jsonify({'error': 'Failed to create trainer'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/add/match', methods=['POST'])
def add_match():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        location = request.form.get('location')
        fighter1_id = int(request.form.get('fighter1_id')) # type: ignore
        fighter2_id = int(request.form.get('fighter2_id')) # type: ignore
        winner_id = request.form.get('winner_id')
        
        if winner_id == 'draw':
            winner_id = 0
        elif winner_id == 'no_contest':
            winner_id = -1
        else:
            winner_id = int(winner_id) # type: ignore
        
        match_id = db.create_match(start_date, location, fighter1_id, fighter2_id, end_date, winner_id)
        
        if match_id:
            return jsonify({'success': True, 'match_id': match_id})
        else:
            return jsonify({'error': 'Failed to create match'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/update/fighter/<int:fighter_id>', methods=['POST'])
def update_fighter(fighter_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        field = request.form.get('field')
        value = request.form.get('value')
        
        if field in ['height', 'age']:
            value = float(value) if field == 'height' else int(value) # type: ignore
        elif field == 'gym_id':
            value = int(value) if value else None
        
        success = db.update_fighter(fighter_id, field, value)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to update fighter'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/update/gym/<int:gym_id>', methods=['POST'])
def update_gym(gym_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        field = request.form.get('field')
        value = request.form.get('value')
        
        if field == 'reputation_score':
            value = int(value) # type: ignore
        
        success = db.update_gym(gym_id, field, value)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to update gym'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/update/trainer/<int:trainer_id>', methods=['POST'])
def update_trainer(trainer_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        field = request.form.get('field')
        value = request.form.get('value')
        
        if field == 'gym_id':
            value = int(value) if value else None
        
        success = db.update_trainer(trainer_id, field, value)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to update trainer'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/update/match/<int:match_id>', methods=['POST'])
def update_match(match_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        field = request.form.get('field')
        value = request.form.get('value')
        
        if field == 'start_date' or field == 'end_date':
            if value:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            else:
                value = None
        
        success = db.update_match(match_id, field, value)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to update match'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/delete/fighter/<int:fighter_id>', methods=['POST'])
def delete_fighter(fighter_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        success = db.delete_fighter(fighter_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to delete fighter'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/delete/gym/<int:gym_id>', methods=['POST'])
def delete_gym(gym_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        success = db.delete_gym(gym_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to delete gym'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/delete/trainer/<int:trainer_id>', methods=['POST'])
def delete_trainer(trainer_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        success = db.delete_trainer(trainer_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to delete trainer'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/delete/match/<int:match_id>', methods=['POST'])
def delete_match(match_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        success = db.delete_match(match_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to delete match'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/fighter/add_trainer', methods=['POST'])
def add_fighter_trainer():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        fighter_id = int(request.form.get('fighter_id')) # type: ignore
        trainer_id = int(request.form.get('trainer_id')) # type: ignore
        
        success = db.add_fighter_trainer(fighter_id, trainer_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to add trainer to fighter'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/fighter/remove_trainer', methods=['POST'])
def remove_fighter_trainer():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        fighter_id = int(request.form.get('fighter_id')) # type: ignore
        trainer_id = int(request.form.get('trainer_id')) # type: ignore
        
        success = db.remove_fighter_trainer(fighter_id, trainer_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to remove trainer from fighter'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/gym/add_fighter', methods=['POST'])
def add_fighter_to_gym():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        gym_id = int(request.form.get('gym_id')) # type: ignore
        fighter_id = int(request.form.get('fighter_id')) # type: ignore
        
        success = db.update_fighter(fighter_id, 'gym_id', gym_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to add fighter to gym'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/gym/add_trainer', methods=['POST'])
def add_trainer_to_gym():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        gym_id = int(request.form.get('gym_id')) # type: ignore
        trainer_id = int(request.form.get('trainer_id')) # type: ignore
        
        success = db.update_trainer(trainer_id, 'gym_id', gym_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to add trainer to gym'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/gym/remove_fighter', methods=['POST'])
def remove_fighter_from_gym():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        fighter_id = int(request.form.get('fighter_id')) # type: ignore
        
        success = db.update_fighter(fighter_id, 'gym_id', None)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to remove fighter from gym'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/gym/remove_trainer', methods=['POST'])
def remove_trainer_from_gym():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        trainer_id = int(request.form.get('trainer_id')) # type: ignore
        
        success = db.update_trainer(trainer_id, 'gym_id', None)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to remove trainer from gym'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/trainer/add_fighter', methods=['POST'])
def add_fighter_to_trainer():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        trainer_id = int(request.form.get('trainer_id')) # type: ignore
        fighter_id = int(request.form.get('fighter_id')) # type: ignore
        
        success = db.add_fighter_trainer(fighter_id, trainer_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to add fighter to trainer'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/trainer/remove_fighter', methods=['POST'])
def remove_fighter_from_trainer():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        trainer_id = int(request.form.get('trainer_id')) # type: ignore
        fighter_id = int(request.form.get('fighter_id')) # type: ignore
        
        success = db.remove_fighter_trainer(fighter_id, trainer_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to remove fighter from trainer'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/match/update_fighter', methods=['POST'])
def update_match_fighter():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        match_id = int(request.form.get('match_id')) # type: ignore
        old_fighter_id = int(request.form.get('old_fighter_id')) # type: ignore
        new_fighter_id = int(request.form.get('new_fighter_id')) # type: ignore
        
        success = db.update_match_player(match_id, old_fighter_id, new_fighter_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to update match fighter'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/match/update_result', methods=['POST'])
def update_match_result():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        match_id = int(request.form.get('match_id')) # type: ignore
        winner_id = int(request.form.get('winner_id')) # type: ignore
        
        success = db.update_match_result(match_id, winner_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to update match result'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/init-db')
def init_db():
    db.init_db()
    return 'Database initialized successfully'

if __name__ == '__main__':
    app.run(debug=True)