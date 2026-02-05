from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from database import Database
import traceback

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')
db = Database()

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')

def require_login(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def convert_to_dict(obj):
    """Convert RealDictRow or any database result to a JSON-serializable dictionary"""
    if obj is None:
        return None
    
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            result[key] = convert_value(value)
        return result
    elif hasattr(obj, '_asdict'):  # For RealDictRow or namedtuple-like objects
        result = {}
        for key, value in obj._asdict().items():
            result[key] = convert_value(value)
        return result
    elif isinstance(obj, list):
        return [convert_to_dict(item) for item in obj]
    else:
        return obj

def convert_value(value):
    """Convert individual values to JSON-serializable types"""
    if value is None:
        return None
    elif isinstance(value, datetime):  # This checks if it's a datetime object
        return value.isoformat()
    elif isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    elif hasattr(value, 'to_integral_value'):  # For Decimal
        return int(value.to_integral_value())
    elif isinstance(value, (int, float, str, bool)):
        return value
    elif isinstance(value, (list, tuple)):
        return [convert_value(item) for item in value]
    elif isinstance(value, dict):
        return convert_to_dict(value)
    else:
        return str(value)

@app.route('/')
def index():
    return render_template('index.html', logged_in='user_id' in session)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check against admin credentials from .env
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['user_id'] = 1
            session['username'] = username
            flash('Login successful! Welcome to the Fight Club Management System.', 'success')
            
            # Return JSON for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'redirect': url_for('dashboard')})
            
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
            
            # Return JSON for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    
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
        flash('Please login to access fighter management', 'warning')
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '')
    
    # Get fighters
    if search_term:
        fighters_list = db.search_fighters(search_term, limit=100)
    else:
        fighters_list = db.get_all_fighters(limit=100)
    
    # Get gyms for the create form
    gyms = db.get_all_gyms()
    
    return render_template('fighters.html', 
                         fighters=fighters_list,
                         gyms=gyms,
                         page=page,
                         search_term=search_term)

@app.route('/api/fighters', methods=['GET'])
def get_fighters():
    """Get all fighters with gym info"""
    try:
        search_term = request.args.get('search', '')
        
        if search_term:
            fighters = db.search_fighters(search_term, limit=100)
        else:
            fighters = db.get_all_fighters(limit=100)
        
        if not fighters:
            return jsonify([])
        
        # Enhance fighter data with gym info and records
        enhanced_fighters = []
        for fighter in fighters:
            fighter_dict = dict(fighter)
            
            # Get fighter record
            record = db.get_fighter_with_record(fighter_dict['fighter_id'])
            if record:
                fighter_dict['wins'] = record.get('wins', 0)
                fighter_dict['losses'] = record.get('losses', 0)
                fighter_dict['draws'] = record.get('draws', 0)
            
            # Get gym name if available
            if fighter_dict.get('gym_id'):
                gym = db.get_gym('gym_id', fighter_dict['gym_id'])
                if gym:
                    fighter_dict['gym_name'] = gym['name']
            
            enhanced_fighters.append(fighter_dict)
        
        return jsonify(enhanced_fighters)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fighters/<int:fighter_id>', methods=['GET'])
def get_fighter(fighter_id):
    """Get detailed fighter information"""
    try:
        fighter = db.get_fighter_with_record(fighter_id)
        if not fighter:
            return jsonify({'error': 'Fighter not found'}), 404
        
        fighter_dict = dict(fighter)
        
        # Add gym details
        if fighter_dict.get('gym_id'):
            gym = db.get_gym('gym_id', fighter_dict['gym_id'])
            if gym:
                fighter_dict['gym_name'] = gym['name']
                fighter_dict['gym_location'] = gym['location']
                fighter_dict['gym_owner'] = gym['owner']
                fighter_dict['gym_reputation'] = gym['reputation_score']
        
        # Add trainers (will be loaded separately by frontend)
        
        return jsonify(fighter_dict)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fighters', methods=['POST'])
@require_login
def create_fighter():
    """Create a new fighter"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'weight_class', 'height', 'age', 'status']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Convert empty string gym_id to None
        gym_id = data.get('gym_id')
        if gym_id == '' or gym_id is None:
            gym_id = None
        elif gym_id:
            try:
                gym_id = int(gym_id)
            except ValueError:
                return jsonify({'error': 'Invalid gym_id'}), 400
        
        # Create fighter
        fighter_id = db.create_fighter(
            name=data['name'],
            nickname=data.get('nickname'),
            weight_class=data['weight_class'],
            height=float(data['height']),
            age=int(data['age']),
            nationality=data.get('nationality'),
            status=data['status'],
            gym_id=gym_id
        )
        
        if fighter_id:
            return jsonify({'id': fighter_id, 'message': 'Fighter created successfully'})
        else:
            return jsonify({'error': 'Failed to create fighter'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fighters/<int:fighter_id>', methods=['PUT'])
@require_login
def update_fighter(fighter_id):
    """Update fighter information"""
    try:
        data = request.get_json()
        
        # Check if fighter exists
        fighter = db.get_fighter('fighter_id', fighter_id)
        if not fighter:
            return jsonify({'error': 'Fighter not found'}), 404
        
        # Update allowed fields
        allowed_fields = ['name', 'nickname', 'weight_class', 'height', 'age', 
                         'nationality', 'status', 'gym_id']
        
        updates = {}
        for field in allowed_fields:
            if field in data:
                if field == 'gym_id' and (data[field] == '' or data[field] is None):
                    updates[field] = None
                else:
                    updates[field] = data[field]
        
        # Apply updates
        for field, value in updates.items():
            if not db.update_fighter(fighter_id, field, value):
                return jsonify({'error': f'Failed to update {field}'}), 500
        
        return jsonify({'message': 'Fighter updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fighters/<int:fighter_id>', methods=['DELETE'])
@require_login
def delete_fighter(fighter_id):
    """Delete a fighter"""
    try:
        # Check if fighter exists
        fighter = db.get_fighter('fighter_id', fighter_id)
        if not fighter:
            return jsonify({'error': 'Fighter not found'}), 404
        
        # Delete fighter
        if db.delete_fighter(fighter_id):
            return jsonify({'message': 'Fighter deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete fighter'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fighters/<int:fighter_id>/gym', methods=['PUT'])
@require_login
def update_fighter_gym(fighter_id):
    """Update fighter's gym affiliation"""
    try:
        data = request.get_json()
        
        # Check if fighter exists
        fighter = db.get_fighter('fighter_id', fighter_id)
        if not fighter:
            return jsonify({'error': 'Fighter not found'}), 404
        
        gym_id = data.get('gym_id')
        
        # If gym_id is provided, check if gym exists
        if gym_id:
            gym = db.get_gym('gym_id', gym_id)
            if not gym:
                return jsonify({'error': 'Gym not found'}), 404
        
        # Update fighter's gym
        if db.update_fighter(fighter_id, 'gym_id', gym_id):
            return jsonify({'message': 'Gym updated successfully'})
        else:
            return jsonify({'error': 'Failed to update gym'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# Add these trainer API routes to app.py

@app.route('/api/trainers', methods=['POST'])
@require_login
def create_trainer():
    """Create a new trainer (JSON API)"""
    try:
        data = request.get_json()
        
        required_fields = ['name', 'specialty']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        trainer_id = db.create_trainer(
            name=data['name'],
            specialty=data['specialty'],
            gym_id=data.get('gym_id')
        )
        
        if trainer_id:
            return jsonify({'id': trainer_id, 'message': 'Trainer created successfully'})
        else:
            return jsonify({'error': 'Failed to create trainer'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trainers/<int:trainer_id>', methods=['GET'])
def get_trainer_details(trainer_id):
    """Get detailed trainer information"""
    try:
        trainer = db.get_trainer('trainer_id', trainer_id)
        if not trainer:
            return jsonify({'error': 'Trainer not found'}), 404
        
        trainer_dict = dict(trainer)
        
        # Add gym details
        if trainer_dict.get('gym_id'):
            gym = db.get_gym('gym_id', trainer_dict['gym_id'])
            if gym:
                trainer_dict['gym_name'] = gym['name']
                trainer_dict['gym_location'] = gym['location']
                trainer_dict['gym_owner'] = gym['owner']
                trainer_dict['gym_reputation'] = gym['reputation_score']
        
        # Get fighter count
        fighters = db.get_trainer_fighters(trainer_id)
        trainer_dict['fighter_count'] = len(fighters) if fighters else 0
        
        return jsonify(trainer_dict)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trainers/<int:trainer_id>', methods=['PUT'])
@require_login
def update_trainer_api(trainer_id):
    """Update trainer information"""
    try:
        data = request.get_json()
        
        # Check if trainer exists
        trainer = db.get_trainer('trainer_id', trainer_id)
        if not trainer:
            return jsonify({'error': 'Trainer not found'}), 404
        
        # Update allowed fields
        allowed_fields = ['name', 'specialty', 'gym_id']
        
        updates = {}
        for field in allowed_fields:
            if field in data:
                if field == 'gym_id' and (data[field] == '' or data[field] is None):
                    updates[field] = None
                else:
                    updates[field] = data[field]
        
        # Apply updates
        for field, value in updates.items():
            if not db.update_trainer(trainer_id, field, value):
                return jsonify({'error': f'Failed to update {field}'}), 500
        
        return jsonify({'message': 'Trainer updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trainers/<int:trainer_id>', methods=['DELETE'])
@require_login
def delete_trainer_api(trainer_id):
    """Delete a trainer"""
    try:
        # Check if trainer exists
        trainer = db.get_trainer('trainer_id', trainer_id)
        if not trainer:
            return jsonify({'error': 'Trainer not found'}), 404
        
        # Delete trainer
        if db.delete_trainer(trainer_id):
            return jsonify({'message': 'Trainer deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete trainer'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trainers/<int:trainer_id>/gym', methods=['PUT'])
@require_login
def update_trainer_gym(trainer_id):
    """Update trainer's gym affiliation"""
    try:
        data = request.get_json()
        
        # Check if trainer exists
        trainer = db.get_trainer('trainer_id', trainer_id)
        if not trainer:
            return jsonify({'error': 'Trainer not found'}), 404
        
        gym_id = data.get('gym_id')
        
        # If gym_id is provided, check if gym exists
        if gym_id:
            gym = db.get_gym('gym_id', gym_id)
            if not gym:
                return jsonify({'error': 'Gym not found'}), 404
        
        # Update trainer's gym
        if db.update_trainer(trainer_id, 'gym_id', gym_id):
            return jsonify({'message': 'Gym updated successfully'})
        else:
            return jsonify({'error': 'Failed to update gym'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trainers/<int:trainer_id>/fighters', methods=['GET'])
def get_trainer_fighters_api(trainer_id):
    """Get all fighters for a trainer"""
    try:
        fighters = db.get_trainer_fighters(trainer_id)
        if not fighters:
            return jsonify([])
        
        return jsonify([dict(fighter) for fighter in fighters])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trainers/<int:trainer_id>/fighters/<int:fighter_id>', methods=['DELETE'])
@require_login
def remove_fighter_from_trainer_api(trainer_id, fighter_id):
    """Remove a fighter from a trainer"""
    try:
        # Check if relationship exists
        current_fighters = db.get_trainer_fighters(trainer_id)
        fighter_exists = False
        for f in current_fighters:
            if f['fighter_id'] == fighter_id and f['end_date'] is None:
                fighter_exists = True
                break
        
        if not fighter_exists:
            return jsonify({'error': 'Fighter not assigned to this trainer'}), 404
        
        # Remove fighter
        if db.remove_fighter_trainer(fighter_id, trainer_id):
            return jsonify({'message': 'Fighter removed successfully'})
        else:
            return jsonify({'error': 'Failed to remove fighter'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# Add these gym API routes to app.py

@app.route('/api/gyms/<int:gym_id>', methods=['GET'])
def get_gym_details(gym_id):
    """Get detailed gym information"""
    try:
        gym = db.get_gym('gym_id', gym_id)
        if not gym:
            return jsonify({'error': 'Gym not found'}), 404
        
        gym_dict = dict(gym)
        
        # Get fighter count
        fighters = db.get_gym_fighters(gym_id)
        gym_dict['fighter_count'] = len(fighters) if fighters else 0
        
        # Get trainer count
        trainers = db.get_gym_trainers(gym_id)
        gym_dict['trainer_count'] = len(trainers) if trainers else 0
        
        # Calculate total wins for fighters in this gym
        total_wins = 0
        if fighters:
            for fighter in fighters:
                record = db.get_fighter_with_record(fighter['fighter_id'])
                if record and 'wins' in record:
                    total_wins += record.get('wins', 0)
        gym_dict['total_wins'] = total_wins
        
        return jsonify(gym_dict)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gyms/<int:gym_id>', methods=['PUT'])
@require_login
def update_gym_api(gym_id):
    """Update gym information"""
    try:
        data = request.get_json()
        
        # Check if gym exists
        gym = db.get_gym('gym_id', gym_id)
        if not gym:
            return jsonify({'error': 'Gym not found'}), 404
        
        # Update allowed fields
        allowed_fields = ['name', 'location', 'owner', 'reputation_score']
        
        updates = {}
        for field in allowed_fields:
            if field in data:
                updates[field] = data[field]
        
        # Apply updates
        for field, value in updates.items():
            if not db.update_gym(gym_id, field, value):
                return jsonify({'error': f'Failed to update {field}'}), 500
        
        return jsonify({'message': 'Gym updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gyms/<int:gym_id>', methods=['DELETE'])
@require_login
def delete_gym_api(gym_id):
    """Delete a gym"""
    try:
        # Check if gym exists
        gym = db.get_gym('gym_id', gym_id)
        if not gym:
            return jsonify({'error': 'Gym not found'}), 404
        
        # Delete gym
        if db.delete_gym(gym_id):
            return jsonify({'message': 'Gym deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete gym'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gyms/<int:gym_id>/fighters', methods=['GET'])
def get_gym_fighters_api(gym_id):
    """Get all fighters for a gym"""
    try:
        fighters = db.get_gym_fighters(gym_id)
        if not fighters:
            return jsonify([])
        
        # Enhance with fighter records
        enhanced_fighters = []
        for fighter in fighters:
            fighter_dict = dict(fighter)
            
            # Get fighter record
            record = db.get_fighter_with_record(fighter_dict['fighter_id'])
            if record:
                fighter_dict['wins'] = record.get('wins', 0)
                fighter_dict['losses'] = record.get('losses', 0)
                fighter_dict['draws'] = record.get('draws', 0)
            
            enhanced_fighters.append(fighter_dict)
        
        return jsonify(enhanced_fighters)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gyms/<int:gym_id>/trainers', methods=['GET'])
def get_gym_trainers_api(gym_id):
    """Get all trainers for a gym"""
    try:
        trainers = db.get_gym_trainers(gym_id)
        if not trainers:
            return jsonify([])
        
        return jsonify([dict(trainer) for trainer in trainers])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Gym API Routes
@app.route('/api/gyms', methods=['GET'])
def get_gyms():
    """Get all gyms"""
    try:
        search_term = request.args.get('search', '')
        
        if search_term:
            gyms = db.search_gyms(search_term, limit=100)
        else:
            gyms = db.get_all_gyms(limit=100)
        
        if not gyms:
            return jsonify([])
        
        return jsonify([dict(gym) for gym in gyms])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gyms', methods=['POST'])
@require_login
def create_gym():
    """Create a new gym"""
    try:
        data = request.get_json()
        
        required_fields = ['name', 'location', 'owner']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        gym_id = db.create_gym(
            name=data['name'],
            location=data['location'],
            owner=data['owner'],
            reputation_score=data.get('reputation_score', 75)
        )
        
        if gym_id:
            return jsonify({'id': gym_id, 'message': 'Gym created successfully'})
        else:
            return jsonify({'error': 'Failed to create gym'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Trainer API Routes
@app.route('/api/trainers', methods=['GET'])
def get_trainers():
    """Get all trainers"""
    try:
        search_term = request.args.get('search', '')
        
        if search_term:
            trainers = db.search_trainers(search_term, limit=100)
        else:
            trainers = db.get_all_trainers(limit=100)
        
        if not trainers:
            return jsonify([])
        
        # Enhance with gym info
        enhanced_trainers = []
        for trainer in trainers:
            trainer_dict = dict(trainer)
            
            if trainer_dict.get('gym_id'):
                gym = db.get_gym('gym_id', trainer_dict['gym_id'])
                if gym:
                    trainer_dict['gym_name'] = gym['name']
            
            enhanced_trainers.append(trainer_dict)
        
        return jsonify(enhanced_trainers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fighters/<int:fighter_id>/trainers', methods=['GET'])
def get_fighter_trainers(fighter_id):
    """Get all trainers for a fighter"""
    try:
        trainers = db.get_fighter_trainers(fighter_id)
        if not trainers:
            return jsonify([])
        
        return jsonify([dict(trainer) for trainer in trainers])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fighters/<int:fighter_id>/trainers', methods=['POST'])
@require_login
def add_fighter_trainer(fighter_id):
    """Add a trainer to a fighter"""
    try:
        data = request.get_json()
        trainer_id = data.get('trainer_id')
        
        if not trainer_id:
            return jsonify({'error': 'trainer_id is required'}), 400
        
        # Check if fighter exists
        fighter = db.get_fighter('fighter_id', fighter_id)
        if not fighter:
            return jsonify({'error': 'Fighter not found'}), 404
        
        # Check if trainer exists
        trainer = db.get_trainer('trainer_id', trainer_id)
        if not trainer:
            return jsonify({'error': 'Trainer not found'}), 404
        
        # Check if relationship already exists
        current_trainers = db.get_fighter_trainers(fighter_id)
        for t in current_trainers:
            if t['trainer_id'] == trainer_id and t['end_date'] is None:
                return jsonify({'error': 'Trainer is already assigned to this fighter'}), 400
        
        # Add trainer
        if db.add_fighter_trainer(fighter_id, trainer_id):
            return jsonify({'message': 'Trainer added successfully'})
        else:
            return jsonify({'error': 'Failed to add trainer'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fighters/<int:fighter_id>/trainers/<int:trainer_id>', methods=['DELETE'])
@require_login
def remove_fighter_trainer(fighter_id, trainer_id):
    """Remove a trainer from a fighter"""
    try:
        # Check if relationship exists
        current_trainers = db.get_fighter_trainers(fighter_id)
        trainer_exists = False
        for t in current_trainers:
            if t['trainer_id'] == trainer_id and t['end_date'] is None:
                trainer_exists = True
                break
        
        if not trainer_exists:
            return jsonify({'error': 'Trainer not assigned to this fighter'}), 404
        
        # Remove trainer
        if db.remove_fighter_trainer(fighter_id, trainer_id):
            return jsonify({'message': 'Trainer removed successfully'})
        else:
            return jsonify({'error': 'Failed to remove trainer'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Match API Routes (for completeness)
@app.route('/api/matches', methods=['GET'])
def get_matches():
    """Get all matches"""
    try:
        search_term = request.args.get('search', '')
        
        if search_term:
            matches = db.search_matches(search_term, limit=100)
        else:
            matches = db.get_all_matches(limit=100)
                
        if matches is None:
            return jsonify([])
        
        # Convert to list of dicts
        matches_list = []
        for match in matches:
            match_dict = dict(match)
            
            # Get fighter details for each match
            match_id = match_dict['match_id']
            fighter_details = db.get_match_fighters(match_id)
            if fighter_details:
                match_dict.update(dict(fighter_details))
            
            matches_list.append(match_dict)
        
        return jsonify(matches_list)
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/matches')
def debug_matches():
    """Debug endpoint to check what's happening"""
    try:
        # Check if table exists
        table_check = db.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'match_events'
            );
        """, fetchone=True)
        
        # Count matches
        count = db.execute("SELECT COUNT(*) as count FROM match_events", fetchone=True)
        
        # Get sample matches
        sample = db.execute("""
            SELECT match_id, start_date, location 
            FROM match_events 
            LIMIT 5
        """, fetch=True)
        
        return jsonify({
            'table_exists': table_check['exists'] if table_check else False,
            'total_matches': count['count'] if count else 0,
            'sample_matches': sample if sample else [],
            'database_uri_set': bool(os.environ.get("DB_URI")),
            'app_secret_set': bool(os.environ.get('SECRET_KEY'))
        })
    except Exception as e:
        return jsonify({'error': str(e)})

# Utility routes
@app.route('/api/fighters/without-gym')
def get_fighters_without_gym():
    """Get fighters without gym affiliation"""
    try:
        fighters = db.get_all_fighters_without_gym()
        return jsonify([dict(fighter) for fighter in fighters]) if fighters else jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trainers/without-gym')
def get_trainers_without_gym():
    """Get trainers without gym affiliation"""
    try:
        trainers = db.get_all_trainers_without_gym()
        return jsonify([dict(trainer) for trainer in trainers]) if trainers else jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Resource not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('500.html'), 500

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

@app.route('/api/matches/<int:match_id>', methods=['GET'])
@app.route('/api/matches/<int:match_id>', methods=['GET'])
def get_match_details(match_id):
    """Get detailed match information"""
    try:
        print(f"DEBUG: Getting match details for match_id: {match_id}")
        
        # Get match details
        match_details = db.execute("""
            SELECT 
                match_id, 
                start_date, 
                end_date, 
                EXTRACT(EPOCH FROM (end_date - start_date)) as duration_seconds,
                location
            FROM match_events WHERE match_id = %s
        """, (match_id,), fetchone=True)
        
        if not match_details:
            return jsonify({'error': 'Match not found'}), 404
        
        # Convert to serializable dictionary
        result = convert_to_dict(match_details)
        
        # Get fighter details
        fighters = db.get_match_fighters(match_id)
        if fighters:
            fighters_dict = convert_to_dict(fighters)
            result.update(fighters_dict)
        
        # Convert duration_seconds to duration string
        if 'duration_seconds' in result and result['duration_seconds']:
            total_seconds = int(result['duration_seconds'])
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            result['duration'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            result['duration'] = None
        
        # Remove duration_seconds
        result.pop('duration_seconds', None)
        
        return jsonify(result)
    except Exception as e:
        print(f"Error getting match details: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/matches/<int:match_id>', methods=['PUT'])
@require_login
def update_match_api(match_id):
    """Update match information"""
    try:
        data = request.get_json()
        
        # Check if match exists
        match = db.execute("SELECT * FROM match_events WHERE match_id = %s", (match_id,), fetchone=True)
        if not match:
            return jsonify({'error': 'Match not found'}), 404
        
        # Update allowed fields
        allowed_fields = ['start_date', 'end_date', 'location']
        
        updates = {}
        for field in allowed_fields:
            if field in data:
                updates[field] = data[field]
        
        # Apply updates
        for field, value in updates.items():
            if not db.update_match(match_id, field, value):
                return jsonify({'error': f'Failed to update {field}'}), 500
        
        return jsonify({'message': 'Match updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/matches', methods=['POST'])
@require_login
def create_match_api():
    """Create a new match"""
    try:
        data = request.get_json()
        
        required_fields = ['start_date', 'location', 'fighter1_id', 'fighter2_id']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Default values
        end_date = data.get('end_date')
        winner_id = data.get('winner_id', 0)  # Default to draw if not specified
        
        # Create match
        match_id = db.create_match(
            start_date=data['start_date'],
            location=data['location'],
            fighter1_id=data['fighter1_id'],
            fighter2_id=data['fighter2_id'],
            end_date=end_date,
            winner_id=winner_id
        )
        
        if match_id:
            return jsonify({'id': match_id, 'message': 'Match created successfully'})
        else:
            return jsonify({'error': 'Failed to create match'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

# =================== UPDATE MATCH FIGHTERS ===================

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

# ==================== UPDATE MATCH RESULT ====================

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

# Add a context processor for datetime formatting
@app.context_processor
def utility_processor():
    import datetime
    def format_datetime(value, format='%Y-%m-%d %H:%M'):
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                return value
        return value.strftime(format)
    
    def format_date(value, format='%Y-%m-%d'):
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.datetime.fromisoformat(value.split('T')[0])
            except:
                return value
        return value.strftime(format)
    
    return dict(format_datetime=format_datetime, format_date=format_date)

@app.route('/api/stats')
def get_stats():
    try:
        fighters = db.execute("SELECT COUNT(*) as count FROM fighters", fetchone=True)['count']
        gyms = db.execute("SELECT COUNT(*) as count FROM gyms", fetchone=True)['count']
        trainers = db.execute("SELECT COUNT(*) as count FROM trainers", fetchone=True)['count']
        matches = db.execute("SELECT COUNT(*) as count FROM match_events", fetchone=True)['count']
        
        return jsonify({
            'fighters': fighters,
            'gyms': gyms,
            'trainers': trainers,
            'matches': matches,
            'success': True
        })
    except Exception as e:
        print(f"Error getting stats: {e}")
        return jsonify({
            'fighters': 0,
            'gyms': 0,
            'trainers': 0,
            'matches': 0,
            'success': False
        })

@app.route('/init-db')
def init_db():
    db.init_db()
    return 'Database initialized successfully'

if __name__ == '__main__':
    app.run(debug=True)