from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, session, flash, Response
import os
import json
import qrcode
import io
from fpdf import FPDF
from io import BytesIO
from datetime import datetime, time
import base64
import csv
import re
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
import threading
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
from flask_mail import Message
from flask import current_app as app
from flask_mail import Mail, Message
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email,Optional
from wtforms import StringField, SelectField, SubmitField, HiddenField, RadioField
from wtforms.validators import DataRequired, Email, Length, Regexp
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.platypus import Image
import random
import string
from pathlib import Path
from datetime import datetime, timedelta
import pytz
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import textwrap
from num2words import num2words
import math
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
csrf = CSRFProtect(app)


# Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'creator_club@sphoorthyengg.ac.in'
app.config['MAIL_PASSWORD'] = 'coav ajwz asgj lmfg'
app.config['MAIL_DEFAULT_SENDER'] = 'creator_club@sphoorthyengg.ac.in'



app.config['WTF_CSRF_CHECK_DEFAULT'] = False  # Disable CSRF by default
app.config['WTF_CSRF_ENABLED'] = True  # But keep CSRF enabled overall
team_id_lock = threading.Lock()

# Reservation system removed — no buffer time

def get_student_status(rollno):
    """Check if a student is already registered. Returns 'REGISTERED' or 'AVAILABLE'."""
    rollno = rollno.strip().upper()
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                    for team in data.get('teams', []):
                        for member in team.get('members', []):
                            if member.get('rollno', '').upper() == rollno:
                                return 'REGISTERED', {
                                    'team_id': team.get('team_id'),
                                    'team_name': team.get('team_name')
                                }
        except Exception as e:
            app.logger.error(f"Error checking registration: {e}")
    return 'AVAILABLE', None

mail = Mail(app)

# Credentials
ADMIN_CREDENTIALS = {'username': 'AD2025', 'password': 'CCAD02'}
TEAMS_CREDENTIALS = {'username': 'TC2025', 'password': 'CCMA1'}
UPLOAD_FOLDER = 'static/images/logos'

HOMEPAGE_CONFIG_FILE = 'data/homepage_config.json'

def get_homepage_config():
    try:
        with open(HOMEPAGE_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return {
            'hero_title': '36 Hours Hackathon Registration',
            'hero_subtitle': 'Register your team for the 36 Hours Hackathon event and showcase your skills',
            'event_date': 'July 21-23, 2025',
            'event_location': 'Sphoorthy Engineering College Campus',
            'registration_deadline': 'July 15, 2025',
            'about_event': 'Join us for an exciting competition where teams showcase their skills and compete for amazing prizes through challenges that test both technical and creative abilities.<br><b>Teams selected from the Ideathon will receive incubation support, mentorship, and potential funding opportunities to help turn their ideas into real-world solutions.</b>',
            'requirements': [
                'Teams must have 3-4 members',
                'Complete all required member information',
                'Payment must be completed for registration',
                'Members can be from any Institutions',
                'Registration deadline: July 15, 2025'
            ]
        }

@app.context_processor
def inject_config():
    return dict(homepage_config=get_homepage_config())

# File upload configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Startup logic to migrate files from old upload folder (root static/uploads) to new upload folder (app static/uploads)
try:
    old_uploads = os.path.join(os.getcwd(), 'static', 'uploads')
    new_uploads = app.config['UPLOAD_FOLDER']
    if os.path.exists(old_uploads) and os.path.abspath(old_uploads) != os.path.abspath(new_uploads):
        import shutil
        os.makedirs(new_uploads, exist_ok=True)
        for item in os.listdir(old_uploads):
            src_path = os.path.join(old_uploads, item)
            dst_path = os.path.join(new_uploads, item)
            if os.path.isfile(src_path) and not os.path.exists(dst_path):
                shutil.copy2(src_path, dst_path)
                print(f"Migrated payment screenshot: {item}")
except Exception as e:
    print(f"Error migrating uploads: {str(e)}")



# Ensure data directories exist
os.makedirs('data', exist_ok=True)
os.makedirs('static/qr_images', exist_ok=True)
# Add this at application startup
os.makedirs(os.path.join(app.root_path, 'static', 'receipts'), exist_ok=True)
os.makedirs(os.path.join(app.root_path, 'static', 'qr_images'), exist_ok=True)
os.makedirs(os.path.join(app.root_path, 'data'), exist_ok=True)
# At the start of create_receipt_pdf()
receipts_dir = os.path.join(app.root_path, 'static', 'receipts')
os.makedirs(receipts_dir, exist_ok=True)  # Create if doesn't exist
# File paths
DATABASE_FILE = 'data/database.json'
SCANNED_LOG_FILE = 'data/scanned_log.json'
SUGGESTIONS_FILE = 'data/suggestions.json'
EMAIL_LOGS_FILE = 'data/email_logs.json'
STUDENT_DATABASE_FILE = 'data/students.json'


# Constants
YEARS = ['1st', '2nd', '3rd', '4th']
BRANCHES = [
    'CSE', 'CSE(AIML)', 'CSE(CS)', 'CSE(DS)', 
    'MECHANICAL', 'CIVIL', 'ECE', 'EEE', 'FRESHMAN'
]

# Section mapping for each branch
SECTION_MAPPING = {
    'CSE': ['A', 'B', 'C', 'D', 'E'],
    'CSE(AIML)': ['A', 'B', 'C', 'D', 'E'],
    'CSE(CS)': ['A', 'B', 'C', 'D', 'E'],
    'CSE(DS)': ['A', 'B', 'C', 'D', 'E'],
    'MECHANICAL': ['A', 'B', 'C', 'D', 'E'],
    'CIVIL': ['A', 'B', 'C', 'D', 'E'],
    'ECE': ['A', 'B', 'C', 'D', 'E'],
    'EEE': ['A', 'B', 'C', 'D', 'E'],
    'FRESHMAN': ['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon', 
                'Zeta', 'Eta', 'Theta', 'Iota', 'Omega']
}

SCAN_TYPES = ['entry', 'breakfast', 'lunch', 'dinner']
PHONEPE_QR_CODE = 'static/team_001_qr.png'
HACKATHON_CONFIG_FILE = 'data/hackathon_config.json'

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'success': False,
        'error': str(e),
        'message': 'Resource not found'
    }), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({
        'success': False,
        'error': str(e),
        'message': 'Internal server error'
    }), 500

IST = pytz.timezone('Asia/Kolkata')

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Default configuration
    default_config = {
        'payment_required': True,
        'registration_fee': 500,
        'registration_open': True,
        'registration_message': "Registrations are currently closed. Please check back later.",
        'reservation_duration': 5
    }
    
    if request.method == 'POST':
        try:
            # Get form data
            payment_required = request.form.get('payment_required') == 'on'
            registration_fee = int(request.form.get('registration_fee', 500))
            registration_open = request.form.get('registration_open') == 'on'
            registration_message = request.form.get('registration_message', '')
            reservation_duration = int(request.form.get('reservation_duration', 5))
            
            with db_transaction():
                # Load existing config to preserve other keys if any
                config = {}
                if os.path.exists(HACKATHON_CONFIG_FILE):
                    try:
                        with open(HACKATHON_CONFIG_FILE, 'r') as f:
                            config = json.load(f)
                    except:
                        pass
                
                config.update({
                    'payment_required': payment_required,
                    'registration_fee': registration_fee,
                    'registration_open': registration_open,
                    'registration_message': registration_message,
                    'reservation_duration': reservation_duration
                })
                
                # Save to file
                with open(HACKATHON_CONFIG_FILE, 'w') as f:
                    json.dump(config, f, indent=4)
            
            flash('Settings updated successfully!', 'success')
        except Exception as e:
            flash(f'Error saving settings: {str(e)}', 'error')
    
    # Load current config
    try:
        with db_transaction():
            if os.path.exists(HACKATHON_CONFIG_FILE):
                with open(HACKATHON_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            else:
                config = default_config
    except:
        config = default_config
        
    # Ensure all default keys are present in config
    for key, val in default_config.items():
        if key not in config:
            config[key] = val
    
    return render_template('admin_settings.html', config=config)

@app.route('/check_roll_number', methods=['POST'])
def check_roll_number():
    roll_no = request.json.get('roll_no', '').strip().upper()
    if not roll_no:
        return jsonify({'exists': False})
    
    # Check for existing roll number in the JSON database
    existing_roll = False
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r') as f:
            try:
                data = json.load(f)
                for team in data.get('teams', []):
                    for member in team.get('members', []):
                        if member.get('rollno', '').strip().upper() == roll_no:
                            existing_roll = True
                            break
                    if existing_roll:
                        break
            except Exception:
                pass

    return jsonify({'exists': existing_roll})

def initialize_files():
    """Initialize all required data files with proper structure"""
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Initialize main database file
    if not os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'w') as f:
            json.dump({'teams': []}, f, indent=4)
        print(f"✅ Created {DATABASE_FILE}")
    else:
        # Validate existing file structure
        try:
            with open(DATABASE_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
                else:
                    data = {}
            
            # Ensure 'teams' key exists
            if 'teams' not in data:
                data['teams'] = []
                with open(DATABASE_FILE, 'w') as f:
                    json.dump(data, f, indent=4)
                print(f"✅ Fixed structure in {DATABASE_FILE}")
        except json.JSONDecodeError:
            # Backup corrupted file
            backup_file = f"{DATABASE_FILE}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(DATABASE_FILE, backup_file)
            print(f"⚠️ Corrupted {DATABASE_FILE} backed up to {backup_file}")
            
            # Create new file
            with open(DATABASE_FILE, 'w') as f:
                json.dump({'teams': []}, f, indent=4)
            print(f"✅ Recreated {DATABASE_FILE}")

@app.route('/admin/homepage', methods=['GET', 'POST'])
def admin_homepage():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        try:
            # Get form data
            config = {
                'hero_title': request.form.get('hero_title', ''),
                'hero_subtitle': request.form.get('hero_subtitle', ''),
                'event_date': request.form.get('event_date', ''),
                'event_location': request.form.get('event_location', ''),
                'registration_deadline': request.form.get('registration_deadline', ''),
                'about_event': request.form.get('about_event', ''),
                'requirements': [
                    request.form.get('requirement1', ''),
                    request.form.get('requirement2', ''),
                    request.form.get('requirement3', ''),
                    request.form.get('requirement4', ''),
                    request.form.get('requirement5', '')
                ]
            }
            
            # Validate - ensure no empty requirements
            config['requirements'] = [req for req in config['requirements'] if req.strip()]
            
            # Save to file
            with open(HOMEPAGE_CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            
            flash('Homepage content updated successfully!', 'success')
            return redirect(url_for('admin_homepage'))
        
        except Exception as e:
            flash(f'Error saving homepage content: {str(e)}', 'error')
    
    # Load current config
    config = get_homepage_config()
    
    # Ensure we have exactly 5 requirements (pad with empty strings if needed)
    while len(config['requirements']) < 5:
        config['requirements'].append('')
    
    return render_template('admin_homepage.html', config=config)



def get_teams_from_database():
    """Get all teams from database with error handling"""
    try:
        with open(DATABASE_FILE, 'r') as f:
            data = json.load(f)
            return data.get('teams', [])
    except Exception as e:
        print(f"Error reading database: {str(e)}")
        return []


# Add these imports with your existing imports
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash

# Add these new constants after your existing constants
EVALUATION_CONFIG_FILE = 'data/evaluation_config.json'
EVALUATORS_FILE = 'data/evaluators.json'
PROJECTS_FILE = 'data/projects.json'
EVALUATIONS_FILE = 'data/evaluations.json'
ALLOWED_EXTENSIONS_PPT = {'ppt', 'pptx', 'pdf', 'doc', 'docx'}

# ============= EVALUATION SYSTEM ROUTES =============

@app.route('/admin/evaluation-settings', methods=['GET', 'POST'])
def evaluation_settings():
    """Admin panel to control evaluation and submission features"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Load current settings
    try:
        with open(EVALUATION_CONFIG_FILE, 'r') as f:
            config = json.load(f)
    except:
        config = {
            'evaluation_enabled': False,
            'submissions_enabled': False,
            'presentation_template_link': '',
            'evaluators': [],
            'criteria': [
                {'name': 'Problem Statement', 'max_marks': 10},
                {'name': 'Innovation/Creativity', 'max_marks': 10},
                {'name': 'Technical Implementation', 'max_marks': 20},
                {'name': 'Presentation', 'max_marks': 10},
                {'name': 'Feasibility', 'max_marks': 10}
            ]
        }
    
    # Ensure presentation_template_link exists in config
    if 'presentation_template_link' not in config:
        config['presentation_template_link'] = ''
    
    # Ensure rounds config exists
    if 'rounds' not in config:
        config['rounds'] = {
            'round1': {'enabled': True,  'label': 'Round 1 – Preliminary'},
            'round2': {'enabled': False, 'label': 'Round 2 – Detailed'},
            'round3': {'enabled': False, 'label': 'Round 3 – Final'}
        }
    
    # Load evaluators
    try:
        with open(EVALUATORS_FILE, 'r') as f:
            evaluators = json.load(f).get('evaluators', [])
    except:
        evaluators = []
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'toggle_evaluation':
            config['evaluation_enabled'] = not config['evaluation_enabled']
            flash(f'Evaluation {"enabled" if config["evaluation_enabled"] else "disabled"}', 'success')
        
        elif action == 'toggle_submissions':
            config['submissions_enabled'] = not config['submissions_enabled']
            flash(f'Submissions {"enabled" if config["submissions_enabled"] else "disabled"}', 'success')
        
        elif action == 'update_submission_link':
            link = request.form.get('presentation_template_link', '').strip()
            config['presentation_template_link'] = link
            flash('Presentation template Google Drive link updated successfully!', 'success')
        
        elif action == 'add_evaluator':
            username = request.form.get('username')
            password = request.form.get('password')
            name = request.form.get('name')
            
            if username and password and name:
                # Check if username exists
                if any(e['username'] == username for e in evaluators):
                    flash('Username already exists', 'error')
                else:
                    evaluator = {
                        'id': str(uuid.uuid4())[:8],
                        'username': username,
                        'password': generate_password_hash(password),
                        'name': name,
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    evaluators.append(evaluator)
                    
                    with open(EVALUATORS_FILE, 'w') as f:
                        json.dump({'evaluators': evaluators}, f, indent=4)
                    
                    flash(f'Evaluator {name} added successfully', 'success')
        
        elif action == 'delete_evaluator':
            evaluator_id = request.form.get('evaluator_id')
            evaluators = [e for e in evaluators if e['id'] != evaluator_id]
            with open(EVALUATORS_FILE, 'w') as f:
                json.dump({'evaluators': evaluators}, f, indent=4)
            flash('Evaluator deleted', 'success')
        
        elif action == 'update_criteria':
            criteria = []
            names = request.form.getlist('criteria_name[]')
            marks = request.form.getlist('criteria_marks[]')
            
            for name, mark in zip(names, marks):
                if name and mark:
                    criteria.append({'name': name, 'max_marks': int(mark)})
            
            config['criteria'] = criteria
            flash('Evaluation criteria updated', 'success')
        
        elif action in ('toggle_round1', 'toggle_round2', 'toggle_round3'):
            round_key = action.replace('toggle_', '')  # 'round1', 'round2', 'round3'
            # Ensure rounds config exists
            if 'rounds' not in config:
                config['rounds'] = {
                    'round1': {'enabled': True,  'label': 'Round 1 – Preliminary'},
                    'round2': {'enabled': False, 'label': 'Round 2 – Detailed'},
                    'round3': {'enabled': False, 'label': 'Round 3 – Final'}
                }
            # Round 1 can never be fully disabled (it's the base round)
            if round_key == 'round1':
                flash('Round 1 is always required and cannot be disabled', 'error')
            else:
                config['rounds'][round_key]['enabled'] = not config['rounds'][round_key]['enabled']
                state = 'enabled' if config['rounds'][round_key]['enabled'] else 'disabled'
                flash(f"{config['rounds'][round_key]['label']} {state}", 'success')
        
        # Save config
        with open(EVALUATION_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        
        return redirect(url_for('evaluation_settings'))
    
    return render_template('evaluation_settings.html', config=config, evaluators=evaluators)


@app.route('/evaluator-login', methods=['GET', 'POST'])
def evaluator_login():
    """Login page for evaluators"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            with open(EVALUATORS_FILE, 'r') as f:
                data = json.load(f)
                evaluators = data.get('evaluators', [])
            
            evaluator = next((e for e in evaluators if e['username'] == username), None)
            
            if evaluator and check_password_hash(evaluator['password'], password):
                session['evaluator_logged_in'] = True
                session['evaluator_id'] = evaluator['id']
                session['evaluator_name'] = evaluator['name']
                return redirect(url_for('evaluation_dashboard'))
            
            flash('Invalid credentials', 'error')
        except Exception as e:
            flash('Login error', 'error')
    
    return render_template('evaluator_login.html')
@app.route('/evaluation-dashboard')
def evaluation_dashboard():
    """Evaluator dashboard"""
    if not session.get('evaluator_logged_in'):
        return redirect(url_for('evaluator_login'))
    
    # Check if evaluation is enabled
    config = {}
    try:
        with open(EVALUATION_CONFIG_FILE, 'r') as f:
            config = json.load(f)
        if not config.get('evaluation_enabled', False):
            flash('Evaluation is currently disabled', 'warning')
    except:
        flash('Evaluation configuration error', 'warning')
    
    # Get all teams that have submitted projects - with duplicate removal
    projects = []
    seen_team_ids = set()
    
    try:
        if os.path.exists(PROJECTS_FILE):
            with open(PROJECTS_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    projects_data = json.loads(content)
                else:
                    projects_data = {'projects': []}
                
                # Handle different data structures
                raw_projects = []
                if isinstance(projects_data, dict):
                    if 'projects' in projects_data:
                        if isinstance(projects_data['projects'], list):
                            raw_projects = projects_data['projects']
                elif isinstance(projects_data, list):
                    raw_projects = projects_data
                
                # Filter out empty projects and remove duplicates
                for p in raw_projects:
                    if isinstance(p, dict):
                        # Skip empty projects
                        if not p or not p.get('team_id'):
                            app.logger.warning(f"Skipping empty project: {p}")
                            continue
                        
                        team_id = p.get('team_id')
                        if team_id:
                            if team_id not in seen_team_ids:
                                seen_team_ids.add(team_id)
                                projects.append(p)
                        else:
                            app.logger.warning(f"Project missing team_id: {p}")
    except Exception as e:
        app.logger.error(f"Error loading projects: {str(e)}")
        projects = []
    
    # Get evaluator's previous evaluations
    my_evaluations = []
    try:
        if os.path.exists(EVALUATIONS_FILE):
            with open(EVALUATIONS_FILE, 'r') as f:
                eval_data = json.load(f)
                evaluations = eval_data.get('evaluations', [])
                if isinstance(evaluations, list):
                    my_evaluations = [e for e in evaluations 
                                    if isinstance(e, dict) and 
                                    e.get('evaluator_id') == session['evaluator_id']]
    except Exception as e:
        app.logger.error(f"Error loading evaluations: {str(e)}")
    
    # Determine the highest enabled round
    highest_active_round = 1
    if config.get('rounds', {}).get('round3', {}).get('enabled'):
        highest_active_round = 3
    elif config.get('rounds', {}).get('round2', {}).get('enabled'):
        highest_active_round = 2

    # Mark which projects are already evaluated by THIS evaluator or OTHERS in highest active round
    evaluated_teams_highest_round = set()
    locked_teams = {}
    all_evaluations_by_team = {}
    
    try:
        if os.path.exists(EVALUATIONS_FILE):
            with open(EVALUATIONS_FILE, 'r') as f:
                eval_data = json.load(f)
                all_evals = eval_data.get('evaluations', [])
                for e in all_evals:
                    if isinstance(e, dict) and e.get('team_id'):
                        tid = e['team_id']
                        # Track who evaluated this team in general (for display names)
                        if tid not in all_evaluations_by_team:
                            all_evaluations_by_team[tid] = e.get('evaluator_name', 'Unknown')
                        
                        # Track active round completions
                        round_key = f'round{highest_active_round}'
                        if e.get(round_key, {}).get('completed', False):
                            if e.get('evaluator_id') == session['evaluator_id']:
                                evaluated_teams_highest_round.add(tid)
                            else:
                                locked_teams[tid] = e.get('evaluator_name', 'Another Evaluator')
    except Exception:
        pass

    # Recalculate stats based on highest round evaluations
    total_projects = len(projects)
    evaluated_by_me_count = len(evaluated_teams_highest_round)
    locked_count = len(locked_teams)
    
    projects_to_evaluate_count = max(0, total_projects - evaluated_by_me_count - locked_count)
    pending_count = max(0, total_projects - evaluated_by_me_count - locked_count)
    
    return render_template('evaluation_dashboard.html', 
                         projects=projects,
                         evaluated_teams=evaluated_teams_highest_round,
                         locked_teams=locked_teams,
                         my_evaluations=my_evaluations,
                         all_evaluations_by_team=all_evaluations_by_team,
                         projects_to_evaluate_count=projects_to_evaluate_count,
                         evaluated_by_me_count=evaluated_by_me_count,
                         pending_count=pending_count,
                         config=config)

@app.route('/admin/cleanup-projects')
def cleanup_projects():
    """Remove duplicate projects based on team_id"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        if os.path.exists(PROJECTS_FILE):
            with open(PROJECTS_FILE, 'r') as f:
                data = json.load(f)
            
            # Handle different data structures
            projects_list = []
            if isinstance(data, dict):
                if 'projects' in data:
                    projects_list = data['projects']
                else:
                    projects_list = [data]
            elif isinstance(data, list):
                projects_list = data
            
            # Remove duplicates
            seen_team_ids = set()
            unique_projects = []
            duplicates_removed = 0
            
            for project in projects_list:
                if isinstance(project, dict):
                    team_id = project.get('team_id')
                    if team_id:
                        if team_id not in seen_team_ids:
                            seen_team_ids.add(team_id)
                            unique_projects.append(project)
                        else:
                            duplicates_removed += 1
                    else:
                        # Keep projects without team_id but log them
                        unique_projects.append(project)
            
            # Save back with proper structure
            with open(PROJECTS_FILE, 'w') as f:
                json.dump({'projects': unique_projects}, f, indent=4)
            
            return jsonify({
                'success': True,
                'message': f'Cleaned up projects. Removed {duplicates_removed} duplicates.',
                'original_count': len(projects_list),
                'new_count': len(unique_projects)
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    

@app.route('/debug-projects-list')
def debug_projects_list():
    """Debug endpoint to see what projects are in the system"""
    if not session.get('admin_logged_in') and not session.get('evaluator_logged_in'):
        return redirect(url_for('admin_login'))
    
    result = {
        'projects_file_exists': os.path.exists(PROJECTS_FILE),
        'projects_file_path': PROJECTS_FILE,
        'evaluations_file_exists': os.path.exists(EVALUATIONS_FILE),
        'projects': [],
        'raw_data_preview': None
    }
    
    try:
        if os.path.exists(PROJECTS_FILE):
            with open(PROJECTS_FILE, 'r') as f:
                content = f.read()
                result['file_size'] = len(content)
                result['raw_data_preview'] = content[:500] if content else 'Empty file'
                
                if content.strip():
                    try:
                        data = json.loads(content)
                        
                        # Handle different structures
                        if isinstance(data, dict):
                            if 'projects' in data:
                                projects_list = data['projects']
                            else:
                                projects_list = [data] if data else []
                        elif isinstance(data, list):
                            projects_list = data
                        else:
                            projects_list = []
                        
                        result['projects_count'] = len(projects_list)
                        
                        # Add details about each project
                        for i, p in enumerate(projects_list):
                            if isinstance(p, dict):
                                project_info = {
                                    'index': i,
                                    'team_id': p.get('team_id', 'MISSING'),
                                    'team_name': p.get('team_name', 'Unknown'),
                                    'project_title': p.get('project_title', 'Untitled'),
                                    'tech_stack': p.get('tech_stack', 'Not specified'),
                                    'has_tech_stack': bool(p.get('tech_stack')),
                                    'file_path': p.get('file_path', 'Not specified'),
                                    'file_exists': os.path.exists(p.get('file_path', '')) if p.get('file_path') else False,
                                    'keys': list(p.keys())
                                }
                                result['projects'].append(project_info)
                    except json.JSONDecodeError as e:
                        result['json_error'] = str(e)
        else:
            result['error'] = f'Projects file not found at: {PROJECTS_FILE}'
            
    except Exception as e:
        result['error'] = str(e)
    
    # Also check evaluated teams
    try:
        if os.path.exists(EVALUATIONS_FILE):
            with open(EVALUATIONS_FILE, 'r') as f:
                eval_content = f.read()
                if eval_content.strip():
                    eval_data = json.loads(eval_content)
                    evaluations = eval_data.get('evaluations', [])
                    result['evaluations_count'] = len(evaluations)
                    
                    # Get unique evaluated team IDs
                    evaluated_teams = set()
                    for e in evaluations:
                        if isinstance(e, dict) and e.get('team_id'):
                            evaluated_teams.add(e['team_id'])
                    result['evaluated_teams'] = list(evaluated_teams)
    except Exception as e:
        result['evaluations_error'] = str(e)
    
    return jsonify(result)

@app.route('/admin/fix-tech-stack')
def fix_tech_stack():
    """Add default tech stack to projects that don't have one"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    fixed_count = 0
    try:
        if os.path.exists(PROJECTS_FILE):
            with open(PROJECTS_FILE, 'r') as f:
                data = json.load(f)
            
            # Handle different data structures
            projects_list = []
            if isinstance(data, dict):
                if 'projects' in data:
                    projects_list = data['projects']
                else:
                    projects_list = [data]
                    data = {'projects': projects_list}
            elif isinstance(data, list):
                projects_list = data
                data = {'projects': projects_list}
            
            # Fix each project
            for project in projects_list:
                if isinstance(project, dict):
                    if not project.get('tech_stack') or project.get('tech_stack') == '':
                        project['tech_stack'] = 'Not specified'
                        fixed_count += 1
            
            # Save back
            with open(PROJECTS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            
            return jsonify({
                'success': True,
                'message': f'Fixed {fixed_count} projects',
                'fixed_count': fixed_count
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Projects file not found'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    
@app.route('/evaluate/<team_id>', methods=['GET', 'POST'])
def evaluate_team(team_id):
    """Evaluation form for a specific team with dynamic multi-round structure"""
    if not session.get('evaluator_logged_in'):
        return redirect(url_for('evaluator_login'))
    
    # Load config for criteria & rounds
    try:
        with open(EVALUATION_CONFIG_FILE, 'r') as f:
            config = json.load(f)
    except:
        config = {'criteria': [], 'rounds': {'round1': {'enabled': True, 'label': 'Round 1 – Preliminary'}, 'round2': {'enabled': False, 'label': 'Round 2 – Detailed'}, 'round3': {'enabled': False, 'label': 'Round 3 – Final'}}}
    
    # Ensure rounds key exists
    if 'rounds' not in config:
        config['rounds'] = {
            'round1': {'enabled': True,  'label': 'Round 1 – Preliminary'},
            'round2': {'enabled': False, 'label': 'Round 2 – Detailed'},
            'round3': {'enabled': False, 'label': 'Round 3 – Final'}
        }
    
    criteria = config.get('criteria', [])
    
    # Get team details from database
    team = None
    try:
        with open(DATABASE_FILE, 'r') as f:
            data = json.load(f)
            team = next((t for t in data.get('teams', []) if t.get('team_id') == team_id), None)
    except Exception as e:
        app.logger.error(f"Error loading team: {str(e)}")
        flash('Error loading team data', 'error')
        return redirect(url_for('evaluation_dashboard'))
    
    if not team:
        flash('Team not found', 'error')
        return redirect(url_for('evaluation_dashboard'))
    
    # Get project details safely
    project = None
    try:
        if os.path.exists(PROJECTS_FILE):
            with open(PROJECTS_FILE, 'r') as f:
                content = f.read().strip()
                projects_data = json.loads(content) if content else {'projects': []}
                projects = []
                if isinstance(projects_data, dict) and 'projects' in projects_data:
                    projects = projects_data['projects'] if isinstance(projects_data['projects'], list) else []
                elif isinstance(projects_data, list):
                    projects = projects_data
                for p in projects:
                    if isinstance(p, dict) and p.get('team_id') == team_id:
                        project = p
                        break
    except Exception as e:
        app.logger.error(f"Error loading project: {str(e)}")
        project = None
    
    if not project:
        flash('Project not found for this team', 'warning')
    
    # Load all evaluations
    all_evaluations = []
    try:
        with open(EVALUATIONS_FILE, 'r') as f:
            all_evaluations = json.load(f).get('evaluations', [])
    except Exception as e:
        app.logger.error(f"Error loading evaluations: {str(e)}")
    
    # Check if already evaluated by THIS evaluator
    existing = next((e for e in all_evaluations
                     if isinstance(e, dict)
                     and e.get('team_id') == team_id
                     and e.get('evaluator_id') == session['evaluator_id']), None)
    
    # Determine the highest enabled round
    highest_active_round = 1
    if config.get('rounds', {}).get('round3', {}).get('enabled'):
        highest_active_round = 3
    elif config.get('rounds', {}).get('round2', {}).get('enabled'):
        highest_active_round = 2

    # Check if already evaluated by ANY OTHER evaluator in the highest active round
    other_eval = next((e for e in all_evaluations
                       if isinstance(e, dict)
                       and e.get('team_id') == team_id
                       and e.get('evaluator_id') != session['evaluator_id']
                       and e.get(f'round{highest_active_round}', {}).get('completed', False)), None)
    already_evaluated_by = other_eval.get('evaluator_name', 'Another Evaluator') if other_eval else None
    
    if request.method == 'POST':
        # If locked by another evaluator, reject silently
        if already_evaluated_by:
            flash(f'This team has already been evaluated by {already_evaluated_by}', 'error')
            return redirect(url_for('evaluation_dashboard'))
        
        problem_statement_accepted = request.form.get('accept_problem_statement') == 'yes'
        
        # Helper: build marks dict for a round from form
        def collect_round_marks(round_num):
            marks = {}
            for criterion in criteria:
                slug = criterion['name'].lower().replace(' ', '_').replace('/', '_')
                key = f'round{round_num}_{slug}'
                max_m = int(criterion.get('max_marks', 10))
                val = min(int(request.form.get(key, 0) or 0), max_m)
                marks[criterion['name']] = val
            return marks
        
        evaluation = {
            'id': existing.get('id', str(uuid.uuid4())) if existing else str(uuid.uuid4()),
            'team_id': team_id,
            'team_name': team.get('team_name', 'Unknown'),
            'evaluator_id': session['evaluator_id'],
            'evaluator_name': session['evaluator_name'],
            'problem_statement_accepted': problem_statement_accepted,
            'round1': {},
            'round2': {},
            'round3': {},
            'comments': request.form.get('comments', ''),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if problem_statement_accepted:
            round1_passed = request.form.get('round1_passed') == 'yes'
            r1_marks = collect_round_marks(1)
            evaluation['round1'] = {**r1_marks, 'passed': round1_passed, 'completed': True}
            
            if round1_passed and config['rounds'].get('round2', {}).get('enabled'):
                round2_passed = request.form.get('round2_passed') == 'yes'
                r2_marks = collect_round_marks(2)
                evaluation['round2'] = {**r2_marks, 'passed': round2_passed, 'completed': True}
                
                if round2_passed and config['rounds'].get('round3', {}).get('enabled'):
                    r3_marks = collect_round_marks(3)
                    evaluation['round3'] = {**r3_marks, 'completed': True}
        
        # Calculate totals per round (sum all criterion marks)
        def round_total(round_data):
            if not round_data:
                return 0
            return sum(v for k, v in round_data.items()
                       if k not in ('passed', 'completed') and isinstance(v, (int, float)))
        
        r1t = round_total(evaluation['round1'])
        r2t = round_total(evaluation['round2'])
        r3t = round_total(evaluation['round3'])
        
        completed_rounds = [t for t in [r1t, r2t, r3t]
                            if t > 0 or (evaluation[f'round{[r1t,r2t,r3t].index(t)+1}'] and
                                         evaluation[f'round{[r1t,r2t,r3t].index(t)+1}'].get('completed'))]
        
        # simpler: count completed flags
        n_done = sum(1 for rk in ('round1', 'round2', 'round3')
                     if evaluation[rk].get('completed'))
        total_sum = r1t + r2t + r3t
        
        evaluation['round1_total'] = r1t
        evaluation['round2_total'] = r2t
        evaluation['round3_total'] = r3t
        evaluation['final_average'] = round(total_sum / n_done, 2) if n_done > 0 else 0
        
        # Persist
        try:
            with open(EVALUATIONS_FILE, 'r') as f:
                eval_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            eval_data = {'evaluations': []}
        
        if 'evaluations' not in eval_data or not isinstance(eval_data['evaluations'], list):
            eval_data['evaluations'] = []
        
        if existing:
            for i, e in enumerate(eval_data['evaluations']):
                if isinstance(e, dict) and e.get('id') == existing['id']:
                    eval_data['evaluations'][i] = evaluation
                    break
        else:
            eval_data['evaluations'].append(evaluation)
        
        try:
            with open(EVALUATIONS_FILE, 'w') as f:
                json.dump(eval_data, f, indent=4)
            flash('Evaluation saved successfully!', 'success')
        except Exception as e:
            app.logger.error(f"Error saving evaluation: {str(e)}")
            flash('Error saving evaluation', 'error')
            return redirect(url_for('evaluate_team', team_id=team_id))
        
        return redirect(url_for('evaluation_dashboard'))
    
    return render_template('evaluate.html',
                           team=team, project=project,
                           config=config, criteria=criteria,
                           existing=existing,
                           already_evaluated_by=already_evaluated_by)


@app.route('/submit-project', methods=['GET', 'POST'])
def submit_project():
    """Page for teams to submit their project presentations"""
    # Load config for submission control and template link
    presentation_template_link = ''
    try:
        with open(EVALUATION_CONFIG_FILE, 'r') as f:
            config = json.load(f)
        if not config.get('submissions_enabled', False):
            return render_template('submission_closed.html', 
                                 message='Project submissions are currently closed')
        presentation_template_link = config.get('presentation_template_link', '')
    except:
        pass
    
    if request.method == 'POST':
        team_id = request.form.get('team_id', '').strip().upper()
        
        # Validate team ID
        if not os.path.exists(DATABASE_FILE):
            flash('Database error', 'error')
            return render_template('submit_project.html', team=None, presentation_template_link=presentation_template_link)
            
        with open(DATABASE_FILE, 'r') as f:
            data = json.load(f)
            team = next((t for t in data.get('teams', []) if t.get('team_id') == team_id), None)
        
        if not team:
            flash('Invalid Team ID', 'error')
            return render_template('submit_project.html', team=None, presentation_template_link=presentation_template_link)
        
        # Check if payment verified
        if not team.get('payment_verified', False):
            flash('Payment must be verified before submitting project', 'error')
            return render_template('submit_project.html', team=team, presentation_template_link=presentation_template_link)
        
        # Get form data
        project_title = request.form.get('project_title', '').strip()
        problem_statement = request.form.get('problem_statement', '').strip()
        solution = request.form.get('solution', '').strip()
        tech_stack = request.form.get('tech_stack', '').strip()
        presentation_link = request.form.get('presentation_link', '').strip()
        
        # Validate required fields
        if not project_title:
            flash('Project title is required', 'error')
            return render_template('submit_project.html', team=team, presentation_template_link=presentation_template_link)
        
        if not problem_statement:
            flash('Problem statement is required', 'error')
            return render_template('submit_project.html', team=team, presentation_template_link=presentation_template_link)
        
        if not solution:
            flash('Solution description is required', 'error')
            return render_template('submit_project.html', team=team, presentation_template_link=presentation_template_link)
        
        if not presentation_link:
            flash('Presentation Google Drive link is required', 'error')
            return render_template('submit_project.html', team=team, presentation_template_link=presentation_template_link)
        
        if not (presentation_link.startswith('http://') or presentation_link.startswith('https://')):
            flash('Presentation link must be a valid URL starting with http:// or https://', 'error')
            return render_template('submit_project.html', team=team, presentation_template_link=presentation_template_link)
        
        # Validate character limits
        if len(problem_statement) > 500:
            flash('Problem statement exceeds 500 characters limit', 'error')
            return render_template('submit_project.html', team=team, presentation_template_link=presentation_template_link)
        
        if len(solution) > 1000:
            flash('Solution exceeds 1000 characters limit', 'error')
            return render_template('submit_project.html', team=team, presentation_template_link=presentation_template_link)
        
        # Ensure projects file has correct structure
        initialize_projects_file()
        
        # Load existing projects with proper error handling
        projects_data = {'projects': []}
        try:
            if os.path.exists(PROJECTS_FILE):
                with open(PROJECTS_FILE, 'r') as f:
                    content = f.read().strip()
                    if content:
                        projects_data = json.loads(content)
                    else:
                        projects_data = {'projects': []}
                    
                    # Ensure 'projects' key exists
                    if not isinstance(projects_data, dict):
                        projects_data = {'projects': []}
                    elif 'projects' not in projects_data:
                        if isinstance(projects_data, list):
                            projects_data = {'projects': projects_data}
                        else:
                            projects_data = {'projects': [projects_data] if projects_data else []}
        except json.JSONDecodeError as e:
            app.logger.error(f"Error loading projects file: {e}")
            # Backup corrupted file
            if os.path.exists(PROJECTS_FILE):
                backup_file = f"{PROJECTS_FILE}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(PROJECTS_FILE, backup_file)
            projects_data = {'projects': []}
        
        # Check if team already submitted
        existing = None
        for p in projects_data.get('projects', []):
            if isinstance(p, dict) and p.get('team_id') == team_id:
                existing = p
                break
        
        # Create/Update project record
        project = {
            'team_id': team_id,
            'team_name': team['team_name'],
            'project_title': project_title,
            'problem_statement': problem_statement,
            'solution': solution,
            'tech_stack': tech_stack,
            'presentation_link': presentation_link,
            'submitted_by': team['members'][0]['name'] if team['members'] else 'Unknown',
            'submission_date': existing.get('submission_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')) if existing else datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if existing:
            # Update existing - remove old and add new
            valid_projects = []
            for p in projects_data.get('projects', []):
                if isinstance(p, dict) and p.get('team_id') != team_id:
                    valid_projects.append(p)
            valid_projects.append(project)
            projects_data['projects'] = valid_projects
            flash('Project updated successfully!', 'success')
        else:
            # Add new
            projects_data['projects'].append(project)
            flash('Project submitted successfully!', 'success')
        
        # Save to file
        with open(PROJECTS_FILE, 'w') as f:
            json.dump(projects_data, f, indent=4)
        
        return redirect(url_for('submit_project', team_id=team_id))
    
    # GET request
    team_id = request.args.get('team_id', '').strip().upper()
    team = None
    project = None
    
    if team_id:
        # Load team
        if os.path.exists(DATABASE_FILE):
            with open(DATABASE_FILE, 'r') as f:
                data = json.load(f)
                for t in data.get('teams', []):
                    if isinstance(t, dict) and t.get('team_id') == team_id:
                        team = t
                        break
        
        # Load existing project if any
        if team and os.path.exists(PROJECTS_FILE):
            try:
                with open(PROJECTS_FILE, 'r') as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                        if isinstance(data, dict):
                            projects = data.get('projects', [])
                            for p in projects:
                                if isinstance(p, dict) and p.get('team_id') == team_id:
                                    project = p
                                    break
            except Exception as e:
                app.logger.error(f"Error loading project: {e}")
    
    return render_template('submit_project.html', team=team, project=project, presentation_template_link=presentation_template_link)


@app.route('/admin/cleanup-projects-now', methods=['GET'])
def cleanup_projects_now():
    """Clean up duplicate projects and fix the projects file"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        # Backup existing file
        if os.path.exists(PROJECTS_FILE):
            backup_file = f"{PROJECTS_FILE}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            import shutil
            shutil.copy2(PROJECTS_FILE, backup_file)
            
            with open(PROJECTS_FILE, 'r') as f:
                data = json.load(f)
            
            # Handle different data structures
            projects_list = []
            if isinstance(data, dict):
                if 'projects' in data:
                    if isinstance(data['projects'], list):
                        projects_list = data['projects']
                    else:
                        projects_list = [data['projects']] if data['projects'] else []
                else:
                    projects_list = [data] if data else []
            elif isinstance(data, list):
                projects_list = data
            else:
                projects_list = []
            
            # Remove empty projects and duplicates
            seen_team_ids = set()
            unique_projects = []
            empty_removed = 0
            duplicate_removed = 0
            
            for project in projects_list:
                if not isinstance(project, dict):
                    continue
                    
                # Skip empty projects
                if not project or not project.get('team_id'):
                    empty_removed += 1
                    continue
                
                team_id = project.get('team_id')
                if team_id not in seen_team_ids:
                    seen_team_ids.add(team_id)
                    unique_projects.append(project)
                else:
                    duplicate_removed += 1
            
            # Save cleaned data
            with open(PROJECTS_FILE, 'w') as f:
                json.dump({'projects': unique_projects}, f, indent=4)
            
            return jsonify({
                'success': True,
                'message': f'Cleaned up projects file',
                'backup_created': backup_file,
                'original_count': len(projects_list),
                'empty_projects_removed': empty_removed,
                'duplicate_projects_removed': duplicate_removed,
                'unique_projects_count': len(unique_projects)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Projects file not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    
@app.route('/admin/fix-projects')
def fix_projects():
    """Fix project file structure and paths"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    result = {'fixed': 0, 'errors': []}
    
    # First, ensure projects file exists with correct structure
    initialize_projects_file()
    
    try:
        with open(PROJECTS_FILE, 'r') as f:
            projects_data = json.load(f)
        
        # Ensure projects_data has the right structure
        if not isinstance(projects_data, dict):
            projects_data = {'projects': projects_data if isinstance(projects_data, list) else []}
        elif 'projects' not in projects_data:
            if isinstance(projects_data, list):
                projects_data = {'projects': projects_data}
            else:
                projects_data = {'projects': [projects_data] if projects_data else []}
        
        # Fix each project
        for project in projects_data['projects']:
            old_path = project.get('file_path')
            filename = project.get('filename')
            
            if not old_path or not os.path.exists(old_path):
                if filename:
                    # Try to find the file
                    possible_paths = [
                        os.path.join(app.root_path, 'static', 'uploads', 'projects', filename),
                        os.path.join('static', 'uploads', 'projects', filename),
                        os.path.join(app.root_path, 'static', 'uploads', filename),
                        old_path  # Keep original if it exists
                    ]
                    
                    for path in possible_paths:
                        if path and os.path.exists(path):
                            project['file_path'] = path
                            result['fixed'] += 1
                            break
                    else:
                        result['errors'].append(f"Could not find file for {project['team_id']}: {filename}")
        
        # Save fixed data
        with open(PROJECTS_FILE, 'w') as f:
            json.dump(projects_data, f, indent=4)
        
    except Exception as e:
        result['errors'].append(str(e))
    
    return jsonify(result)
# Add this temporary route to fix paths
@app.route('/admin/fix-project-paths')
def fix_project_paths():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    fixed = 0
    errors = []
    
    try:
        if os.path.exists(PROJECTS_FILE):
            with open(PROJECTS_FILE, 'r') as f:
                projects_data = json.load(f)
            
            for project in projects_data.get('projects', []):
                old_path = project.get('file_path')
                filename = project.get('filename')
                
                if not old_path or not os.path.exists(old_path):
                    # Try to find the file
                    possible_path = os.path.join(app.root_path, 'static', 'uploads', 'projects', filename)
                    if os.path.exists(possible_path):
                        project['file_path'] = possible_path
                        fixed += 1
                    else:
                        errors.append(f"Could not find file for {project['team_id']}: {filename}")
            
            # Save fixed paths
            with open(PROJECTS_FILE, 'w') as f:
                json.dump(projects_data, f, indent=4)
    
    except Exception as e:
        return jsonify({'error': str(e)})
    
    return jsonify({'fixed': fixed, 'errors': errors})

# Add this temporary route to debug


@app.route('/debug-projects')
def debug_projects():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        with open(PROJECTS_FILE, 'r') as f:
            projects = json.load(f)
        
        # Check file existence
        for project in projects.get('projects', []):
            file_path = project.get('file_path')
            exists = os.path.exists(file_path) if file_path else False
            project['file_exists'] = exists
            project['actual_path'] = file_path
        
        return jsonify(projects)
    except Exception as e:
        return jsonify({'error': str(e)})

def initialize_projects_file():
    """Initialize the projects file with correct structure"""
    os.makedirs('data', exist_ok=True)
    
    if not os.path.exists(PROJECTS_FILE):
        with open(PROJECTS_FILE, 'w') as f:
            json.dump({'projects': []}, f, indent=4)
        print(f"✅ Created {PROJECTS_FILE}")
    else:
        # Check if existing file has correct structure
        try:
            with open(PROJECTS_FILE, 'r') as f:
                data = json.load(f)
            
            # If the file doesn't have the 'projects' key, fix it
            if 'projects' not in data:
                # Try to recover existing data
                if isinstance(data, list):
                    # If it's a list, move it to projects key
                    corrected_data = {'projects': data}
                elif isinstance(data, dict):
                    # If it's a dict but missing projects key, wrap it
                    corrected_data = {'projects': [data]}
                else:
                    # Default empty structure
                    corrected_data = {'projects': []}
                
                # Save corrected structure
                with open(PROJECTS_FILE, 'w') as f:
                    json.dump(corrected_data, f, indent=4)
                print(f"✅ Fixed structure in {PROJECTS_FILE}")
        except json.JSONDecodeError:
            # File is corrupted, create new one
            with open(PROJECTS_FILE, 'w') as f:
                json.dump({'projects': []}, f, indent=4)
            print(f"✅ Recreated corrupted {PROJECTS_FILE}")

# Call this after other initializations
initialize_projects_file()

 
@app.route('/get-team-details', methods=['POST'])
def get_team_details_ajax():
    """AJAX endpoint to get team details by ID"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
            
        team_id = data.get('team_id', '').strip().upper()
        
        if not team_id:
            return jsonify({'success': False, 'error': 'Team ID required'})
        
        # Load database
        if not os.path.exists(DATABASE_FILE):
            return jsonify({'success': False, 'error': 'Database not found'})
            
        with open(DATABASE_FILE, 'r') as f:
            data = json.load(f)
            team = None
            for t in data.get('teams', []):
                if isinstance(t, dict) and t.get('team_id') == team_id:
                    team = t
                    break
        
        if team:
            # Get existing project if any
            project = None
            try:
                if os.path.exists(PROJECTS_FILE):
                    with open(PROJECTS_FILE, 'r') as f:
                        content = f.read().strip()
                        if content:
                            projects_data = json.load(content)
                        else:
                            projects_data = {'projects': []}
                        
                        # Handle different data structures
                        projects = []
                        if isinstance(projects_data, dict) and 'projects' in projects_data:
                            if isinstance(projects_data['projects'], list):
                                projects = projects_data['projects']
                        elif isinstance(projects_data, list):
                            projects = projects_data
                        
                        # Find project safely
                        for p in projects:
                            if isinstance(p, dict) and p.get('team_id') == team_id:
                                project = p
                                break
            except Exception as e:
                app.logger.error(f"Error loading project: {e}")
            
            return jsonify({
                'success': True,
                'team': {
                    'team_id': team.get('team_id'),
                    'team_name': team.get('team_name'),
                    'members': team.get('members', []),
                    'payment_verified': team.get('payment_verified', False)
                },
                'project': project
            })
        
        return jsonify({'success': False, 'error': 'Team not found'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/admin/leaderboard')
def leaderboard():
    """Admin leaderboard showing average scores from all evaluators"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Load all evaluations
    try:
        with open(EVALUATIONS_FILE, 'r') as f:
            evaluations = json.load(f).get('evaluations', [])
    except:
        evaluations = []
    
    # Load projects to filter only submitted ones
    try:
        with open(PROJECTS_FILE, 'r') as f:
            projects_data = json.load(f)
            projects = projects_data.get('projects', [])
            # Ensure projects is a list
            if not isinstance(projects, list):
                projects = []
    except:
        projects = []
    
    # Calculate average scores per team
    team_scores = {}
    for eval_item in evaluations:
        if not isinstance(eval_item, dict):
            continue
            
        team_id = eval_item.get('team_id')
        if not team_id:
            continue
        
        if team_id not in team_scores:
            team_scores[team_id] = {
                'team_name': eval_item.get('team_name', 'Unknown'),
                'scores': [],
                'evaluations': [],
                'total_evaluators': 0,
                'marks_breakdown': {}
            }
        
        team_scores[team_id]['scores'].append(eval_item.get('total', 0))
        team_scores[team_id]['evaluations'].append(eval_item)
        team_scores[team_id]['total_evaluators'] += 1
        
        # Aggregate marks per criterion
        marks = eval_item.get('marks', {})
        if isinstance(marks, dict):
            for criterion, mark in marks.items():
                if criterion not in team_scores[team_id]['marks_breakdown']:
                    team_scores[team_id]['marks_breakdown'][criterion] = []
                team_scores[team_id]['marks_breakdown'][criterion].append(mark)
    
    # Calculate averages
    leaderboard = []
    for team_id, data in team_scores.items():
        # Check if team has submitted project
        project = None
        for p in projects:
            if isinstance(p, dict) and p.get('team_id') == team_id:
                project = p
                break
                
        if not project:
            continue  # Skip teams that haven't submitted
            
        avg_score = sum(data['scores']) / len(data['scores']) if data['scores'] else 0
        
        # Calculate average per criterion
        avg_breakdown = {}
        for criterion, marks in data['marks_breakdown'].items():
            avg_breakdown[criterion] = sum(marks) / len(marks) if marks else 0
        
        leaderboard.append({
            'team_id': team_id,
            'team_name': data['team_name'],
            'avg_score': round(avg_score, 2),
            'total_evaluators': data['total_evaluators'],
            'project_title': project.get('project_title', 'Untitled'),
            'submission_date': project.get('submission_date', 'Unknown'),
            'avg_breakdown': avg_breakdown
        })
    
    # Sort by average score descending
    leaderboard.sort(key=lambda x: x['avg_score'], reverse=True)
    
    # Add ranks
    for i, team in enumerate(leaderboard, 1):
        team['rank'] = i
    
    # Get config for max possible score
    try:
        with open(EVALUATION_CONFIG_FILE, 'r') as f:
            config = json.load(f)
            max_possible = sum(c.get('max_marks', 0) for c in config.get('criteria', []) if isinstance(c, dict))
    except:
        max_possible = 60
        
    homepage_config = get_homepage_config()
    
    return render_template('leaderboard.html', 
                         leaderboard=leaderboard,
                         max_possible=max_possible,
                         homepage_config=homepage_config)


@app.route('/admin/evaluation-results')
def evaluation_results():
    """Detailed evaluation results for admin"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Load all data
    try:
        with open(EVALUATIONS_FILE, 'r') as f:
            evaluations = json.load(f).get('evaluations', [])
            if not isinstance(evaluations, list):
                evaluations = []
    except:
        evaluations = []
    
    try:
        with open(PROJECTS_FILE, 'r') as f:
            projects_data = json.load(f)
            projects = projects_data.get('projects', [])
            if not isinstance(projects, list):
                projects = []
    except:
        projects = []
    
    try:
        with open(EVALUATORS_FILE, 'r') as f:
            evaluators_data = json.load(f)
            evaluators = evaluators_data.get('evaluators', [])
            if not isinstance(evaluators, list):
                evaluators = []
    except:
        evaluators = []
    
    # Group by team
    teams_data = {}
    for eval_item in evaluations:
        if not isinstance(eval_item, dict):
            continue
            
        team_id = eval_item.get('team_id')
        if not team_id:
            continue
            
        if team_id not in teams_data:
            # Find project for this team
            project = None
            for p in projects:
                if isinstance(p, dict) and p.get('team_id') == team_id:
                    project = p
                    break
                    
            teams_data[team_id] = {
                'team_name': eval_item.get('team_name', 'Unknown'),
                'evaluations': [],
                'project': project
            }
        
        teams_data[team_id]['evaluations'].append(eval_item)
    
    # Compute average score per team in Python (safe type coercion)
    for team_id, data in teams_data.items():
        evals = data['evaluations']
        if evals:
            total_sum = sum(float(e.get('total', 0)) for e in evals)
            data['avg_score'] = round(total_sum / len(evals), 1)
        else:
            data['avg_score'] = 0

    return render_template('evaluation_results.html', 
                         teams_data=teams_data,
                         evaluators=evaluators)



@app.route('/download-project/<team_id>')
def download_project(team_id):
    """Download project presentation file"""
    if not session.get('admin_logged_in') and not session.get('evaluator_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        with open(PROJECTS_FILE, 'r') as f:
            projects_data = json.load(f)
            projects = projects_data.get('projects', [])
            
            # Find project safely
            project = None
            for p in projects:
                if isinstance(p, dict) and p.get('team_id') == team_id:
                    project = p
                    break
        
        if project and isinstance(project, dict):
            presentation_link = project.get('presentation_link')
            if presentation_link:
                return redirect(presentation_link)
            
            file_path = project.get('file_path')
            filename = project.get('filename')
            
            if file_path and os.path.exists(file_path):
                # Check if it's a raw view request
                if request.args.get('raw') == '1':
                    # For inline viewing
                    ext = filename.rsplit('.', 1)[1].lower() if filename and '.' in filename else ''
                    content_types = {
                        'pdf': 'application/pdf',
                        'jpg': 'image/jpeg',
                        'jpeg': 'image/jpeg',
                        'png': 'image/png',
                        'gif': 'image/gif',
                        'txt': 'text/plain'
                    }
                    mimetype = content_types.get(ext, 'application/octet-stream')
                    return send_file(file_path, 
                                   mimetype=mimetype,
                                   as_attachment=False)
                else:
                    # Normal download
                    return send_file(file_path, 
                                   as_attachment=True,
                                   download_name=filename)
        
        flash('File not found', 'error')
        return redirect(request.referrer or url_for('index'))
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'error')
        return redirect(request.referrer or url_for('index'))
    
@app.route('/view-project/<team_id>')
def view_project(team_id):
    """View project presentation inline in browser"""
    if not session.get('admin_logged_in') and not session.get('evaluator_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        with open(PROJECTS_FILE, 'r') as f:
            projects_data = json.load(f)
            projects = projects_data.get('projects', [])
            
            # Find project safely
            project = None
            for p in projects:
                if isinstance(p, dict) and p.get('team_id') == team_id:
                    project = p
                    break
        
        if not project or not isinstance(project, dict):
            flash('Project not found', 'error')
            return redirect(request.referrer or url_for('evaluation_dashboard'))
        
        presentation_link = project.get('presentation_link')
        if presentation_link:
            return redirect(presentation_link)
        
        # Get the file path from project
        file_path = project.get('file_path')
        
        # If file_path is relative, make it absolute
        if file_path and not os.path.isabs(file_path):
            # Try multiple possible base paths
            possible_paths = [
                file_path,  # Original path
                os.path.join(app.root_path, file_path),  # Relative to app root
                os.path.join(app.root_path, 'static', 'uploads', 'projects', os.path.basename(file_path)),  # In static/uploads/projects
                os.path.join('static', 'uploads', 'projects', os.path.basename(file_path)),  # Relative static path
            ]
            
            # Find the first existing path
            for path in possible_paths:
                if os.path.exists(path):
                    file_path = path
                    break
        
        # Check if file exists
        if not file_path or not os.path.exists(file_path):
            app.logger.error(f"File not found for team {team_id}. Tried: {file_path}")
            
            # Try to find the file by searching in common locations
            possible_dirs = [
                os.path.join(app.root_path, 'static', 'uploads', 'projects'),
                os.path.join('static', 'uploads', 'projects'),
                app.config.get('UPLOAD_FOLDER', 'static/uploads'),
            ]
            
            filename = project.get('filename')
            if filename:
                for directory in possible_dirs:
                    full_path = os.path.join(directory, filename)
                    if os.path.exists(full_path):
                        file_path = full_path
                        # Update the project record with correct path
                        project['file_path'] = full_path
                        with open(PROJECTS_FILE, 'w') as f:
                            json.dump(projects_data, f, indent=4)
                        app.logger.info(f"Updated file path for {team_id} to {full_path}")
                        break
            
            if not file_path or not os.path.exists(file_path):
                flash('Project file not found on server', 'error')
                return redirect(request.referrer or url_for('evaluation_dashboard'))
        
        # Get file extension
        filename = project.get('filename', '')
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        # Determine content type for inline viewing
        content_types = {
            'pdf': 'application/pdf',
            'ppt': 'application/vnd.ms-powerpoint',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'txt': 'text/plain'
        }
        
        content_type = content_types.get(ext, 'application/octet-stream')
        
        # For direct viewing of supported formats
        if ext in ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'txt']:
            return send_file(file_path, 
                           mimetype=content_type,
                           as_attachment=False)
        
        # For Office documents, use viewer page with Google Docs integration
        else:
            # Pass the file path as a parameter to the viewer template
            file_url = url_for('serve_project_file', filename=os.path.basename(file_path), _external=True)
            return render_template('view_presentation.html', 
                                 project=project,
                                 team_id=team_id,
                                 file_ext=ext,
                                 file_url=file_url)
        
    except Exception as e:
        app.logger.error(f"Error viewing project: {str(e)}")
        flash(f'Error viewing file: {str(e)}', 'error')
        return redirect(request.referrer or url_for('evaluation_dashboard'))  


@app.route('/project-file/<filename>')
def serve_project_file(filename):
    """Serve project files for viewing"""
    if not session.get('admin_logged_in') and not session.get('evaluator_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Look for the file in common locations
    possible_paths = [
        os.path.join(app.root_path, 'static', 'uploads', 'projects', filename),
        os.path.join('static', 'uploads', 'projects', filename),
        os.path.join(app.config.get('UPLOAD_FOLDER', 'static/uploads'), 'projects', filename),
    ]
    
    for file_path in possible_paths:
        if os.path.exists(file_path):
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            content_types = {
                'pdf': 'application/pdf',
                'ppt': 'application/vnd.ms-powerpoint',
                'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'doc': 'application/msword',
                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'gif': 'image/gif',
                'txt': 'text/plain'
            }
            return send_file(file_path, 
                           mimetype=content_types.get(ext, 'application/octet-stream'),
                           as_attachment=False)
    
    return "File not found", 404


@app.route('/api/verified-count', methods=['GET'])
def get_verified_count():
    """Get count of verified participants for QR reminder feature"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        with open(DATABASE_FILE, 'r') as f:
            data = json.load(f)
            teams = data.get('teams', [])
            
            verified_teams = [t for t in teams if t.get('payment_verified')]
            verified_count = sum(len(t.get('members', [])) for t in verified_teams)
            
            return jsonify({
                'success': True,
                'count': verified_count,
                'teams': len(verified_teams)
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/send-qr-reminders', methods=['POST'])
def send_qr_reminders():
    """Send QR code reminders to all payment-verified participants"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        # Load database
        with open(DATABASE_FILE, 'r') as f:
            data = json.load(f)
            teams = data.get('teams', [])
        
        # Filter verified teams
        verified_teams = [t for t in teams if t.get('payment_verified')]
        
        if not verified_teams:
            return jsonify({
                'success': False, 
                'message': 'No verified teams found'
            }), 404
        
        # Collect all recipients
        recipients = []
        for team in verified_teams:
            for member in team.get('members', []):
                if member.get('email'):
                    recipients.append({
                        'name': member.get('name'),
                        'email': member.get('email'),
                        'team': team.get('team_name'),
                        'team_id': team.get('team_id')
                    })
        
        if not recipients:
            return jsonify({
                'success': False, 
                'message': 'No email addresses found for verified participants'
            }), 404
        
        # Create email log entry
        email_log = {
            'id': str(uuid.uuid4()),
            'subject': '🔔 Event QR Code Reminder - IdeaHackathon 2026',
            'message': 'QR Code Reminder for verified participants',
            'recipients_type': 'qr_reminder',
            'total_recipients': len(recipients),
            'sent_by': session.get('admin_id', 'unknown'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'recipients': recipients[:100]
        }
        
        # Send emails in background thread
        def send_qr_reminders_thread():
            with app.app_context():
                sent_count = 0
                for recipient in recipients:
                    try:
                        # Get team data
                        team = next((t for t in verified_teams if t['team_id'] == recipient['team_id']), None)
                        if not team:
                            continue
                        
                        # Generate QR code
                        qr_data = {
                            'team_id': team['team_id'],
                            'team_name': team['team_name'],
                            'members': [{'name': m['name'], 'id': m['id']} for m in team['members']]
                        }
                        
                        qr_img = generate_qr_code_image(json.dumps(qr_data))
                        qr_img_base64 = base64.b64encode(qr_img.getvalue()).decode('utf-8')
                        
                        # Send thank you email (reuse existing function)
                        send_thank_you_email(recipient['email'], team, qr_img_base64)
                        sent_count += 1
                        
                    except Exception as e:
                        app.logger.error(f"Failed to send QR reminder to {recipient['email']}: {str(e)}")
                        log_email(recipient['team_id'], 'qr_reminder', recipient['email'], False, str(e))
                
                # Update log
                email_log['actually_sent'] = sent_count
                email_log['success_rate'] = f"{sent_count}/{len(recipients)}"
                
                # Save to email logs
                try:
                    email_logs = []
                    if os.path.exists(EMAIL_LOGS_FILE):
                        with open(EMAIL_LOGS_FILE, 'r') as f:
                            email_logs = json.load(f)
                    
                    email_logs.append(email_log)
                    
                    with open(EMAIL_LOGS_FILE, 'w') as f:
                        json.dump(email_logs, f, indent=4)
                except Exception as e:
                    app.logger.error(f"Failed to save email log: {str(e)}")
        
        threading.Thread(target=send_qr_reminders_thread).start()
        
        return jsonify({
            'success': True,
            'message': f'QR code reminders are being sent to {len(recipients)} recipients',
            'sent_count': len(recipients)
        })
        
    except Exception as e:
        app.logger.error(f"Error sending QR reminders: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500
     
# Receipt Generation completely removed.


def generate_qr_code(data, filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)

# Receipt email sending completely removed.


def send_payment_verification_email(recipient_email, team_data):
    """
    Send a responsive payment verification email with team details.
    """
    with app.app_context():
        try:
            # Load homepage config for event details
            homepage_config = get_homepage_config()
            
            # Load logos as base64 for embedding directly in HTML (no attachment needed)
            clglogo_b64 = ""
            cclogo_b64 = ""
            try:
                clglogo_path = os.path.join(app.root_path, 'static', 'images', 'logo', 'clglogo.png')
                if os.path.exists(clglogo_path):
                    with open(clglogo_path, 'rb') as f:
                        clglogo_b64 = base64.b64encode(f.read()).decode('utf-8')
            except Exception as e:
                print(f"⚠️ Failed to load college logo for verification email: {e}")

            try:
                cclogo_path = os.path.join(app.root_path, 'static', 'images', 'logo', 'cc.png')
                if os.path.exists(cclogo_path):
                    with open(cclogo_path, 'rb') as f:
                        cclogo_b64 = base64.b64encode(f.read()).decode('utf-8')
            except Exception as e:
                print(f"⚠️ Failed to load club logo for verification email: {e}")
            college_logo_src = "https://res.cloudinary.com/dvfqvqbkn/image/upload/v1752482945/clglogo_rqnxum.png"
            club_logo_src = "https://res.cloudinary.com/dvfqvqbkn/image/upload/v1752482876/cc_lbohfd.png"

            event_name = homepage_config.get('hero_title', '36 Hours Ideathon Registration').replace(' Registration', '')
            subject = f"✅ Payment Verified - Team {team_data['team_name']} | {event_name}"
            
            # Generate members list HTML
            members_html = ""
            for member in team_data['members']:
                members_html += f"<li style='margin-bottom: 8px; color: #666;'><strong>{member['name']}</strong> - {member.get('email', 'N/A')}</li>"
            
            # HTML email content
            html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>Payment Verified - {event_name}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        
        body {{
            background-color: #f4f7fc;
            line-height: 1.6;
        }}
        
        .email-wrapper {{
            max-width: 600px;
            margin: 20px auto;
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 20px 40px rgba(0,0,0,0.08);
        }}
        
        .email-header {{
            background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
            padding: 30px 20px;
            text-align: center;
            border-bottom: 4px solid #c41e3a;
        }}
        
        .logo-container {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        
        .logo {{
            height: 60px;
            margin-bottom: 15px;
            filter: drop-shadow(0 4px 6px rgba(0,0,0,0.2));
        }}
        
        .event-badge {{
            background: #c41e3a;
            color: white;
            padding: 6px 16px;
            border-radius: 40px;
            font-size: 0.9rem;
            font-weight: 500;
            display: inline-block;
            margin-bottom: 10px;
        }}
        
        .header-title {{
            color: white;
            font-size: 32px;
            font-weight: 700;
            margin: 10px 0;
            letter-spacing: -0.5px;
        }}
        
        .event-name {{
            color: #c41e3a;
            font-size: 22px;
            font-weight: 600;
            margin: 5px 0;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .success-icon {{
            text-align: center;
            margin-bottom: 25px;
        }}
        
        .success-icon i {{
            font-size: 70px;
            color: #28a745;
        }}
        
        .team-card {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            border-left: 4px solid #c41e3a;
        }}
        
        .team-card h3 {{
            color: #1a1a1a;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .team-card h3 i {{
            color: #c41e3a;
        }}
        
        .info-row {{
            display: flex;
            margin-bottom: 10px;
            padding: 8px 0;
            border-bottom: 1px solid #eaeaea;
        }}
        
        .info-label {{
            font-weight: 600;
            width: 120px;
            color: #666;
        }}
        
        .info-value {{
            flex: 1;
            color: #1a1a1a;
        }}
        
        .members-list {{
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
        }}
        
        .members-list ul {{
            list-style: none;
            padding-left: 0;
        }}
        
        .event-details-mini {{
            display: flex;
            justify-content: space-between;
            background: #e8f5e9;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            flex-wrap: wrap;
            gap: 10px;
        }}
        
        .event-detail-item {{
            text-align: center;
            flex: 1;
            min-width: 120px;
        }}
        
        .event-detail-item .label {{
            color: #666;
            font-size: 0.8rem;
            margin-bottom: 4px;
        }}
        
        .event-detail-item .value {{
            font-weight: 600;
            color: #1a1a1a;
        }}
        
        .next-steps {{
            background: #e8f5e9;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        
        .next-steps h4 {{
            color: #1a1a1a;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .next-steps ul {{
            list-style: none;
            padding-left: 0;
        }}
        
        .next-steps li {{
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .next-steps i {{
            color: #28a745;
            width: 20px;
        }}
        
        .footer {{
            background: #1a1a1a;
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        
        .footer-logos {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-bottom: 20px;
        }}
        
        .footer-logo {{
            height: 40px;
            filter: brightness(0) invert(1);
        }}
        
        .contact-links {{
            display: flex;
            justify-content: center;
            gap: 15px;
            flex-wrap: wrap;
            margin: 20px 0;
        }}
        
        .contact-links a {{
            color: white;
            text-decoration: none;
            padding: 8px 16px;
            background: rgba(255,255,255,0.1);
            border-radius: 40px;
            transition: all 0.3s ease;
        }}
        
        .contact-links a:hover {{
            background: #c41e3a;
            color: white;
        }}
        
        .developer-credit {{
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0 10px;
        }}
        
        @media (max-width: 480px) {{
            .content {{
                padding: 20px;
            }}
            
            .info-row {{
                flex-direction: column;
            }}
            
            .info-label {{
                width: 100%;
                margin-bottom: 4px;
            }}
            
            .header-title {{
                font-size: 28px;
            }}
            
            .event-name {{
                font-size: 18px;
            }}
            
            .event-details-mini {{
                flex-direction: column;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-header">
            <table align="center" border="0" cellpadding="0" cellspacing="0" style="margin: 0 auto 20px auto; text-align: center;">
                <tr>
                    <td style="padding: 0 10px; vertical-align: middle;">
                        <img src="{college_logo_src}" alt="College Logo" style="height: 60px; max-height: 60px; width: auto; display: block; border: 0;">
                    </td>
                    <td style="padding: 0 10px; vertical-align: middle;">
                        <img src="{club_logo_src}" alt="Creator Club" style="height: 60px; max-height: 60px; width: auto; display: block; border: 0;">
                    </td>
                </tr>
            </table>
            <span class="event-badge">{event_name}</span>
            <div class="header-title">PAYMENT VERIFIED!</div>
            <div class="event-name">Team {team_data['team_name']}</div>
        </div>
        
        <div class="content">
            <div class="success-icon">
                <i class="fas fa-check-circle"></i>
            </div>
            
            <p style="font-size: 18px; margin-bottom: 25px; text-align: center;">
                Dear <strong>Team {team_data['team_name']}</strong>,
            </p>
            
            <p style="color: #666; margin-bottom: 25px; text-align: center;">
                We're pleased to inform you that your payment has been verified and your registration for <strong>{event_name}</strong> is now complete!
            </p>
            
            <!-- Event Details Mini -->
            <div class="event-details-mini">
                <div class="event-detail-item">
                    <div class="label">Event Dates</div>
                    <div class="value">{homepage_config.get('event_date', 'March 06-07, 2026')}</div>
                </div>
                <div class="event-detail-item">
                    <div class="label">Venue</div>
                    <div class="value">{homepage_config.get('event_location', 'Sphoorthy Engineering College Campus')}</div>
                </div>
                <div class="event-detail-item">
                    <div class="label">Registration Deadline</div>
                    <div class="value">{homepage_config.get('registration_deadline', 'February 28, 2026')}</div>
                </div>
            </div>
            
            <div class="team-card">
                <h3><i class="fas fa-users"></i> Team Information</h3>
                
                <div class="info-row">
                    <span class="info-label">Team ID:</span>
                    <span class="info-value"><strong>{team_data['team_id']}</strong></span>
                </div>
                
                <div class="info-row">
                    <span class="info-label">Team Name:</span>
                    <span class="info-value"><strong>{team_data['team_name']}</strong></span>
                </div>
                
                <div class="info-row">
                    <span class="info-label">Total Members:</span>
                    <span class="info-value"><strong>{len(team_data['members'])}</strong></span>
                </div>
                
                <div class="members-list">
                    <h4 style="margin-bottom: 10px; color: #c41e3a;">Team Members:</h4>
                    <ul>
                        {members_html}
                    </ul>
                </div>
            </div>
            
            <!-- What's Next Section -->
            <div class="next-steps">
                <h4><i class="fas fa-arrow-right"></i> What's Next?</h4>
                <ul>
                    <li><i class="fas fa-check-circle"></i> <strong>Fully Registered:</strong> Your team is now fully registered for {event_name}</li>
                    <li><i class="fas fa-envelope"></i> <strong>Event Updates:</strong> Watch your email for the event schedule and important updates</li>
                    <li><i class="fas fa-qrcode"></i> <strong>QR Code:</strong> Keep your QR code handy for check-in at the venue</li>
                    <li><i class="fas fa-clock"></i> <strong>Prepare for 36 Hours:</strong> Get ready for an exciting competition with incubation opportunities!</li>
                </ul>
            </div>
            
            <!-- About Event Snippet -->
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="color: #666; font-style: italic;">
                    "{homepage_config.get('about_event', 'Teams selected from the Ideathon will receive incubation support, mentorship, and potential funding opportunities to help turn their ideas into real-world solutions.')}"
                </p>
            </div>
            
            <!-- Important Note -->
            <div style="background: #fff3cd; padding: 15px; border-radius: 8px;">
                <i class="fas fa-info-circle" style="color: #856404; margin-right: 8px;"></i>
                <span style="color: #856404; font-weight: 500;">Important:</span>
                <p style="color: #856404; margin-top: 5px;">Please report to the venue on {homepage_config.get('event_date', 'March 06-07, 2026')} at 9:00 AM sharp with your team members.</p>
            </div>
        </div>
        
        <div class="footer">
            <table align="center" border="0" cellpadding="0" cellspacing="0" style="margin: 0 auto 20px auto; text-align: center;">
                <tr>
                    <td style="padding: 0 10px; vertical-align: middle;">
                        <img src="{college_logo_src}" alt="College" style="height: 40px; max-height: 40px; width: auto; display: block; border: 0; filter: brightness(0) invert(1);">
                    </td>
                    <td style="padding: 0 10px; vertical-align: middle;">
                        <img src="{club_logo_src}" alt="Club" style="height: 40px; max-height: 40px; width: auto; display: block; border: 0; filter: brightness(0) invert(1);">
                    </td>
                </tr>
            </table>
            
            <p>Creator Club | Sphoorthy Engineering College</p>
            <p style="color: #ccc; font-size: 14px;">Organizers of {event_name}</p>
            
            <div class="contact-links">
                <a href="https://instagram.com/creator_club_official"><i class="fab fa-instagram"></i> Instagram</a>
                <a href="https://wa.me/919059160424"><i class="fab fa-whatsapp"></i> WhatsApp</a>
                <a href="mailto:creator_club@sphoorthyengg.ac.in"><i class="fas fa-envelope"></i> Email</a>
            </div>
            
            <p style="color: #999; font-size: 12px; margin-top: 20px;">
                © {datetime.now().year} Creator Club. All rights reserved.
            </p>
        </div>
    </div>
</body>
</html>
            """
            
            # Plain text version
            text = f"""
╔══════════════════════════════════════════════════════════════╗
║               PAYMENT VERIFIED - Creator Club                 ║
║{event_name.center(62)}║
╚══════════════════════════════════════════════════════════════╝

Dear Team {team_data['team_name']},

We're pleased to inform you that your payment has been verified and your registration for {event_name} is now complete!

════════════════════════════════════════════════════════════════
EVENT DETAILS
════════════════════════════════════════════════════════════════
Dates: {homepage_config.get('event_date', 'March 06-07, 2026')}
Venue: {homepage_config.get('event_location', 'Sphoorthy Engineering College Campus')}
Registration Deadline: {homepage_config.get('registration_deadline', 'February 28, 2026')}

════════════════════════════════════════════════════════════════
TEAM INFORMATION
════════════════════════════════════════════════════════════════
Team ID: {team_data['team_id']}
Team Name: {team_data['team_name']}
Total Members: {len(team_data['members'])}

TEAM MEMBERS:
{chr(10).join(f"- {member['name']} ({member['email']})" for member in team_data['members'])}

════════════════════════════════════════════════════════════════
WHAT'S NEXT?
════════════════════════════════════════════════════════════════
✓ Fully Registered: Your team is now fully registered for {event_name}
✓ Event Updates: Watch your email for the event schedule and important updates
✓ QR Code: Keep your QR code handy for check-in at the venue
✓ Prepare for 36 Hours: Get ready for an exciting competition with incubation opportunities!

ABOUT THE EVENT:
Teams selected from the Ideathon will receive incubation support, mentorship, and potential funding opportunities to help turn their ideas into real-world solutions.

IMPORTANT: Please report to the venue on {homepage_config.get('event_date', 'March 06-07, 2026')} at 9:00 AM sharp with your team members.

════════════════════════════════════════════════════════════════
CONTACT INFORMATION
════════════════════════════════════════════════════════════════
For any questions, contact us at:
Creator Club | Sphoorthy Engineering College
Instagram: @creator_club_official | WhatsApp: +91 9059160424
Email: creator_club@sphoorthyengg.ac.in

© {datetime.now().year} Creator Club. All rights reserved.
            """
            
            # Create and send message
            msg = Message(subject, recipients=[recipient_email])
            msg.body = text
            msg.html = html
            
            # Logos are now embedded as base64 data URIs directly in HTML — no attachment needed
            
            mail = app.extensions.get('mail')
            if mail:
                mail.send(msg)
                print(f"✓ Verification email sent successfully to {recipient_email}")
                log_email(team_data['team_id'], 'payment_verification', recipient_email, True)
            else:
                print("❌ Flask-Mail extension not initialized!")
            
        except Exception as e:
            print(f"❌ Failed to send verification email to {recipient_email}: {e}")
            log_email(team_data['team_id'], 'payment_verification', recipient_email, False, str(e))
            raise
        

def send_thank_you_email(recipient_email, team_data, qr_img_base64):
    """
    Send a fully responsive thank you email with team details and QR code.
    QR code is embedded as inline image, not attachment.
    """
    with app.app_context():
        try:
            # Load logos as base64 for embedding directly in HTML
            clglogo_b64 = ""
            cclogo_b64 = ""
            try:
                clglogo_path = os.path.join(app.root_path, 'static', 'images', 'logo', 'clglogo.png')
                if os.path.exists(clglogo_path):
                    with open(clglogo_path, 'rb') as f:
                        clglogo_b64 = base64.b64encode(f.read()).decode('utf-8')
            except Exception as e:
                print(f"⚠️ Failed to load college logo for email: {e}")

            try:
                cclogo_path = os.path.join(app.root_path, 'static', 'images', 'logo', 'cc.png')
                if os.path.exists(cclogo_path):
                    with open(cclogo_path, 'rb') as f:
                        cclogo_b64 = base64.b64encode(f.read()).decode('utf-8')
            except Exception as e:
                print(f"⚠️ Failed to load club logo for email: {e}")

            college_logo_src = "https://res.cloudinary.com/dvfqvqbkn/image/upload/v1752482945/clglogo_rqnxum.png"
            club_logo_src = "https://res.cloudinary.com/dvfqvqbkn/image/upload/v1752482876/cc_lbohfd.png"

            # Load hackathon config
            try:
                with open(HACKATHON_CONFIG_FILE, 'r') as f:
                    hackathon_config = json.load(f)
            except:
                hackathon_config = {'payment_required': True, 'registration_fee': 500}

            # Load homepage config for event details
            homepage_config = get_homepage_config()

            event_name = homepage_config.get('hero_title', '36 Hours Ideathon Registration').replace(' Registration', '')
            subject = f"✅ Registration Confirmed - Team {team_data['team_name']} | {event_name}"
            
            # Generate members list HTML with better styling
            members_html = ""
            for idx, member in enumerate(team_data['members'], 1):
                members_html += f"""
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eaeaea; text-align: center; width: 40px; color: #c41e3a; font-weight: 600;">{idx}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eaeaea;">
                        <strong style="color: #1a1a1a;">{member['name']}</strong><br>
                        <span style="color: #666; font-size: 0.85rem;">{member.get('branch', 'N/A')} - {member.get('year', 'N/A')}</span>
                    </td>
                    <td style="padding: 10px; border-bottom: 1px solid #eaeaea; color: #666;">{member.get('contact', 'N/A')}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eaeaea; color: #666;">{member.get('email', 'N/A')}</td>
                </tr>
                """
            
            # Generate requirements list HTML
            requirements_html = ""
            for req in homepage_config.get('requirements', []):
                requirements_html += f'<li style="margin-bottom: 8px; display: flex; align-items: center; gap: 8px;"><i class="fas fa-check-circle" style="color: #28a745; font-size: 14px;"></i> <span style="color: #666;">{req}</span></li>'
            
            # Payment status HTML
            payment_html = ""
            if hackathon_config.get('payment_required', True):
                payment_status = "Verified ✓" if team_data.get('payment_verified') else "Pending Verification ⏳"
                status_color = "#28a745" if team_data.get('payment_verified') else "#ffc107"
                payment_html = f"""
                <div style="background-color: #f8f9fa; border-radius: 10px; padding: 20px; margin: 20px 0; border-left: 4px solid {status_color};">
                    <h3 style="margin: 0 0 15px 0; font-size: 1.1rem; color: #1a1a1a;">
                        <i class="fas fa-credit-card" style="color: #c41e3a; margin-right: 8px;"></i>Payment Status
                    </h3>
                    <div style="display: flex; flex-wrap: wrap; gap: 15px;">
                        <div style="flex: 1;">
                            <div style="color: #666; font-size: 0.9rem;">Status</div>
                            <div style="font-weight: 600; color: {status_color};">{payment_status}</div>
                        </div>
                        {f'<div style="flex: 1;"><div style="color: #666; font-size: 0.9rem;">Method</div><div style="font-weight: 600;">{team_data.get("payment_method", "N/A").title()}</div></div>' if team_data.get('payment_method') else ''}
                        {f'<div style="flex: 1;"><div style="color: #666; font-size: 0.9rem;">Amount</div><div style="font-weight: 600; color: #c41e3a;">₹{hackathon_config.get("registration_fee", 500)}</div></div>' if hackathon_config.get('payment_required') else ''}
                    </div>
                </div>
                """
            
            # HTML email content with modern responsive design
            html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>Registration Confirmed - {event_name}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        /* Reset styles */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }}
        
        body {{
            background-color: #f4f7fc;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}
        
        /* Main container */
        .email-wrapper {{
            max-width: 600px;
            margin: 20px auto;
            background-color: #ffffff;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 20px 40px rgba(0,0,0,0.08);
        }}
        
        /* Header section */
        .email-header {{
            background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
            padding: 30px 20px;
            text-align: center;
            border-bottom: 4px solid #c41e3a;
        }}
        
        .logo-container {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        
        .logo {{
            width: auto;
            height: 60px;
            object-fit: contain;
            filter: drop-shadow(0 4px 6px rgba(0,0,0,0.2));
        }}
        
        .club-badge {{
            background: #c41e3a;
            color: white;
            padding: 8px 20px;
            border-radius: 40px;
            font-size: 1rem;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 10px;
        }}
        
        .email-title {{
            font-size: 32px;
            font-weight: 700;
            color: white;
            margin: 10px 0 5px;
            letter-spacing: -0.5px;
            line-height: 1.2;
        }}
        
        .event-name {{
            color: #c41e3a;
            font-size: 24px;
            font-weight: 600;
            margin: 5px 0;
        }}
        
        .email-subtitle {{
            color: rgba(255,255,255,0.9);
            font-size: 16px;
            max-width: 400px;
            margin: 10px auto 0;
        }}
        
        /* Content area */
        .email-content {{
            padding: 30px 25px;
        }}
        
        /* Success banner */
        .success-banner {{
            background: linear-gradient(135deg, #c41e3a 0%, #a01830 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            margin-bottom: 25px;
            text-align: center;
            box-shadow: 0 8px 16px rgba(196,30,58,0.2);
        }}
        
        .success-banner i {{
            font-size: 48px;
            margin-bottom: 10px;
        }}
        
        .success-banner h2 {{
            font-size: 24px;
            margin: 10px 0;
            font-weight: 700;
        }}
        
        /* Section styling */
        .section {{
            background: #ffffff;
            border-radius: 12px;
            margin-bottom: 25px;
            border: 1px solid #eaeaea;
            overflow: hidden;
        }}
        
        .section-header {{
            background: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid #eaeaea;
        }}
        
        .section-header h3 {{
            margin: 0;
            font-size: 18px;
            font-weight: 600;
            color: #1a1a1a;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .section-header h3 i {{
            color: #c41e3a;
            font-size: 20px;
        }}
        
        .section-body {{
            padding: 20px;
        }}
        
        /* Event details grid */
        .event-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}
        
        .event-item {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
        }}
        
        .event-item.full-width {{
            grid-column: 1 / -1;
        }}
        
        .event-item .label {{
            color: #666;
            font-size: 0.85rem;
            margin-bottom: 5px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .event-item .value {{
            font-weight: 600;
            color: #1a1a1a;
            font-size: 1.1rem;
        }}
        
        /* About event */
        .about-event {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-top: 15px;
        }}
        
        .about-event p {{
            color: #666;
            line-height: 1.6;
        }}
        
        .about-event b {{
            color: #c41e3a;
        }}
        
        /* Requirements list */
        .requirements-list {{
            list-style: none;
            padding: 0;
        }}
        
        .requirements-list li {{
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        /* Team info */
        .team-id-card {{
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            border: 2px dashed #c41e3a;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 20px;
            text-align: center;
        }}
        
        .team-id-card .label {{
            color: #666;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .team-id-card .id {{
            font-size: 24px;
            font-weight: 700;
            color: #c41e3a;
            font-family: monospace;
            margin: 5px 0;
        }}
        
        .team-id-card .name {{
            font-size: 20px;
            font-weight: 600;
            color: #1a1a1a;
        }}
        
        /* Members table */
        .members-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .members-table th {{
            background: #f8f9fa;
            padding: 10px;
            font-size: 0.85rem;
            font-weight: 600;
            color: #666;
            text-align: left;
            border-bottom: 2px solid #eaeaea;
        }}
        
        /* QR Code section */
        .qr-section {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 25px;
            margin: 25px 0;
            text-align: center;
            border: 2px dashed #c41e3a;
        }}
        
        .qr-section h3 {{
            color: #1a1a1a;
            margin-bottom: 15px;
            font-size: 18px;
        }}
        
        .qr-code {{
            max-width: 200px;
            width: 100%;
            height: auto;
            margin: 15px auto;
            display: block;
            border-radius: 12px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.1);
            border: 3px solid white;
        }}
        
        .qr-instruction {{
            color: #666;
            font-size: 14px;
            line-height: 1.6;
            max-width: 300px;
            margin: 15px auto 0;
        }}
        
        .qr-instruction i {{
            color: #c41e3a;
            margin-right: 5px;
        }}
        
        /* Next steps */
        .steps-list {{
            list-style: none;
            padding: 0;
        }}
        
        .steps-list li {{
            padding: 12px 0;
            border-bottom: 1px solid #eaeaea;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .steps-list li:last-child {{
            border-bottom: none;
        }}
        
        .steps-list .step-number {{
            width: 28px;
            height: 28px;
            background: #c41e3a;
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 14px;
            flex-shrink: 0;
        }}
        
        /* Footer */
        .email-footer {{
            background: #1a1a1a;
            padding: 30px 20px;
            color: white;
            text-align: center;
        }}
        
        .footer-logos {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 30px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        
        .footer-logo {{
            height: 50px;
            width: auto;
            object-fit: contain;
            filter: brightness(0) invert(1);
        }}
        
        .club-info {{
            margin: 20px 0;
        }}
        
        .club-info h4 {{
            font-size: 18px;
            margin-bottom: 10px;
            color: white;
        }}
        
        .contact-grid {{
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
            margin: 20px 0;
        }}
        
        .contact-link {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: white;
            text-decoration: none;
            padding: 8px 16px;
            background: rgba(255,255,255,0.1);
            border-radius: 40px;
            transition: all 0.3s ease;
        }}
        
        .contact-link:hover {{
            background: #c41e3a;
            color: white;
        }}
        
        .copyright {{
            color: #999;
            font-size: 13px;
            margin-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.1);
            padding-top: 20px;
        }}
        
        /* Developer credit */
        .developer-credit {{
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0 10px;
        }}
        
        .developer-credit p {{
            color: #ccc;
            font-size: 13px;
        }}
        
        .developer-credit strong {{
            color: #c41e3a;
        }}
        
        /* Responsive styles */
        @media only screen and (max-width: 480px) {{
            .email-content {{
                padding: 20px 15px;
            }}
            
            .event-grid {{
                grid-template-columns: 1fr;
            }}
            
            .logo-container {{
                gap: 10px;
            }}
            
            .logo {{
                height: 50px;
            }}
            
            .email-title {{
                font-size: 28px;
            }}
            
            .event-name {{
                font-size: 20px;
            }}
            
            .team-id-card .id {{
                font-size: 20px;
            }}
            
            .team-id-card .name {{
                font-size: 18px;
            }}
            
            .members-table th,
            .members-table td {{
                padding: 8px;
                font-size: 13px;
            }}
            
            .contact-grid {{
                flex-direction: column;
                gap: 10px;
            }}
            
            .contact-link {{
                width: 100%;
                justify-content: center;
            }}
            
            .qr-code {{
                max-width: 150px;
            }}
        }}
        
        @media only screen and (max-width: 360px) {{
            .members-table {{
                display: block;
                overflow-x: auto;
                white-space: nowrap;
            }}
            
            .step-number {{
                width: 24px;
                height: 24px;
                font-size: 12px;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <!-- Header -->
        <div class="email-header">
            <table align="center" border="0" cellpadding="0" cellspacing="0" style="margin: 0 auto 20px auto; text-align: center;">
                <tr>
                    <td style="padding: 0 10px; vertical-align: middle;">
                        <img src="{college_logo_src}" alt="College Logo" style="height: 60px; max-height: 60px; width: auto; display: block; border: 0;">
                    </td>
                    <td style="padding: 0 10px; vertical-align: middle;">
                        <img src="{club_logo_src}" alt="Creators Club" style="height: 60px; max-height: 60px; width: auto; display: block; border: 0;">
                    </td>
                </tr>
            </table>
            <span class="club-badge">{event_name}</span>
            <h1 class="email-title">REGISTRATION</h1>
            <div class="event-name">CONFIRMED!</div>
            <div class="email-subtitle">Team {team_data['team_name']}</div>
        </div>
        
        <!-- Content -->
        <div class="email-content">
            <!-- Success Banner -->
            <div class="success-banner">
                <i class="fas fa-check-circle"></i>
                <h2>Thank You for Registering!</h2>
                <p style="opacity: 0.9; font-size: 15px;">Your team has been successfully registered for {event_name}</p>
            </div>
            
            <!-- Event Details -->
            <div class="section">
                <div class="section-header">
                    <h3><i class="fas fa-calendar-alt"></i> Event Details</h3>
                </div>
                <div class="section-body">
                    <div class="event-grid">
                        <div class="event-item">
                            <div class="label">Event Name</div>
                            <div class="value">{homepage_config.get('hero_title', '36 Hours Ideathon Registration')}</div>
                        </div>
                        <div class="event-item">
                            <div class="label">Dates</div>
                            <div class="value">{homepage_config.get('event_date', 'March 06-07, 2026')}</div>
                        </div>
                        <div class="event-item">
                            <div class="label">Registration Deadline</div>
                            <div class="value">{homepage_config.get('registration_deadline', 'February 28, 2026')}</div>
                        </div>
                        <div class="event-item">
                            <div class="label">Venue</div>
                            <div class="value">{homepage_config.get('event_location', 'Sphoorthy Engineering College Campus')}</div>
                        </div>
                    </div>
                    
                    <!-- About Event -->
                    <div class="about-event">
                        <p>{homepage_config.get('about_event', 'Join us for an exciting competition where teams showcase their skills and compete for amazing prizes through challenges that test both technical and creative abilities.<br><b>Teams selected from the Ideathon will receive incubation support, mentorship, and potential funding opportunities to help turn their ideas into real-world solutions.</b>')}</p>
                    </div>
                </div>
            </div>
            
            <!-- Team Information -->
            <div class="section">
                <div class="section-header">
                    <h3><i class="fas fa-users"></i> Team Information</h3>
                </div>
                <div class="section-body">
                    <div class="team-id-card">
                        <div class="label">Team ID</div>
                        <div class="id">{team_data['team_id']}</div>
                        <div class="name">{team_data['team_name']}</div>
                        <div style="margin-top: 10px; color: #666;">
                        <i class="fas fa-user-friends" style="color: #c41e3a;"></i> {len(team_data['members'])} Members
                    </div>
                    </div>
                    
                    <h4 style="margin: 20px 0 10px; color: #1a1a1a; font-size: 16px;">Team Members</h4>
                    <table class="members-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Name & Branch</th>
                                <th>Contact</th>
                                <th>Email</th>
                            </tr>
                        </thead>
                        <tbody>
                            {members_html}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Payment Status -->
            {payment_html}
            
            <!-- QR Code Section - Displayed as Image NOT Attachment -->
            <div class="qr-section">
                <h3><i class="fas fa-qrcode" style="color: #c41e3a; margin-right: 8px;"></i> Your Event QR Code</h3>
                <p style="text-align: center; color: #555; margin-bottom: 15px; font-size: 14px;">
                    <i class="fas fa-info-circle" style="color: #c41e3a;"></i>
                    Your QR Code is attached below and has also been sent with this email.
                </p>
                <img src="cid:event_qr" alt="Event QR Code" class="qr-code">
                <div class="qr-instruction">
                    <i class="fas fa-info-circle"></i> 
                    <strong>Important:</strong> Present this QR code at the venue for:
                    <ul style="list-style: none; padding: 0; margin-top: 10px;">
                        <li>✓ Quick check-in</li>
                        <li>✓ Meal tracking (Breakfast, Lunch, Dinner)</li>
                        <li>✓ Session attendance</li>
                    </ul>
                    <p style="margin-top: 10px; font-size: 13px;">📱 Save this image on your phone or take a screenshot</p>
                </div>
            </div>
            
            <!-- Requirements -->
            <div class="section">
                <div class="section-header">
                    <h3><i class="fas fa-clipboard-list"></i> Important Requirements</h3>
                </div>
                <div class="section-body">
                    <ul class="requirements-list">
                        {requirements_html}
                    </ul>
                </div>
            </div>
            
            <!-- Next Steps -->
            <div class="section">
                <div class="section-header">
                    <h3><i class="fas fa-arrow-right"></i> Next Steps</h3>
                </div>
                <div class="section-body">
                    <ul class="steps-list">
                        <li>
                            <span class="step-number">1</span>
                            <span><strong>Save QR Code</strong> - Keep your QR code handy for entry</span>
                        </li>
                        <li>
                            <span class="step-number">2</span>
                            <span><strong>Check Email</strong> - Watch for event updates and schedule</span>
                        </li>
                        <li>
                            <span class="step-number">3</span>
                            <span><strong>Follow Social Media</strong> - Stay updated on announcements</span>
                        </li>
                        <li>
                            <span class="step-number">4</span>
                            <span><strong>Prepare for 36 Hours</strong> - Get ready for an exciting competition!</span>
                        </li>
                        {f'<li><span class="step-number">5</span><span><strong>Payment Verification</strong> - Your registration will be complete after payment verification</span></li>' if hackathon_config.get('payment_required', True) and not team_data.get('payment_verified') else ''}
                    </ul>
                </div>
            </div>
        </div>
        
        <!-- Footer -->
        <div class="email-footer">
            <table align="center" border="0" cellpadding="0" cellspacing="0" style="margin: 0 auto 20px auto; text-align: center;">
                <tr>
                    <td style="padding: 0 15px; vertical-align: middle;">
                        <img src="{college_logo_src}" alt="College Logo" style="height: 50px; max-height: 50px; width: auto; display: block; border: 0; filter: brightness(0) invert(1);">
                    </td>
                    <td style="padding: 0 15px; vertical-align: middle;">
                        <img src="{club_logo_src}" alt="Club Logo" style="height: 50px; max-height: 50px; width: auto; display: block; border: 0; filter: brightness(0) invert(1);">
                    </td>
                </tr>
            </table>
            
            <div class="club-info">
                <h4>Creator Club | Sphoorthy Engineering College</h4>
            </div>
            
            <div class="contact-grid">
                <a href="https://instagram.com/creator_club_official" target="_blank" class="contact-link">
                    <i class="fab fa-instagram"></i> Instagram
                </a>
                <a href="https://wa.me/919059160424" target="_blank" class="contact-link">
                    <i class="fab fa-whatsapp"></i> WhatsApp
                </a>
                <a href="mailto:creator_club@sphoorthyengg.ac.in" class="contact-link">
                    <i class="fas fa-envelope"></i> Email
                </a>
                <a href="tel:+919059160424" class="contact-link">
                    <i class="fas fa-phone"></i> Call
                </a>
            </div>
            
            <div class="copyright">
                &copy; {datetime.now().year} Creator Club, Sphoorthy Engineering College. All rights reserved.<br>
                <span style="font-size: 11px;">This is an automated message, please do not reply directly to this email.</span>
            </div>
        </div>
    </div>
</body>
</html>
            """
            
            # Plain text version
            payment_text = ""
            if hackathon_config.get('payment_required', True):
                payment_status = "Verified" if team_data.get('payment_verified') else "Pending Verification"
                payment_text = f"\nPAYMENT STATUS:\nStatus: {payment_status}"
                if team_data.get('payment_method'):
                    payment_text += f"\nMethod: {team_data.get('payment_method').title()}"
                if hackathon_config.get('registration_fee'):
                    payment_text += f"\nAmount: ₹{hackathon_config.get('registration_fee')}"
            
            requirements_text = "\nIMPORTANT REQUIREMENTS:\n"
            for req in homepage_config.get('requirements', []):
                requirements_text += f"✓ {req}\n"
            
            next_steps = "\nNEXT STEPS:\n1. Save QR Code - Keep your QR code handy for entry\n2. Check Email - Watch for event updates and schedule\n3. Follow Social Media - Stay updated on announcements\n4. Prepare for 36 Hours - Get ready for an exciting competition!"
            
            if hackathon_config.get('payment_required', True) and not team_data.get('payment_verified'):
                next_steps += "\n5. Payment Verification - Your registration will be complete after payment verification"
            
            members_text = ""
            for idx, member in enumerate(team_data['members'], 1):
                members_text += f"\n   {idx}. {member['name']} - {member.get('branch', 'N/A')} ({member.get('year', 'N/A')})\n      📞 {member.get('contact', 'N/A')} | ✉️ {member.get('email', 'N/A')}"
            
            text = f"""
╔══════════════════════════════════════════════════════════════╗
║               REGISTRATION CONFIRMED - Creator Club          ║
║{event_name.center(62)}║
╚══════════════════════════════════════════════════════════════╝

🎉 Thank You for Registering, Team {team_data['team_name']}!

════════════════════════════════════════════════════════════════
📋 EVENT DETAILS
════════════════════════════════════════════════════════════════
Event: {homepage_config.get('hero_title', '36 Hours Ideathon Registration')}
Dates: {homepage_config.get('event_date', 'March 06-07, 2026')}
Registration Deadline: {homepage_config.get('registration_deadline', 'February 28, 2026')}
Venue: {homepage_config.get('event_location', 'Sphoorthy Engineering College Campus')}

ABOUT THE EVENT:
{homepage_config.get('about_event', 'Join us for an exciting competition where teams showcase their skills and compete for amazing prizes.')}

════════════════════════════════════════════════════════════════
👥 TEAM INFORMATION
════════════════════════════════════════════════════════════════
Team ID: {team_data['team_id']}
Team Name: {team_data['team_name']}
Total Members: {len(team_data['members'])}

TEAM MEMBERS:{members_text}
{payment_text}
{requirements_text}
════════════════════════════════════════════════════════════════
📱 YOUR EVENT QR CODE
════════════════════════════════════════════════════════════════
A QR code image has been embedded in this email.
Please present it at the venue for:
• Quick check-in
• Meal tracking (Breakfast, Lunch, Dinner)
• Session attendance

💡 Save this image on your phone or take a screenshot
{next_steps}

════════════════════════════════════════════════════════════════
📞 CONTACT INFORMATION
════════════════════════════════════════════════════════════════
For any queries, contact:
Phone: +91 9059160424
Creator Club | Sphoorthy Engineering College
Instagram: @creator_club_official
Email: creator_club@sphoorthyengg.ac.in

© {datetime.now().year} Creator Club. All rights reserved.
This is an automated message, please do not reply directly to this email.
            """
            
            # Create message
            msg = Message(subject, recipients=[recipient_email])
            msg.body = text
            msg.html = html
            
            # Logos are now embedded as base64 data URIs directly in HTML — no attachment needed
            
            # Attach QR code as an inline image
            qr_img_data = base64.b64decode(qr_img_base64)
            msg.attach(
                filename=f"qr_code_team_{team_data['team_id']}.png",
                content_type="image/png",
                data=qr_img_data,
                disposition="inline",
                headers={"Content-ID": "<event_qr>"}
            )
            
            # Send email
            mail = app.extensions.get('mail')
            if mail:
                mail.send(msg)
                print(f"✓ Thank you email sent successfully to {recipient_email}")
                log_email(team_data['team_id'], 'thank_you_email', recipient_email, True)
            else:
                print("❌ Flask-Mail extension not initialized!")
                
        except Exception as e:
            print(f"❌ Failed to send thank you email to {recipient_email}: {e}")
            log_email(team_data['team_id'], 'thank_you_email', recipient_email, False, str(e))
            raise




def log_email(team_id, action, recipient_email, success=True, error=None, admin_id=None):
    """Log email sending attempts"""
    try:
        email_logs = []
        if os.path.exists(EMAIL_LOGS_FILE):
            with open(EMAIL_LOGS_FILE, 'r') as f:
                email_logs = json.load(f)
        
        log_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'team_id': team_id,
            'action': action,
            'recipient': recipient_email,
            'success': success,
            'error': error,
            'sent_by': admin_id or 'system'  # Use passed admin_id or default to 'system'
        }
        
        email_logs.append(log_entry)
        
        with open(EMAIL_LOGS_FILE, 'w') as f:
            json.dump(email_logs, f, indent=4)
    except Exception as e:
        print(f"Failed to log email: {str(e)}")
        
def generate_qr_code_image(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

      
def get_next_receipt_number():
    counter_file = Path(app.root_path) / 'receipt_counter.txt'
    
    try:
        with open(counter_file, 'r') as f:
            last_number = int(f.read().strip())
    except (FileNotFoundError, ValueError):
        last_number = 0
    
    next_number = last_number + 1
    
    with open(counter_file, 'w') as f:
        f.write(str(next_number))
    
    return next_number



@app.route('/')
def index():
    # Load homepage config
    config = get_homepage_config()
    
    # Load evaluation config to check if evaluation is enabled
    try:
        with open(EVALUATION_CONFIG_FILE, 'r') as f:
            eval_config = json.load(f)
            config['evaluation_enabled'] = eval_config.get('evaluation_enabled', False)
            config['submissions_enabled'] = eval_config.get('submissions_enabled', False)
    except:
        config['evaluation_enabled'] = False
        config['submissions_enabled'] = False
    
    return render_template('index.html', config=config)

@app.route('/check_team_name', methods=['POST'])
def check_team_name():
    team_name = request.json.get('team_name', '').strip().upper()
    if not team_name:
        return jsonify({'exists': False})
    
    # Check for existing team name in the JSON database
    existing_team = False
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r') as f:
            try:
                data = json.load(f)
                for team in data.get('teams', []):
                    if team.get('team_name', '').strip().upper() == team_name:
                        existing_team = True
                        break
            except Exception:
                pass

    return jsonify({'exists': existing_team})

@app.route('/check_member_details', methods=['POST'])
def check_member_details():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    contact = data.get('contact', '').strip()
    
    if not email and not contact:
        return jsonify({'error': 'No data provided'}), 400
    
    # Check database for existing details
    existing = {'email': False, 'contact': False}
    
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r') as f:
            try:
                db_data = json.load(f)
                for team in db_data.get('teams', []):
                    for member in team.get('members', []):
                        if email and member.get('email', '').lower() == email:
                            existing['email'] = True
                        if contact and member.get('contact', '') == contact:
                            existing['contact'] = True
            except Exception:
                pass
    
    return jsonify(existing)


# Add these new imports at the top
import pandas as pd
from werkzeug.utils import secure_filename
import hashlib

# Add these new constants
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}


import re
from datetime import datetime
import pandas as pd

def parse_dob(dob_value):
    """
    Parse various date formats and convert to DDMMYYYY
    Handles: 
    - Excel serial dates (like 44678)
    - DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    - YYYY-MM-DD, YYYY/MM/DD
    - DDMMYYYY (8 digits)
    - Mixed formats with text
    """
    if pd.isna(dob_value):
        return None
    
    # If it's a number (Excel serial date)
    if isinstance(dob_value, (int, float)) and not pd.isna(dob_value):
        try:
            # Excel serial date (days since 1900-01-01)
            # Handle both integer and float
            excel_date = float(dob_value)
            if excel_date > 0:
                # Excel's epoch starts at 1900-01-01
                # Note: Excel incorrectly treats 1900 as leap year
                date_obj = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(excel_date) - 2)
                return date_obj.strftime('%d%m%Y')
        except Exception:
            pass
    
    dob_str = str(dob_value).strip()
    
    # If it's empty
    if not dob_str or dob_str.lower() in ['nan', 'null', 'none', '']:
        return None
    
    # Remove any non-digit characters for initial check
    digits_only = re.sub(r'\D', '', dob_str)
    
    # If we have 8 digits, it might already be in DDMMYYYY format
    if len(digits_only) == 8:
        # Validate if it's a plausible date
        try:
            day = int(digits_only[:2])
            month = int(digits_only[2:4])
            year = int(digits_only[4:])
            if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100:
                return digits_only
        except:
            pass
    
    # Try to parse as date with various formats
    date_formats = [
        '%d/%m/%Y',      # 15/02/2005
        '%d-%m-%Y',      # 15-02-2005
        '%d.%m.%Y',      # 15.02.2005
        '%d %m %Y',      # 15 02 2005
        '%Y-%m-%d',      # 2005-02-15
        '%Y/%m/%d',      # 2005/02/15
        '%Y.%m.%d',      # 2005.02.15
        '%m/%d/%Y',      # 02/15/2005 (US format)
        '%d/%m/%y',      # 15/02/05
        '%d-%m-%y',      # 15-02-05
        '%d.%m.%y',      # 15.02.05
        '%y-%m-%d',      # 05-02-15
        '%d%m%Y',        # 15022005
        '%d%m%y',        # 150205
        '%Y%m%d',        # 20050215
    ]
    
    for fmt in date_formats:
        try:
            date_obj = datetime.strptime(dob_str, fmt)
            # Convert to DDMMYYYY
            return date_obj.strftime('%d%m%Y')
        except ValueError:
            continue
    
    # If the string contains date-like patterns, try to extract
    # Look for patterns like DD/MM/YYYY or YYYY-MM-DD
    patterns = [
        r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})',  # DD/MM/YYYY or MM/DD/YYYY
        r'(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})',  # YYYY/MM/DD
        r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2})',   # DD/MM/YY
    ]
    
    for pattern in patterns:
        match = re.search(pattern, dob_str)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                try:
                    # Try to interpret as DD/MM/YYYY
                    if len(groups[2]) == 4:
                        day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                        if 1 <= day <= 31 and 1 <= month <= 12:
                            return f"{day:02d}{month:02d}{year}"
                    # Try to interpret as YYYY/MM/DD
                    elif len(groups[0]) == 4:
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        if 1 <= day <= 31 and 1 <= month <= 12:
                            return f"{day:02d}{month:02d}{year}"
                    # Try to interpret as DD/MM/YY
                    else:
                        day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                        year = 2000 + year if year < 100 else year
                        if 1 <= day <= 31 and 1 <= month <= 12:
                            return f"{day:02d}{month:02d}{year}"
                except:
                    pass
    
    # If we have digits only but not 8 digits, try to interpret
    if digits_only:
        # If it's 6 digits (DDMMYY)
        if len(digits_only) == 6:
            try:
                day = int(digits_only[:2])
                month = int(digits_only[2:4])
                year = int(digits_only[4:])
                # Assume 2000s for years < 100
                if year < 100:
                    year = 2000 + year if year < 50 else 1900 + year
                if 1 <= day <= 31 and 1 <= month <= 12:
                    return f"{day:02d}{month:02d}{year}"
            except:
                pass
        
        # If it's 7 digits, might be missing leading zero
        elif len(digits_only) == 7:
            # Try adding leading zero
            try:
                # Could be DDMYYYY or DMMYYYY
                for i in [1, 2]:
                    test = '0' + digits_only if i == 1 else digits_only[:1] + '0' + digits_only[1:]
                    if len(test) == 8:
                        day = int(test[:2])
                        month = int(test[2:4])
                        year = int(test[4:])
                        if 1 <= day <= 31 and 1 <= month <= 12:
                            return test
            except:
                pass
    
    return None

@app.route('/check-excel-format', methods=['POST'])
def check_excel_format():
    """Debug endpoint to check Excel file format"""
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        
        # Get info about each column
        info = {
            'columns': list(df.columns),
            'dtypes': {col: str(df[col].dtype) for col in df.columns},
            'sample': df.head(5).to_dict('records'),
            'dob_column': None,
            'dob_sample': []
        }
        
        # Try to identify DOB column
        for col in df.columns:
            col_lower = str(col).lower()
            if any(word in col_lower for word in ['dob', 'date', 'birth']):
                info['dob_column'] = col
                info['dob_sample'] = df[col].head(5).tolist()
                break
        
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'xlsx', 'xls', 'csv'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def initialize_student_database():
    """Initialize the student database file with correct structure"""
    STUDENT_DATABASE_FILE = 'data/students.json'
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Create the file with proper structure if it doesn't exist
    if not os.path.exists(STUDENT_DATABASE_FILE):
        with open(STUDENT_DATABASE_FILE, 'w') as f:
            json.dump({'students': []}, f, indent=4)
        print(f"✅ Created {STUDENT_DATABASE_FILE} with correct structure")
    else:
        # Check if existing file has correct structure
        try:
            with open(STUDENT_DATABASE_FILE, 'r') as f:
                data = json.load(f)
            
            # If the file doesn't have the 'students' key, fix it
            if 'students' not in data:
                # Try to recover existing data
                if isinstance(data, list):
                    # If it's a list, move it to students key
                    corrected_data = {'students': data}
                elif isinstance(data, dict) and len(data) > 0:
                    # If it's a dict but missing students key, wrap it
                    corrected_data = {'students': [data]}
                else:
                    # Default empty structure
                    corrected_data = {'students': []}
                
                # Save corrected structure
                with open(STUDENT_DATABASE_FILE, 'w') as f:
                    json.dump(corrected_data, f, indent=4)
                print(f"✅ Fixed structure in {STUDENT_DATABASE_FILE}")
        except json.JSONDecodeError:
            # File is corrupted, create new one
            with open(STUDENT_DATABASE_FILE, 'w') as f:
                json.dump({'students': []}, f, indent=4)
            print(f"✅ Recreated corrupted {STUDENT_DATABASE_FILE}")


# Call this in initialize_files()
initialize_files()  # Add this line inside initialize_files() function

@app.route('/admin/upload-students', methods=['GET', 'POST'])
def upload_students():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    STUDENT_DATABASE_FILE = 'data/students.json'
    
    # Ensure the database exists with correct structure
    initialize_student_database()
    
    if request.method == 'POST':
        # Check if it's a file upload
        if 'student_file' in request.files and request.files['student_file'].filename != '':
            # Handle file upload
            file = request.files['student_file']
            if file and allowed_file(file.filename):
                try:
                    # Read the file
                    if file.filename.endswith('.csv'):
                        df = pd.read_csv(file)
                    else:
                        df = pd.read_excel(file)
                    
                    # Debug: Print column names and first few rows to console
                    print("\n" + "="*50)
                    print("📊 FILE UPLOAD DEBUG INFO")
                    print("="*50)
                    print("Columns:", list(df.columns))
                    print("\nFirst 5 rows:")
                    print(df.head())
                    print("="*50 + "\n")
                    
                    # Normalize column names to lowercase for case-insensitive matching
                    df.columns = [str(col).strip().lower() for col in df.columns]
                    
                    # Try to identify the DOB column
                    dob_column = None
                    possible_dob_names = [
                        'dob', 'date of birth', 'birth date', 'birthdate', 
                        'd.o.b', 'date_of_birth', 'birth', 'dateofbirth',
                        'dob.', 'birth.day', 'birth_date'
                    ]
                    
                    for possible_name in possible_dob_names:
                        if possible_name in df.columns:
                            dob_column = possible_name
                            print(f"✅ Found DOB column: '{dob_column}'")
                            break
                    
                    if not dob_column:
                        # Try fuzzy matching - find any column containing 'dob' or 'date' or 'birth'
                        for col in df.columns:
                            col_lower = col.lower()
                            if any(word in col_lower for word in ['dob', 'date', 'birth']):
                                dob_column = col
                                print(f"✅ Found possible DOB column (fuzzy match): '{dob_column}'")
                                break
                    
                    if not dob_column:
                        flash('❌ Could not find DOB column in file. Expected column names: dob, date of birth, birth date', 'error')
                        return redirect(url_for('upload_students'))
                    
                    # Load existing students with proper error handling
                    if os.path.exists(STUDENT_DATABASE_FILE):
                        try:
                            with open(STUDENT_DATABASE_FILE, 'r') as f:
                                student_data = json.load(f)
                                # Ensure the structure is correct
                                if not isinstance(student_data, dict) or 'students' not in student_data:
                                    student_data = {'students': []}
                        except json.JSONDecodeError:
                            student_data = {'students': []}
                    else:
                        student_data = {'students': []}
                    
                    students_added = 0
                    errors = []
                    
                    # Process each row
                    for index, row in df.iterrows():
                        try:
                            # Get roll number from various possible column names
                            rollno = ''
                            for col in ['rollno', 'roll number', 'roll', 'roll_no', 'roll_num', 'roll.no', 'rollno.', 'roll num']:
                                if col in df.columns and pd.notna(row[col]):
                                    rollno = str(row[col]).strip().upper()
                                    break
                            
                            # Get name from various possible column names
                            name = ''
                            for col in ['name', 'student name', 'studentname', 'full name', 'student_name', 'student', 'fullname']:
                                if col in df.columns and pd.notna(row[col]):
                                    name = str(row[col]).strip().title()
                                    break
                            
                            # Get branch from various possible column names
                            branch = ''
                            for col in ['branch', 'department', 'dept', 'branch name', 'dept name', 'department_name']:
                                if col in df.columns and pd.notna(row[col]):
                                    branch = str(row[col]).strip()
                                    break
                            
                            # Get year from various possible column names
                            year = ''
                            for col in ['year', 'year of study', 'study year', 'academic year', 'year_of_study', 'year study']:
                                if col in df.columns and pd.notna(row[col]):
                                    year = str(row[col]).strip()
                                    break
                            
                            # Get DOB value
                            dob_raw = row[dob_column]
                            
                            # Debug print for DOB values
                            print(f"Row {index + 2}: Raw DOB value = '{dob_raw}' (type: {type(dob_raw).__name__})")
                            
                            # Parse DOB
                            dob = parse_dob(dob_raw)
                            
                            if dob:
                                print(f"Row {index + 2}: Parsed DOB = '{dob}' ✓")
                            else:
                                print(f"Row {index + 2}: Parsed DOB = FAILED ✗")
                            
                            # Get section from various possible column names
                            section = ''
                            for col in ['section', 'sec', 'class', 'division', 'section_name', 'batch']:
                                if col in df.columns and pd.notna(row[col]):
                                    section = str(row[col]).strip().upper()
                                    break
                            
                            # Validate required fields
                            if not rollno:
                                errors.append(f"Row {index + 2}: Missing Roll Number")
                                continue
                            
                            if not name:
                                errors.append(f"Row {index + 2}: Missing Name for {rollno}")
                                continue
                            
                            if not branch:
                                errors.append(f"Row {index + 2}: Missing Branch for {rollno}")
                                continue
                            
                            if not year:
                                errors.append(f"Row {index + 2}: Missing Year for {rollno}")
                                continue
                            
                            if not dob:
                                errors.append(f"Row {index + 2}: Invalid DOB format for {rollno}. Raw value: '{dob_raw}'")
                                continue
                            
                            # Check duplicate
                            if any(s.get('rollno') == rollno for s in student_data['students']):
                                errors.append(f"Row {index + 2}: Student {rollno} already exists")
                                continue
                            
                            # Add student
                            new_student = {
                                'rollno': rollno,
                                'name': name,
                                'branch': branch,
                                'year': year,
                                'section': section,
                                'dob': dob,
                                'registered': False,
                                'registration_date': None,
                                'team_id': None
                            }
                            
                            student_data['students'].append(new_student)
                            students_added += 1
                            
                        except Exception as e:
                            errors.append(f"Row {index + 2}: {str(e)}")
                    
                    # Save if any students were added
                    if students_added > 0:
                        with open(STUDENT_DATABASE_FILE, 'w') as f:
                            json.dump(student_data, f, indent=4)
                        flash(f'✅ Successfully added {students_added} students!', 'success')
                    else:
                        flash('⚠️ No students were added. Please check your file format.', 'warning')
                    
                    if errors:
                        # Show first 5 errors
                        error_msg = '; '.join(errors[:5])
                        if len(errors) > 5:
                            error_msg += f' and {len(errors) - 5} more errors'
                        flash(f'⚠️ Errors: {error_msg}', 'warning')
                    
                except Exception as e:
                    flash(f'❌ Error processing file: {str(e)}', 'error')
                    print(f"File processing error: {str(e)}")
                
                return redirect(url_for('upload_students'))
        
        # Handle single student entry
        elif request.form.get('form_type') == 'single':
            try:
                # Get form data
                roll_number = request.form.get('roll_number', '').strip().upper()
                name = request.form.get('name', '').strip().title()
                year = request.form.get('year', '').strip()
                branch = request.form.get('branch', '').strip()
                section = request.form.get('section', '').strip().upper()
                dob = request.form.get('password', '').strip()
                
                # Validate required fields
                if not all([roll_number, name, year, branch, dob]):
                    flash('❌ All required fields must be filled', 'error')
                    return redirect(url_for('upload_students'))
                
                # Parse DOB
                parsed_dob = parse_dob(dob)
                if not parsed_dob:
                    flash('❌ Invalid date format. Please use DDMMYYYY (e.g., 15022005) or DD/MM/YYYY format', 'error')
                    return redirect(url_for('upload_students'))
                
                # Load existing students with proper error handling
                if os.path.exists(STUDENT_DATABASE_FILE):
                    try:
                        with open(STUDENT_DATABASE_FILE, 'r') as f:
                            student_data = json.load(f)
                            # Ensure the structure is correct
                            if not isinstance(student_data, dict) or 'students' not in student_data:
                                student_data = {'students': []}
                    except json.JSONDecodeError:
                        student_data = {'students': []}
                else:
                    student_data = {'students': []}
                
                # Check for duplicate roll number
                if any(s.get('rollno') == roll_number for s in student_data['students']):
                    flash(f'❌ Student with roll number {roll_number} already exists', 'error')
                    return redirect(url_for('upload_students'))
                
                # Create new student
                new_student = {
                    'rollno': roll_number,
                    'name': name,
                    'branch': branch,
                    'year': year,
                    'section': section,
                    'dob': parsed_dob,
                    'registered': False,
                    'registration_date': None,
                    'team_id': None
                }
                
                # Add to list
                student_data['students'].append(new_student)
                
                # Save to file
                with open(STUDENT_DATABASE_FILE, 'w') as f:
                    json.dump(student_data, f, indent=4)
                
                flash(f'✅ Student {name} added successfully!', 'success')
                return redirect(url_for('upload_students'))
                
            except Exception as e:
                flash(f'❌ Error adding student: {str(e)}', 'error')
                return redirect(url_for('upload_students'))
        
        # Handle batch entry
        elif request.form.get('form_type') == 'batch':
            try:
                batch_data = request.form.get('batch_data', '').strip()
                if not batch_data:
                    flash('❌ No batch data provided', 'error')
                    return redirect(url_for('upload_students'))
                
                # Load existing students with proper error handling
                if os.path.exists(STUDENT_DATABASE_FILE):
                    try:
                        with open(STUDENT_DATABASE_FILE, 'r') as f:
                            student_data = json.load(f)
                            # Ensure the structure is correct
                            if not isinstance(student_data, dict) or 'students' not in student_data:
                                student_data = {'students': []}
                    except json.JSONDecodeError:
                        student_data = {'students': []}
                else:
                    student_data = {'students': []}
                
                lines = batch_data.split('\n')
                students_added = 0
                errors = []
                
                for line_num, line in enumerate(lines, 1):
                    try:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        # Split by comma, but handle quoted values
                        parts = []
                        current = ''
                        in_quotes = False
                        for char in line:
                            if char == '"' and not in_quotes:
                                in_quotes = True
                            elif char == '"' and in_quotes:
                                in_quotes = False
                            elif char == ',' and not in_quotes:
                                parts.append(current.strip())
                                current = ''
                            else:
                                current += char
                        if current:
                            parts.append(current.strip())
                        
                        if len(parts) < 5:
                            errors.append(f'Line {line_num}: Insufficient fields (need at least 5)')
                            continue
                        
                        roll_number = parts[0].upper()
                        name = parts[1].title()
                        year = parts[2]
                        branch = parts[3]
                        dob_raw = parts[4]
                        section = parts[5] if len(parts) >= 6 else ''
                        
                        # Parse DOB
                        dob = parse_dob(dob_raw)
                        if not dob:
                            errors.append(f'Line {line_num}: Invalid DOB format for {roll_number}. Raw value: "{dob_raw}"')
                            continue
                        
                        # Check duplicate
                        if any(s.get('rollno') == roll_number for s in student_data['students']):
                            errors.append(f'Line {line_num}: Student {roll_number} already exists')
                            continue
                        
                        # Add student
                        new_student = {
                            'rollno': roll_number,
                            'name': name,
                            'branch': branch,
                            'year': year,
                            'section': section,
                            'dob': dob,
                            'registered': False,
                            'registration_date': None,
                            'team_id': None
                        }
                        
                        student_data['students'].append(new_student)
                        students_added += 1
                        
                    except Exception as e:
                        errors.append(f'Line {line_num}: {str(e)}')
                
                # Save if any students were added
                if students_added > 0:
                    with open(STUDENT_DATABASE_FILE, 'w') as f:
                        json.dump(student_data, f, indent=4)
                    flash(f'✅ Successfully added {students_added} students!', 'success')
                else:
                    flash('⚠️ No students were added. Please check your input format.', 'warning')
                
                if errors:
                    error_msg = '; '.join(errors[:5])
                    if len(errors) > 5:
                        error_msg += f' and {len(errors) - 5} more errors'
                    flash(f'⚠️ Errors: {error_msg}', 'warning')
                
                return redirect(url_for('upload_students'))
                
            except Exception as e:
                flash(f'❌ Error processing batch: {str(e)}', 'error')
                return redirect(url_for('upload_students'))
        
        else:
            flash('❌ Invalid form submission', 'error')
            return redirect(url_for('upload_students'))
    
    # GET request - show upload page with stats
    student_count = 0
    registered_count = 0
    try:
        if os.path.exists(STUDENT_DATABASE_FILE):
            with open(STUDENT_DATABASE_FILE, 'r') as f:
                student_data = json.load(f)
                # Handle both possible structures
                if isinstance(student_data, dict) and 'students' in student_data:
                    student_count = len(student_data.get('students', []))
                    registered_count = sum(1 for s in student_data.get('students', []) if s.get('registered'))
                elif isinstance(student_data, list):
                    # If it's a list, convert it to proper structure
                    student_count = len(student_data)
                    registered_count = sum(1 for s in student_data if s.get('registered'))
    except Exception as e:
        print(f"Error loading student stats: {e}")
        pass
    
    return render_template('upload_students.html', 
                         student_count=student_count, 
                         registered_count=registered_count)


@app.route('/download-student-template')
def download_student_template():
    """Download a sample student template with correct format"""
    import pandas as pd
    from io import BytesIO
    
    # Create sample data
    data = {
        'rollno': ['23CS1001', '23EC2002', '22ME3003', '24CS1004'],
        'name': ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown'],
        'branch': ['CSE', 'ECE', 'MECH', 'CSE'],
        'year': ['2', '2', '3', '1'],
        'dob': ['15022005', '22082005', '10112004', '18032006'],
        'section': ['A', 'B', 'C', 'A']
    }
    
    df = pd.DataFrame(data)
    
    # Create Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Students')
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='student_template.xlsx'
    )

@app.route('/check_student', methods=['POST'])
def check_student():
    """Verify student roll number (and DOB for Team Lead)"""
    try:
        data = request.get_json()
        rollno = data.get('rollno', '').strip().upper()
        current_member_index = int(data.get('member_index', 0))
        dob_input = data.get('dob', '').strip()  # Expected as YYYY-MM-DD from HTML date input

        if not rollno:
            return jsonify({'success': False, 'error': 'Roll number required'})

        # Team Lead (member 1) must also provide DOB
        if current_member_index == 1 and not dob_input:
            return jsonify({'success': False, 'error': 'Date of birth required for Team Lead verification'})

        # Check student database exists
        if not os.path.exists(STUDENT_DATABASE_FILE):
            return jsonify({'success': False, 'error': 'Student database not found'})

        # Check if already registered
        status, details = get_student_status(rollno)
        if status == 'REGISTERED':
            return jsonify({
                'success': False,
                'error': f"Already registered in team \"{details.get('team_name')}\" (ID: {details.get('team_id')})",
                'team_id': details.get('team_id'),
                'team_name': details.get('team_name')
            })

        # Verify student exists
        with open(STUDENT_DATABASE_FILE, 'r') as f:
            student_data = json.load(f)

        student = next((s for s in student_data.get('students', []) if s['rollno'].upper() == rollno), None)
        if not student:
            return jsonify({'success': False, 'error': 'Roll number not found'})

        # For Team Lead (member_index == 1), check DOB
        if current_member_index == 1:
            formatted_dob = dob_input
            try:
                parts = dob_input.split('-')
                if len(parts) == 3:
                    formatted_dob = f"{parts[2]}{parts[1]}{parts[0]}"
                else:
                    formatted_dob = dob_input.replace('-', '')
            except Exception:
                pass

            db_dob = student.get('dob', '').strip()
            if db_dob != formatted_dob:
                return jsonify({'success': False, 'error': 'Invalid date of birth'})

        return jsonify({
            'success': True,
            'student': {
                'name': student['name'],
                'branch': student['branch'],
                'year': student['year'],
                'section': student.get('section', ''),
                'rollno': student['rollno']
            }
        })

    except Exception as e:
        app.logger.error(f"Error in check_student: {e}")
        return jsonify({'success': False, 'error': str(e)})
    

@app.route('/retrieve-qr', methods=['GET', 'POST'])
def retrieve_qr():
    """Page for users to retrieve their lost QR code using roll number and DOB"""
    if request.method == 'POST':
        rollno = request.form.get('rollno', '').strip().upper()
        dob = request.form.get('dob', '').strip()
        
        if not rollno or not dob:
            flash('Please enter both Roll Number and Date of Birth', 'error')
            return render_template('retrieve_qr.html')
        
        # Parse DOB to standard format (DDMMYYYY)
        parsed_dob = parse_dob(dob)
        if not parsed_dob:
            flash('Invalid date format. Please use DDMMYYYY (e.g., 15022005) or DD/MM/YYYY', 'error')
            return render_template('retrieve_qr.html')
        
        # Search for the student in database
        student_found = None
        team_found = None
        
        try:
            # First, check if student exists in student database
            if os.path.exists(STUDENT_DATABASE_FILE):
                with open(STUDENT_DATABASE_FILE, 'r') as f:
                    student_data = json.load(f)
                    for student in student_data.get('students', []):
                        if student.get('rollno') == rollno and student.get('dob') == parsed_dob:
                            student_found = student
                            break
            
            if not student_found:
                flash('No student found with the provided Roll Number and Date of Birth', 'error')
                return render_template('retrieve_qr.html')
            
            # Check if student is registered in any team
            if os.path.exists(DATABASE_FILE):
                with open(DATABASE_FILE, 'r') as f:
                    data = json.load(f)
                    for team in data.get('teams', []):
                        for member in team.get('members', []):
                            if member.get('rollno') == rollno:
                                team_found = team
                                break
                        if team_found:
                            break
            
            if not team_found:
                flash('You are not registered in any team yet. Please register first.', 'error')
                return render_template('retrieve_qr.html')
            
            # Check if payment is verified (if required)
            try:
                with open(HACKATHON_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            except:
                config = {'payment_required': True}
            
            if config.get('payment_required', True) and not team_found.get('payment_verified'):
                flash('Your payment is not verified yet. QR code will be available after payment verification.', 'warning')
                return render_template('retrieve_qr.html')
            
            # Generate QR code for the team
            qr_data = {
                'team_id': team_found['team_id'],
                'team_name': team_found['team_name'],
                'members': [{'name': m['name'], 'id': m['id']} for m in team_found['members']]
            }
            
            qr_img = generate_qr_code_image(json.dumps(qr_data))
            qr_img_base64 = base64.b64encode(qr_img.getvalue()).decode('utf-8')
            
            # Also check if QR code file exists
            qr_file_path = f"static/qr_images/{team_found['team_id']}.png"
            qr_file_exists = os.path.exists(qr_file_path)
            
            return render_template('retrieve_qr.html', 
                                 show_result=True,
                                 success=True,
                                 team=team_found,
                                 student=student_found,
                                 qr_img=qr_img_base64,
                                 qr_file_path=qr_file_path if qr_file_exists else None,
                                 team_id=team_found['team_id'])
            
        except Exception as e:
            app.logger.error(f"Error in retrieve_qr: {str(e)}")
            flash('An error occurred while retrieving your QR code. Please try again later.', 'error')
            return render_template('retrieve_qr.html')
    
    # GET request
    return render_template('retrieve_qr.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Load hackathon config
    try:
        with open(HACKATHON_CONFIG_FILE, 'r') as f:
            config = json.load(f)
    except:
        config = {
            'payment_required': True, 
            'registration_open': True,
            'registration_fee': 500
        }
    
    # Check if registrations are open
    if not config.get('registration_open', True):
        message = config.get('registration_message', 'Registrations are currently closed. Please check back later.')
        return render_template('registration_closed.html', message=message)  
    
    if request.method == 'POST':
        # Get form data
        team_name = request.form.get('team_name', '').strip()
        if not team_name:
            flash('Team name is required', 'error')
            return redirect(url_for('register'))
        
        # Check duplicate members in the form data
        duplicate_members = check_duplicate_members_in_request(request.form)
        if duplicate_members:
            errors = {}
            for dup in duplicate_members:
                errors[f'member_{dup["member_index"]}_rollno'] = dup['message']
            
            flash('Duplicate member details found within the team', 'error')
            return render_template('register.html',
                branches=BRANCHES,
                years=YEARS,
                genders=['Male', 'Female', 'Other', 'Prefer not to say'],
                payment_required=config.get('payment_required', True),
                registration_fee=config.get('registration_fee', 500),
                form_data=request.form,
                errors=errors
            )

        members = []
        errors = {}
        
        # First pass to parse and validate details
        team_lead_roll = request.form.get('member_1_rollno', '').strip().upper()
        if not team_lead_roll:
            errors['member_1_rollno'] = 'Team Lead roll number is required'
            
        with db_transaction():
            # Check if team name already exists
            if os.path.exists(DATABASE_FILE):
                try:
                    with open(DATABASE_FILE, 'r') as f:
                        content = f.read().strip()
                        data = json.loads(content) if content else {'teams': []}
                        for team in data.get('teams', []):
                            if team.get('team_name', '').strip().upper() == team_name.upper():
                                errors['team_name'] = f'Team name "{team_name}" is already taken.'
                except Exception as e:
                    app.logger.error(f"Error checking team name: {e}")

            # Collect and validate each member slot (up to 4 members)
            for i in range(1, 5):
                rollno = request.form.get(f'member_{i}_rollno', '').strip().upper()
                if not rollno:
                    if i <= 3:  # First 3 members are required
                        errors[f'member_{i}_rollno'] = f'Roll number is required for member {i}'
                    continue
                
                # Check if already registered
                status, details = get_student_status(rollno)
                if status == 'REGISTERED':
                    errors[f'member_{i}_rollno'] = f'Roll number {rollno} is already registered in team "{details.get("team_name")}"'
                    continue
                
                # Verify student exists in students.json
                if not os.path.exists(STUDENT_DATABASE_FILE):
                    errors[f'member_{i}_rollno'] = 'Student database not found'
                    continue
                
                try:
                    with open(STUDENT_DATABASE_FILE, 'r') as f:
                        student_data = json.load(f)
                except json.JSONDecodeError:
                    errors[f'member_{i}_rollno'] = 'Student database is corrupted'
                    continue
                
                student = next((s for s in student_data.get('students', []) if s['rollno'] == rollno), None)
                if not student:
                    errors[f'member_{i}_rollno'] = f'Roll number {rollno} not found in database'
                    continue
                
                # Get email and contact
                email = request.form.get(f'member_{i}_email', '').strip().lower()
                contact = request.form.get(f'member_{i}_contact', '').strip()
                gender = request.form.get(f'member_{i}_gender', '')
                
                # Validate email and contact for first member
                if i == 1:
                    if not email:
                        errors['member_1_email'] = 'Email is required'
                    elif check_existing_values('email', email):
                        errors['member_1_email'] = 'Email already registered'
                    
                    if not contact:
                        errors['member_1_contact'] = 'Contact number is required'
                    elif check_existing_values('contact', contact):
                        errors['member_1_contact'] = 'Contact number already registered'
                else:
                    if email and check_existing_values('email', email):
                        errors[f'member_{i}_email'] = 'Email already registered'
                    if contact and check_existing_values('contact', contact):
                        errors[f'member_{i}_contact'] = 'Contact number already registered'
                
                member_data = {
                    'id': f"mem_{uuid.uuid4().hex[:8]}",
                    'rollno': student['rollno'],
                    'name': student['name'],
                    'branch': student['branch'],
                    'year': student['year'],
                    'section': student.get('section', ''),
                    'email': email,
                    'contact': contact,
                    'college': 'Sphoorthy Engineering College',
                    'gender': gender
                }
                members.append(member_data)
                
            # Validate team size
            if len(members) < 3:
                errors['team_size'] = 'You must have at least 3 team members'
                
            # If there are errors, return to form
            if errors:
                return render_template('register.html',
                    branches=BRANCHES,
                    years=YEARS,
                    genders=['Male', 'Female', 'Other', 'Prefer not to say'],
                    payment_required=config.get('payment_required', True),
                    registration_fee=config.get('registration_fee', 500),
                    form_data=request.form,
                    errors=errors
                )
            
            try:
                # Generate team number
                team_number = generate_team_number()
                
                team_data = {
                    'team_id': team_number,
                    'team_name': team_name,
                    'members': members,
                    'gender': members[0].get('gender'),
                    'registration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'payment_verified': False,
                    'payment_id': None,
                    'payment_method': None,
                    'payment_date': None,
                    'registration_complete': False
                }
                
                # Save to database.json
                if os.path.exists(DATABASE_FILE):
                    try:
                        with open(DATABASE_FILE, 'r') as f:
                            content = f.read().strip()
                            data = json.loads(content) if content else {'teams': []}
                    except json.JSONDecodeError:
                        data = {'teams': []}
                else:
                    data = {'teams': []}
                
                if 'teams' not in data:
                    data['teams'] = []
                data['teams'].append(team_data)
                
                with open(DATABASE_FILE, 'w') as f:
                    json.dump(data, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())
                    
                # Update student database students.json
                if os.path.exists(STUDENT_DATABASE_FILE):
                    try:
                        with open(STUDENT_DATABASE_FILE, 'r') as sf:
                            content = sf.read().strip()
                            student_data = json.loads(content) if content else {'students': []}
                    except json.JSONDecodeError:
                        student_data = {'students': []}
                        
                    if 'students' not in student_data:
                        student_data['students'] = []
                        
                    updated = False
                    for member in members:
                        for student in student_data['students']:
                            if student['rollno'].upper() == member['rollno'].upper():
                                student['registered'] = True
                                student['registration_date'] = team_data['registration_date']
                                student['team_id'] = team_number
                                updated = True
                                break
                    if updated:
                        with open(STUDENT_DATABASE_FILE, 'w') as sf:
                            json.dump(student_data, sf, indent=4)
                            sf.flush()
                            os.fsync(sf.fileno())
                            
                # (Reservation cleanup removed — no reservation system)
                        
                # Generate QR code
                qr_data = {
                    'team_id': team_number,
                    'team_name': team_data['team_name'],
                    'members': [{'name': m['name'], 'id': m['id']} for m in team_data['members']]
                }
                
                qr_img = generate_qr_code_image(json.dumps(qr_data))
                qr_img_base64 = base64.b64encode(qr_img.getvalue()).decode('utf-8')
                
                # Save QR code as file
                qr_filename = f"static/qr_images/{team_number}.png"
                with open(qr_filename, 'wb') as f:
                    f.write(qr_img.getvalue())
                
                # Check if payment is required
                if not config.get('payment_required', True):
                    # Payment not required - mark as verified
                    team_data['payment_verified'] = True
                    team_data['payment_method'] = 'free'
                    team_data['payment_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    team_data['registration_complete'] = True
                    
                    # Update database and registrations with payment info
                    update_team_payment_status(team_number, True, 'free')
                    
                    # Send confirmation emails
                    for member in team_data['members']:
                        if member.get('email'):
                            try:
                                threading.Thread(
                                    target=send_thank_you_email,
                                    args=(member['email'], team_data, qr_img_base64)
                                ).start()
                            except Exception as e:
                                app.logger.error(f"Failed to start email thread: {str(e)}")
                    
                    session.pop('team_data', None)
                    return render_template(
                        'success.html', 
                        team=team_data, 
                        qr_img=qr_img_base64,
                        team_number=team_number
                    )
                else:
                    # Payment required - store in session and redirect to payment
                    session['team_data'] = team_data
                    return redirect(url_for('payment'))
                    
            except Exception as e:
                app.logger.error(f"Error saving team: {str(e)}")
                app.logger.exception("Full traceback:")
                flash('Error creating team. Please try again.', 'error')
                return redirect(url_for('register'))
    
    # GET request - show registration form
    return render_template('register.html', 
                         branches=BRANCHES, 
                         years=YEARS, 
                         genders=['Male', 'Female', 'Other', 'Prefer not to say'],
                         payment_required=config.get('payment_required', True),
                         registration_fee=config.get('registration_fee', 500))



# Add this function to check for duplicate team members within the same registration
def check_duplicate_members_in_request(form_data):
    """Check if any member details are duplicated within the same registration request"""
    members = []
    duplicates = []
    
    for i in range(1, 5):  # Check up to 4 members
        rollno = form_data.get(f'member_{i}_rollno', '').strip().upper()
        
        if rollno:
            if rollno in members:
                duplicates.append({
                    'member_index': i,
                    'rollno': rollno,
                    'message': f'Member {i} has the same roll number as an earlier member'
                })
            else:
                members.append(rollno)
    
    return duplicates


def generate_team_number(with_retry=False):
    """
    Generate a unique team number with format:
    CC60326XXX where:
    - CC60326 = Fixed constant prefix
    - XXX = Sequential number (001-999)
    """
    from pathlib import Path
    import json
    from datetime import datetime
    
    # Fixed prefix (constant)
    fixed_prefix = "CC60326"
    
    # Track sequences
    counter_file = Path(app.root_path) / 'team_sequence_counter.json'
    
    # Load existing sequences
    try:
        with open(counter_file, 'r') as f:
            data = json.load(f)
            last_sequence = data.get('last_sequence', 0)
    except (FileNotFoundError, json.JSONDecodeError):
        last_sequence = 0
    
    # Get next sequence (increment)
    next_sequence = last_sequence + 1
    
    # Ensure sequence doesn't exceed 999
    if next_sequence > 999:
        # If we exceed 999, we need to handle this - either wrap around or extend
        # Option 1: Wrap around (but this could cause duplicates)
        # next_sequence = 1
        
        # Option 2: Extend to 4 digits (better)
        # This would make it CC60326001, CC60326002, etc. with 4 digits
        # For now, we'll just use 4 digits if needed
        pass
    
    # Save updated sequence
    with open(counter_file, 'w') as f:
        json.dump({'last_sequence': next_sequence}, f, indent=4)
    
    # Format sequence with leading zeros (3 digits)
    sequence_part = f"{next_sequence:03d}"
    
    # Combine fixed prefix with sequence
    team_number = f"{fixed_prefix}{sequence_part}"
    
    return team_number

def update_team_payment_status(team_id, verified, method):
    """Update team payment status in database and registrations file"""
    try:
        # Update in database.json
        with open(DATABASE_FILE, 'r+') as f:
            data = json.load(f)
            for team in data.get('teams', []):
                if team['team_id'] == team_id:
                    team['payment_verified'] = verified
                    team['payment_method'] = method
                    team['payment_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    team['registration_complete'] = verified
                    break
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()
        
        # (registrations.json removed - database.json is the single source of truth)
        
        return True
    except Exception as e:
        app.logger.error(f"Error updating payment status: {str(e)}")
        return False
         
def check_existing_values(field, value):
    """Check if a value already exists in the database for a specific field"""
    if not os.path.exists(DATABASE_FILE):
        return False
        
    try:
        with open(DATABASE_FILE, 'r') as f:
            data = json.load(f)
            for team in data.get('teams', []):
                for member in team.get('members', []):
                    if member.get(field, '').lower() == value.lower():
                        return True
    except Exception:
        pass
    return False


@app.route('/get_team_members/<team_id>')
def get_team_members(team_id):
    with open(DATABASE_FILE, 'r') as f:
        data = json.load(f)
        team = next((t for t in data['teams'] if t['team_id'] == team_id), None)
        if team:
            members = [{'id': m['id'], 'name': m['name']} for m in team['members']]
            return jsonify({'members': members})
    return jsonify({'members': []})


# Update this dictionary in your code
BRANCH_EMAILS = {
    "FRESHMAN": "hodhns@sphoorthyengg.ac.in",
    "CSE": "hodcse@sphoorthyengg.ac.in",
    "CSE(AIML)": "hodaiml@sphoorthyengg.ac.in",
    "CSE(DS)": "hodds@sphoorthyengg.ac.in",
    "CSE(CS)": "csdepartment62@gmail.com",
    "ECE": "morishettymadan10@gmail.com",
    "MECHANICAL": "morishettymadan10@gmail.com",
    "CIVIL": "hodcivil@sphoorthyengg.ac.in",
    "EEE": "hodeee@sphoorthyengg.ac.in",  # Add this if you have an email
    "ALL": "vsharath@sphoorthyengg.ac.in"
}

@app.route('/attendance')
def attendance_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    branch_filter = request.args.get('branch', 'all')
    
    # Load all teams data
    with open(DATABASE_FILE, 'r') as f:
        data = json.load(f)
        teams = data.get('teams', [])
    
    # Load scan logs
    with open(SCANNED_LOG_FILE, 'r') as f:
        scan_logs = json.load(f)
    
    # Process attendance data with rule numbers
    attendance_data = []
    for team in teams:
        for member in team['members']:
            # Skip if branch filter is set and doesn't match
            member_branch = member.get('branch', '').upper()
            if branch_filter != 'all' and member_branch != branch_filter:
                continue
                
            # Generate rule number (roll number + section if available)
            rule_number = member.get('rollno', '')
            if member.get('section'):
                rule_number += f" (Sec: {member['section']})"
                
            attendance_data.append({
                'team_id': team['team_id'],
                'team_name': team['team_name'],
                'member_id': member['id'],
                'member_name': member.get('name', ''),
                'email': member.get('email', ''),
                'contact': member.get('contact', ''),
                'college': member.get('college', ''),
                'branch': member_branch,
                'year': member.get('year', ''),
                'rule_number': rule_number,
                'entry_scans': 0,
                'breakfast_scans': 0,
                'lunch_scans': 0,
                'dinner_scans': 0,
                'last_scan_time': None
            })
    
    # Process scan logs to update attendance data
    for entry in scan_logs.get('entries', []):
        for i, member_id in enumerate(entry.get('members', [])):
            for attendee in attendance_data:
                if attendee['member_id'] == member_id and attendee['team_id'] == entry['team_id']:
                    attendee['entry_scans'] += 1
                    attendee['last_scan_time'] = entry['timestamp']
    
    for meal_type in ['breakfast', 'lunch', 'dinner']:
        for entry in scan_logs.get('food', {}).get(meal_type, []):
            for i, member_id in enumerate(entry.get('members', [])):
                for attendee in attendance_data:
                    if attendee['member_id'] == member_id and attendee['team_id'] == entry['team_id']:
                        if meal_type == 'breakfast':
                            attendee['breakfast_scans'] += 1
                        elif meal_type == 'lunch':
                            attendee['lunch_scans'] += 1
                        elif meal_type == 'dinner':
                            attendee['dinner_scans'] += 1
                        attendee['last_scan_time'] = entry['timestamp']
    
    # Sort by year, then by member name
    attendance_data.sort(key=lambda x: (x['year'], x['member_name']))
    
    # Calculate statistics
    total_participants = len(attendance_data)
    present_today = sum(1 for a in attendance_data if a['entry_scans'] > 0)
    breakfast_count = sum(1 for a in attendance_data if a['breakfast_scans'] > 0)
    lunch_count = sum(1 for a in attendance_data if a['lunch_scans'] > 0)
    dinner_count = sum(1 for a in attendance_data if a['dinner_scans'] > 0)
    
    # Create branch_emails dictionary from BRANCHES list (with placeholder emails)
    branch_emails = {"ALL": "vsharath@sphoorthyengg.ac.in"}
    for branch in BRANCHES:
        # You can set appropriate emails here or keep placeholders
        branch_emails[branch] = f"hod{branch.lower()}@sphoorthyengg.ac.in"
    
    return render_template('attendance_dashboard.html',
                         attendance_data=attendance_data,
                         total_participants=total_participants,
                         present_today=present_today,
                         breakfast_count=breakfast_count,
                         lunch_count=lunch_count,
                         dinner_count=dinner_count,
                         branch_filter=branch_filter,
                         branches=BRANCHES,  # Pass BRANCHES to template
                         branch_emails=branch_emails)

@app.route('/attendance/export', methods=['POST'])
def export_attendance():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    export_type = request.form.get('export_type', 'csv')
    message = request.form.get('message', '')
    branch = request.form.get('branch', 'all')
    
    # Get recipients - can be multiple
    recipients = request.form.getlist('recipients')
    categories = request.form.getlist('categories') or ['all']
    
    # Get attendance data
    with open(DATABASE_FILE, 'r') as f:
        data = json.load(f)
        teams = data.get('teams', [])
    
    with open(SCANNED_LOG_FILE, 'r') as f:
        scan_logs = json.load(f)
    
    # Process attendance data with filtering based on categories
    attendance_data = []
    for team in teams:
        for member in team['members']:
            if branch != 'all' and member.get('branch', '').lower() != branch:
                continue
                
            attendee = {
                'team_id': team['team_id'],
                'team_name': team['team_name'],
                'member_id': member['id'],
                'member_name': member['name'],
                'email': member['email'],
                'contact': member['contact'],
                'college': member.get('college', ''),
                'branch': member.get('branch', ''),
                'year': member.get('year', ''),
                'rule_number': member.get('rollno', '') + (f" (Sec: {member['section']})" if member.get('section') else ''),
                'entry_scans': 0,
                'breakfast_scans': 0,
                'lunch_scans': 0,
                'dinner_scans': 0,
                'last_scan_time': None
            }
            attendance_data.append(attendee)
    
    # Process scan logs
    for entry in scan_logs.get('entries', []):
        for i, member_id in enumerate(entry.get('members', [])):
            for attendee in attendance_data:
                if attendee['member_id'] == member_id and attendee['team_id'] == entry['team_id']:
                    attendee['entry_scans'] += 1
                    attendee['last_scan_time'] = entry['timestamp']
    
    for meal_type in ['breakfast', 'lunch', 'dinner']:
        for entry in scan_logs.get('food', {}).get(meal_type, []):
            for i, member_id in enumerate(entry.get('members', [])):
                for attendee in attendance_data:
                    if attendee['member_id'] == member_id and attendee['team_id'] == entry['team_id']:
                        if meal_type == 'breakfast':
                            attendee['breakfast_scans'] += 1
                        elif meal_type == 'lunch':
                            attendee['lunch_scans'] += 1
                        elif meal_type == 'dinner':
                            attendee['dinner_scans'] += 1
                        attendee['last_scan_time'] = entry['timestamp']
    
    # Filter data based on selected categories
    filtered_data = []
    if 'all' in categories:
        filtered_data = attendance_data
    else:
        for attendee in attendance_data:
            include = False
            if 'present' in categories and attendee['entry_scans'] > 0:
                include = True
            if 'absent' in categories and attendee['entry_scans'] == 0:
                include = True
            if 'meals' in categories and (attendee['breakfast_scans'] > 0 or 
                                        attendee['lunch_scans'] > 0 or 
                                        attendee['dinner_scans'] > 0):
                include = True
            if include:
                filtered_data.append(attendee)
    
    # Calculate statistics based on filtered data
    total_participants = len(filtered_data)
    present_today = sum(1 for a in filtered_data if a['entry_scans'] > 0)
    breakfast_count = sum(1 for a in filtered_data if a['breakfast_scans'] > 0)
    lunch_count = sum(1 for a in filtered_data if a['lunch_scans'] > 0)
    dinner_count = sum(1 for a in filtered_data if a['dinner_scans'] > 0)
    
    if export_type == 'csv':
        # Generate CSV with simplified Status column only
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Team ID', 'Team Name', 'Member ID', 'Member Name',
            'Email', 'Contact', 'College', 'Branch', 'Year', 'Roll Number',
            'Status'
        ])
        
        for attendee in filtered_data:
            # Present if ANY scan (entry, breakfast, lunch, or dinner) occurred
            is_present = (
                attendee['entry_scans'] > 0 or
                attendee['breakfast_scans'] > 0 or
                attendee['lunch_scans'] > 0 or
                attendee['dinner_scans'] > 0
            )
            status = 'Present' if is_present else 'Absent'
            writer.writerow([
                attendee['team_id'],
                attendee['team_name'],
                attendee['member_id'],
                attendee['member_name'],
                attendee['email'],
                attendee['contact'],
                attendee['college'],
                attendee['branch'],
                attendee['year'],
                attendee['rule_number'],
                status
            ])
        
        output.seek(0)
        
        if recipients:
            # Create the email content with enhanced styling
            subject = f"Attendance Report - {branch.upper()} Branch"
            if len(categories) == 1 and categories[0] != 'all':
                subject += f" ({categories[0].title()} Only)"
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <title>{subject}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f7fa;
            margin: 0;
            padding: 0;
        }}
        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        .email-header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 30px 20px;
            text-align: center;
            color: white;
        }}
        .logo-container {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            margin-bottom: 15px;
        }}
        .logo {{
            height: 50px;
            width: auto;
            object-fit: contain;
        }}
        .email-title {{
            font-size: 24px;
            font-weight: 700;
            margin: 10px 0;
            color: white;
        }}
        .email-body {{
            padding: 25px;
        }}
        .stats-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 25px;
        }}
        .stat-card {{
            flex: 1;
            min-width: 120px;
            background: #ffffff;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: 700;
            color: #1e3c72;
            margin: 5px 0;
        }}
        .stat-label {{
            font-size: 14px;
            color: #666;
        }}
        .highlight-card {{
            background: linear-gradient(135deg, #4b6cb7 0%, #182848 100%);
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 600;
            color: #1e3c72;
            margin: 20px 0 10px;
            padding-bottom: 5px;
            border-bottom: 2px solid #eaeaea;
        }}
        .email-footer {{
            background-color: #f5f7fa;
            padding: 20px;
            text-align: center;
            border-top: 1px solid #eaeaea;
            font-size: 12px;
            color: #666;
        }}
        .developer-info {{
            margin-top: 15px;
            font-style: italic;
            color: #444;
        }}
        .contact-info {{
            margin: 10px 0;
        }}
        .filter-list {{
            list-style-type: none;
            padding: 0;
            margin: 15px 0;
        }}
        .filter-list li {{
            display: inline-block;
            background-color: #e0e7ff;
            color: #1e3c72;
            padding: 5px 10px;
            border-radius: 15px;
            margin-right: 5px;
            margin-bottom: 5px;
            font-size: 14px;
        }}
        @media only screen and (max-width: 600px) {{
            .logo-container {{
                flex-direction: column;
            }}
            .stat-card {{
                min-width: calc(50% - 20px);
            }}
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="email-header">
            <div class="logo-container">
                <img src="https://res.cloudinary.com/dvfqvqbkn/image/upload/v1752482945/clglogo_rqnxum.png" alt="College Logo" class="logo">
                <img src="https://res.cloudinary.com/dvfqvqbkn/image/upload/v1752482876/cc_lbohfd.png" alt="Club Logo" class="logo">
            </div>
            <div class="email-title">ATTENDANCE REPORT</div>
            <div style="font-size: 16px;">{branch.upper()} Branch</div>
            {"<div style='font-size: 14px; margin-top: 5px;'>(Filtered: " + categories[0].title() + " Only)</div>" if len(categories) == 1 and categories[0] != 'all' else ''}
        </div>
        
        <div class="email-body">
            <div class="highlight-card">
                <div style="font-size: 18px; font-weight: 600; margin-bottom: 10px;">Attendance Summary</div>
                <div style="font-size: 14px;">Report generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}</div>
            </div>
            
            <div class="stats-container">
                <div class="stat-card">
                    <div class="stat-value">{total_participants}</div>
                    <div class="stat-label">Total Participants</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{present_today}</div>
                    <div class="stat-label">Present Today</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{breakfast_count}</div>
                    <div class="stat-label">Breakfast</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{lunch_count}</div>
                    <div class="stat-label">Lunch</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{dinner_count}</div>
                    <div class="stat-label">Dinner</div>
                </div>
            </div>
            
            <div class="section-title">Report Details</div>
            <p>Please find attached the detailed attendance report in CSV format.</p>
            
            {message and f'<div style="background-color: #f0f7ff; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #4b6cb7;">{message}</div>'}
            
            <div class="section-title">Filters Applied</div>
            <ul class="filter-list">
                {''.join(f'<li>{cat.title()}</li>' for cat in categories)}
            </ul>
        </div>
        
        <div class="email-footer">
            <div class="contact-info">
                <strong>Creators Club | Sphoorthy Engineering College</strong><br>
                <a href="mailto:creator_club@sphoorthyengg.ac.in" style="color: #1e3c72; text-decoration: none;">creator_club@sphoorthyengg.ac.in</a>
            </div>
            
            
            <div style="margin-top: 15px;">
                &copy; {datetime.now().year} Creators Club. All rights reserved.
            </div>
        </div>
    </div>
</body>
</html>
            """
            
            # Plain text version
            text_content = f"""
ATTENDANCE REPORT - {branch.upper()} BRANCH
{"(" + categories[0].upper() + " ONLY)" if len(categories) == 1 and categories[0] != 'all' else ''}

Summary:
- Total Participants: {total_participants}
- Present Today: {present_today}
- Breakfast: {breakfast_count}
- Lunch: {lunch_count}
- Dinner: {dinner_count}

Filters Applied: {', '.join(categories)}

Please find attached the detailed attendance report in CSV format.

{message if message else ''}

---
Creators Club | Sphoorthy Engineering College
Email: creator_club@sphoorthyengg.ac.in


© {datetime.now().year} Creators Club. All rights reserved.
            """
            
            # Create and send email to all recipients
            msg = Message(
                subject=subject,
                recipients=recipients,
                body=text_content,
                html=html_content
            )
            
            # Attach CSV
            msg.attach(
                f"attendance_report_{branch}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv",
                output.getvalue()
            )
            
            try:
                mail.send(msg)
                return jsonify({
                    'success': True, 
                    'message': f'Email sent to {len(recipients)} recipient(s)'
                })
            except Exception as e:
                return jsonify({
                    'success': False, 
                    'message': str(e)
                }), 500
        else:
            # Return CSV for download
            return Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={
                    "Content-Disposition": f"attachment;filename=attendance_report_{branch}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
                }
            )
    
    elif export_type == 'pdf':
        # Generate PDF with filtered data
        pdf = create_attendance_pdf(filtered_data, branch, categories)
        pdf_output = io.BytesIO()
        pdf_output.write(pdf.output(dest='S').encode('latin1'))
        pdf_output.seek(0)
        
        if recipients:
            # Create the email content with enhanced styling
            subject = f"Attendance Report - {branch.upper()} Branch"
            if len(categories) == 1 and categories[0] != 'all':
                subject += f" ({categories[0].title()} Only)"
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <title>{subject}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f7fa;
            margin: 0;
            padding: 0;
        }}
        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        .email-header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 30px 20px;
            text-align: center;
            color: white;
        }}
        .logo-container {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            margin-bottom: 15px;
        }}
        .logo {{
            height: 50px;
            width: auto;
            object-fit: contain;
        }}
        .email-title {{
            font-size: 24px;
            font-weight: 700;
            margin: 10px 0;
            color: white;
        }}
        .email-body {{
            padding: 25px;
        }}
        .stats-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 25px;
        }}
        .stat-card {{
            flex: 1;
            min-width: 120px;
            background: #ffffff;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: 700;
            color: #1e3c72;
            margin: 5px 0;
        }}
        .stat-label {{
            font-size: 14px;
            color: #666;
        }}
        .highlight-card {{
            background: linear-gradient(135deg, #4b6cb7 0%, #182848 100%);
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 600;
            color: #1e3c72;
            margin: 20px 0 10px;
            padding-bottom: 5px;
            border-bottom: 2px solid #eaeaea;
        }}
        .email-footer {{
            background-color: #f5f7fa;
            padding: 20px;
            text-align: center;
            border-top: 1px solid #eaeaea;
            font-size: 12px;
            color: #666;
        }}
        .developer-info {{
            margin-top: 15px;
            font-style: italic;
            color: #444;
        }}
        .contact-info {{
            margin: 10px 0;
        }}
        .filter-list {{
            list-style-type: none;
            padding: 0;
            margin: 15px 0;
        }}
        .filter-list li {{
            display: inline-block;
            background-color: #e0e7ff;
            color: #1e3c72;
            padding: 5px 10px;
            border-radius: 15px;
            margin-right: 5px;
            margin-bottom: 5px;
            font-size: 14px;
        }}
        @media only screen and (max-width: 600px) {{
            .logo-container {{
                flex-direction: column;
            }}
            .stat-card {{
                min-width: calc(50% - 20px);
            }}
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="email-header">
            <div class="logo-container">
                <img src="https://res.cloudinary.com/dvfqvqbkn/image/upload/v1752482945/clglogo_rqnxum.png" alt="College Logo" class="logo">
                <img src="https://res.cloudinary.com/dvfqvqbkn/image/upload/v1752482876/cc_lbohfd.png" alt="Club Logo" class="logo">
            </div>
            <div class="email-title">ATTENDANCE REPORT</div>
            <div style="font-size: 16px;">{branch.upper()} Branch</div>
            {"<div style='font-size: 14px; margin-top: 5px;'>(Filtered: " + categories[0].title() + " Only)</div>" if len(categories) == 1 and categories[0] != 'all' else ''}
        </div>
        
        <div class="email-body">
            <div class="highlight-card">
                <div style="font-size: 18px; font-weight: 600; margin-bottom: 10px;">Attendance Summary</div>
                <div style="font-size: 14px;">Report generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}</div>
            </div>
            
            <div class="stats-container">
                <div class="stat-card">
                    <div class="stat-value">{total_participants}</div>
                    <div class="stat-label">Total Participants</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{present_today}</div>
                    <div class="stat-label">Present Today</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{breakfast_count}</div>
                    <div class="stat-label">Breakfast</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{lunch_count}</div>
                    <div class="stat-label">Lunch</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{dinner_count}</div>
                    <div class="stat-label">Dinner</div>
                </div>
            </div>
            
            <div class="section-title">Report Details</div>
            <p>Please find attached the detailed attendance report in PDF format.</p>
            
            {message and f'<div style="background-color: #f0f7ff; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #4b6cb7;">{message}</div>'}
            
            <div class="section-title">Filters Applied</div>
            <ul class="filter-list">
                {''.join(f'<li>{cat.title()}</li>' for cat in categories)}
            </ul>
        </div>
        
        <div class="email-footer">
            <div class="contact-info">
                <strong>Creators Club | Sphoorthy Engineering College</strong><br>
                <a href="mailto:creator_club@sphoorthyengg.ac.in" style="color: #1e3c72; text-decoration: none;">creator_club@sphoorthyengg.ac.in</a>
            </div>
            
            
            <div style="margin-top: 15px;">
                &copy; {datetime.now().year} Creators Club. All rights reserved.
            </div>
        </div>
    </div>
</body>
</html>
            """
            
            # Plain text version
            text_content = f"""
ATTENDANCE REPORT - {branch.upper()} BRANCH
{"(" + categories[0].upper() + " ONLY)" if len(categories) == 1 and categories[0] != 'all' else ''}

Summary:
- Total Participants: {total_participants}
- Present Today: {present_today}
- Breakfast: {breakfast_count}
- Lunch: {lunch_count}
- Dinner: {dinner_count}

Filters Applied: {', '.join(categories)}

Please find attached the detailed attendance report in PDF format.

{message if message else ''}

---
Creators Club | Sphoorthy Engineering College
Email: creator_club@sphoorthyengg.ac.in


© {datetime.now().year} Creators Club. All rights reserved.
            """
            
            # Create and send email to all recipients
            msg = Message(
                subject=subject,
                recipients=recipients,
                body=text_content,
                html=html_content
            )
            
            # Attach PDF
            msg.attach(
                f"attendance_report_{branch}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                "application/pdf",
                pdf_output.getvalue()
            )
            
            try:
                mail.send(msg)
                return jsonify({
                    'success': True, 
                    'message': f'Email sent to {len(recipients)} recipient(s)'
                })
            except Exception as e:
                return jsonify({
                    'success': False, 
                    'message': str(e)
                }), 500
        else:
            # Return PDF for download
            return Response(
                pdf_output.getvalue(),
                mimetype='application/pdf',
                headers={
                    "Content-Disposition": f"attachment;filename=attendance_report_{branch}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                }
            )
    
    return jsonify({'success': False, 'message': 'Invalid export type'}), 400

def create_attendance_pdf(attendance_data, branch, logo_path=None):
    """Generate a PDF attendance report with responsive styling"""
    # First, load all teams data to get member details
    try:
        with open(DATABASE_FILE, 'r') as f:
            teams_data = json.load(f).get('teams', [])
    except:
        teams_data = []
    
    # Create a mapping of member details for quick lookup
    member_details = {}
    for team in teams_data:
        for member in team.get('members', []):
            member_key = f"{team['team_id']}_{member['id']}"
            member_details[member_key] = {
                'rollno': member.get('rollno', ''),
                'section': member.get('section', '')
            }
    
    # Enhance attendance data with rule numbers
    for attendee in attendance_data:
        member_key = f"{attendee['team_id']}_{attendee['member_id']}"
        details = member_details.get(member_key, {})
        rollno = details.get('rollno', '')
        section = details.get('section', '')
        
        # Create rule number text
        rule_number = rollno
        if section:
            rule_number += f" (Sec: {section})"
        attendee['rule_number'] = rule_number if rule_number else 'N/A'
    
    # Sort attendance data by year, then by member name
    attendance_data = sorted(attendance_data, key=lambda x: (
        x.get('year', ''),
        x.get('member_name', '')
    ))
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Set colors
    primary_color = (106, 27, 154)  # Purple
    secondary_color = (63, 81, 181)  # Indigo
    accent_color = (233, 30, 99)    # Pink
    dark_text = (33, 33, 33)        # Dark gray
    light_text = (117, 117, 117)    # Light gray
    
    # Header with logo - increased height
    header_height = 30  # Increased height for title
    pdf.set_fill_color(*primary_color)
    pdf.rect(0, 0, pdf.w, header_height, style='F')
    
    if logo_path:
        try:
            pdf.image(logo_path, x=10, y=8, w=20)  # Centered logo in header
        except:
            pass  # Skip if logo can't be loaded
    
    # Title with increased padding
    pdf.set_font("Helvetica", 'B', 20)  # Larger title font
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(0, 8)
    pdf.cell(0, 12, f"{branch.upper()} ATTENDANCE REPORT", ln=True, align='C')
    
    # Subheader
    pdf.set_font("Helvetica", '', 10)  # Larger subtitle font
    pdf.cell(0, 8, datetime.now().strftime("%B %d, %Y %H:%M:%S"), ln=True, align='C')
    
    # Calculate statistics
    present_today = sum(1 for a in attendance_data if a['entry_scans'] > 0)
    breakfast_count = sum(1 for a in attendance_data if a['breakfast_scans'] > 0)
    lunch_count = sum(1 for a in attendance_data if a['lunch_scans'] > 0)
    dinner_count = sum(1 for a in attendance_data if a['dinner_scans'] > 0)
    total_count = len(attendance_data)
    
    # Consolidated stats container (4 columns)
    stats_height = 36
    stats_width = pdf.w - 20  # Full width with margins
    start_y = header_height + 15
    
    # Main container
    pdf.set_fill_color(245, 245, 245)  # Light gray background
    pdf.rect(10, start_y, stats_width, stats_height, style='F')
    
    # Calculate column widths for stats (4 columns)
    col_width = stats_width / 4
    
    # Total participants
    pdf.set_xy(10, start_y + 4)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.set_text_color(*dark_text)
    pdf.cell(col_width, 6, "TOTAL PARTICIPANTS", ln=0, align='C')
    pdf.set_xy(10, start_y + 12)
    pdf.set_font("Helvetica", 'B', 18)
    pdf.set_text_color(*secondary_color)
    pdf.cell(col_width, 8, str(total_count), ln=0, align='C')
    
    # Present today
    pdf.set_xy(10 + col_width, start_y + 4)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.set_text_color(*dark_text)
    pdf.cell(col_width, 6, "PRESENT TODAY", ln=0, align='C')
    pdf.set_xy(10 + col_width, start_y + 12)
    pdf.set_font("Helvetica", 'B', 18)
    pdf.set_text_color(56, 142, 60)  # Green
    pdf.cell(col_width, 8, str(present_today), ln=0, align='C')
    
    # Meals stats (combined)
    pdf.set_xy(10 + 2*col_width, start_y + 4)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.set_text_color(*dark_text)
    pdf.cell(col_width, 6, "MEALS SERVED", ln=0, align='C')
    pdf.set_xy(10 + 2*col_width, start_y + 12)
    pdf.set_font("Helvetica", 'B', 18)
    pdf.set_text_color(*primary_color)
    pdf.cell(col_width, 8, f"{breakfast_count + lunch_count + dinner_count}", ln=0, align='C')
    
    # Last column for detailed meals
    pdf.set_xy(10 + 3*col_width, start_y + 4)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.set_text_color(*dark_text)
    pdf.cell(col_width, 6, "MEAL DETAILS", ln=0, align='C')
    pdf.set_xy(10 + 3*col_width, start_y + 10)
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(col_width, 5, f"Breakfast: {breakfast_count}", ln=1, align='C')
    pdf.set_x(10 + 3*col_width)
    pdf.cell(col_width, 5, f"Lunch: {lunch_count}", ln=1, align='C')
    pdf.set_x(10 + 3*col_width)
    pdf.cell(col_width, 5, f"Dinner: {dinner_count}", ln=1, align='C')
    
    # Table positioning
    table_start_y = start_y + stats_height + 15
    pdf.set_y(table_start_y)
    
    # Table headers - Simplified: Member, Year, Roll Number, Status
    headers = ["Member", "Year", "Roll Number", "Status"]
    
    # Calculate column widths - responsive to content
    max_lengths = {
        'member': max([pdf.get_string_width(str(s.get('member_name', ''))) for s in attendance_data] + [pdf.get_string_width("Member")]),
        'year': max([pdf.get_string_width(str(s.get('year', ''))) for s in attendance_data] + [pdf.get_string_width("Year")]),
        'rule_number': max([pdf.get_string_width(str(s.get('rule_number', ''))) for s in attendance_data] + [pdf.get_string_width("Roll Number")]),
    }
    
    col_widths = [
        min(max_lengths['member'] + 5, 110),     # Member
        20,                                      # Year
        min(max_lengths['rule_number'] + 5, 60), # Roll Number
        30,                                      # Status
    ]
    
    # Adjust if too wide
    total_width = sum(col_widths)
    if total_width > pdf.w - 20:
        scale_factor = (pdf.w - 20) / total_width
        col_widths = [w * scale_factor for w in col_widths]
    
    # Header row
    pdf.set_fill_color(*secondary_color)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", 'B', 10)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1, align='C', fill=True)
    pdf.ln()
    
    # Table rows
    pdf.set_text_color(*dark_text)
    pdf.set_font("Helvetica", '', 9)
    
    current_year = None
    row_height = 8
    
    for i, attendee in enumerate(attendance_data):
        # Check if we need a new page (leave space for footer)
        if pdf.get_y() + row_height * 3 > pdf.h - 40:
            pdf.add_page()
            pdf.set_y(10)
            # Recreate header on new page
            pdf.set_fill_color(*secondary_color)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", 'B', 10)
            for j, header in enumerate(headers):
                pdf.cell(col_widths[j], 10, header, border=1, align='C', fill=True)
            pdf.ln()
            pdf.set_text_color(*dark_text)
            pdf.set_font("Helvetica", '', 9)
        
        # Year sub-header
        if attendee.get('year') != current_year:
            current_year = attendee.get('year')
            pdf.set_fill_color(245, 245, 245)
            pdf.set_text_color(*secondary_color)
            pdf.set_font("Helvetica", 'B', 8)
            pdf.cell(sum(col_widths), row_height,
                    f" YEAR: {current_year if current_year else 'N/A'} ",
                    border=1, ln=True, align='L', fill=True)
            pdf.set_text_color(*dark_text)
            pdf.set_font("Helvetica", '', 9)
        
        # Determine status: Present if ANY scan occurred
        is_present = (
            attendee.get('entry_scans', 0) > 0 or
            attendee.get('breakfast_scans', 0) > 0 or
            attendee.get('lunch_scans', 0) > 0 or
            attendee.get('dinner_scans', 0) > 0
        )
        status_text = 'Present' if is_present else 'Absent'
        
        # Row color: light green for Present, light red for Absent
        if is_present:
            fill_color = (220, 255, 220) if i % 2 == 0 else (205, 245, 205)
        else:
            fill_color = (255, 235, 235) if i % 2 == 0 else (250, 220, 220)
        pdf.set_fill_color(*fill_color)
        
        row_data = [
            (attendee.get('member_name', 'N/A'), 'L'),
            (attendee.get('year', 'N/A'), 'C'),
            (attendee.get('rule_number', 'N/A'), 'C'),
            (status_text, 'C'),
        ]
        
        for j, (item, align) in enumerate(row_data):
            text = str(item)
            while pdf.get_string_width(text) > col_widths[j] - 2 and len(text) > 3:
                text = text[:-1]
            if len(text) < len(str(item)):
                text = text[:-3] + "..." if len(text) > 3 else "..."
            
            # Color the status cell text
            if j == 3:
                pdf.set_text_color(0, 128, 0) if is_present else pdf.set_text_color(180, 0, 0)
                pdf.set_font("Helvetica", 'B', 9)
            else:
                pdf.set_text_color(*dark_text)
                pdf.set_font("Helvetica", '', 9)
            
            pdf.cell(col_widths[j], row_height, text, border=1, align=align, fill=True)
        pdf.ln()
    
    # Footer with developer credit - responsive positioning
    # Calculate remaining space on current page
    remaining_space = pdf.h - pdf.get_y() - 40  # 40 is approximate footer height
    
    # If not enough space, create new page
    if remaining_space < 40:
        pdf.add_page()
    
    # Footer content
    footer_y = max(pdf.get_y(), pdf.h - 60)  # Ensure footer is at bottom
    
    # Footer background
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(0, footer_y, pdf.w, 60, style='F')
    
    # Report generation timestamp
    today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pdf.set_font("Helvetica", 'I', 8)
    pdf.set_text_color(*light_text)
    pdf.set_xy(10, footer_y + 5)
    pdf.cell(0, 6, f"Report generated on: {today}", 0, 0, 'L')
    
    # Page number
    pdf.set_text_color(*primary_color)
    pdf.set_xy(-30, footer_y + 5)
    pdf.cell(0, 6, f"Page {pdf.page_no()}", 0, 0, 'R')
    

    
    # Contact information
    pdf.set_text_color(*secondary_color)
    pdf.cell(0, 6, "Contact: creator_club@sphoorthyengg.ac.in", 0, 1, 'L')
    
    return pdf

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    # Load hackathon config
    try:
        with open(HACKATHON_CONFIG_FILE, 'r') as f:
            config = json.load(f)
    except:
        config = {'payment_required': True}
    
    if not config.get('payment_required'):
        flash('This hackathon does not require payment', 'info')
        return redirect(url_for('register'))
    
    if 'team_data' not in session:
        flash('Please complete your registration first', 'error')
        return redirect(url_for('register', clear_pending=1))
    
    team_data = session['team_data']
    
    # Verify the team hasn't already completed payment
    with open(DATABASE_FILE, 'r') as f:
        try:
            data = json.load(f)
            existing_team = next((t for t in data.get('teams', []) if t['team_id'] == team_data['team_id']), None)
            if existing_team and existing_team.get('payment_id'):
                flash('This team has already completed payment', 'error')
                session.pop('team_data', None)
                return redirect(url_for('register'))
        except json.JSONDecodeError:
            pass  # Continue with payment if database is corrupt
    
    if request.method == 'POST':
        payment_method = request.form.get('payment_method', 'online')
        
        payment_id = request.form.get('payment_id')
        if not payment_id:
            flash('Please enter your payment ID', 'error')
            return redirect(url_for('payment'))
        
        # Handle file upload
        payment_screenshot = None
        if 'payment_screenshot' in request.files:
            file = request.files['payment_screenshot']
            if file and allowed_file(file.filename):
                filename = f"payment_{team_data['team_id']}.{file.filename.rsplit('.', 1)[1].lower()}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                payment_screenshot = f"static/uploads/{filename}"
            elif file.filename:
                flash('Invalid file type for payment screenshot', 'error')
                return redirect(url_for('payment'))
        
        # Update team data with payment info
        team_data['payment_method'] = 'online'
        team_data['payment_verified'] = False
        team_data['payment_id'] = payment_id
        team_data['payment_screenshot'] = payment_screenshot
        
        # Common fields for both payment methods
        team_data['payment_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Save to database with thread-safe locking
        with team_id_lock:
            try:
                with open(DATABASE_FILE, 'r+') as f:
                    try:
                        data = json.load(f)
                        if 'teams' not in data:
                            data['teams'] = []
                        
                        # Find and update the existing team record
                        updated = False
                        for idx, team in enumerate(data['teams']):
                            if team['team_id'] == team_data['team_id']:
                                data['teams'][idx] = team_data
                                updated = True
                                break
                        
                        if not updated:
                            data['teams'].append(team_data)
                        
                        f.seek(0)
                        json.dump(data, f, indent=4)
                        f.truncate()
                        
                    except json.JSONDecodeError:
                        # Handle corrupt file by creating new one
                        data = {'teams': [team_data]}
                        with open(DATABASE_FILE, 'w') as f:
                            json.dump(data, f, indent=4)
            except Exception as e:
                flash('Error saving payment details. Please try again.', 'error')
                print(f"Error in payment processing: {str(e)}")
                return redirect(url_for('payment'))
        
        # Generate QR code
        qr_data = {
            'team_id': team_data['team_id'],
            'team_name': team_data['team_name'],
            'members': [{'name': m['name'], 'id': m['id']} for m in team_data['members']]
        }
        
        qr_img = generate_qr_code_image(json.dumps(qr_data))
        qr_img_base64 = base64.b64encode(qr_img.getvalue()).decode('utf-8')

        # Send thank you emails to eligible members
        for member in team_data['members']:
            if member['email'].endswith(('@laxminivasmorishetty143.com', '@gmail.com')):
                threading.Thread(target=send_thank_you_email, args=(member['email'], team_data, qr_img_base64)).start()

        session.pop('team_data', None)
        flash('Payment details submitted successfully! Your registration will be complete after admin verification.', 'success')
        return render_template('success.html', team=team_data, qr_img=qr_img_base64)
    
    return render_template('payment.html', team=team_data, phonepe_qr=PHONEPE_QR_CODE)

@app.route('/update_payment_status/<team_id>', methods=['POST'])
def update_payment_status(team_id):
    # Authentication check removed for public roster desks


    try:
        data = request.get_json()
        action = data.get('action')
        reason = data.get('reason', '')
        
        # Validate action
        if action not in ['approve', 'reject']:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400
            
        # Load database
        with open(DATABASE_FILE, 'r+') as f:
            try:
                db_data = json.load(f)
                teams = db_data.get('teams', [])
                
                # Find the team
                team_found = False
                for team in teams:
                    if team['team_id'] == team_id:
                        team_found = True
                        # Update payment status
                        team['payment_verified'] = (action == 'approve')
                        team['payment_status'] = 'approved' if action == 'approve' else 'rejected'
                        team['payment_review_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        team['payment_review_by'] = session.get('admin_id', 'unknown')
                        
                        if action == 'reject':
                            team['payment_rejection_reason'] = reason
                        
                        break
                
                if not team_found:
                    return jsonify({'success': False, 'message': 'Team not found'}), 404
                
                # Save changes
                f.seek(0)
                json.dump(db_data, f, indent=4)
                f.truncate()
                
                # Send email if payment is approved
                if action == 'approve':
                    for member in team['members']:
                        send_payment_verification_email(member['email'], team)

                return jsonify({
                    'success': True,
                    'message': f'Payment {action}d successfully',
                    'new_status': action == 'approve'
                })
                
            except json.JSONDecodeError as e:
                return jsonify({
                    'success': False,
                    'message': 'Database error',
                    'error': str(e)
                }), 500
                
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Server error',
            'error': str(e)
        }), 500
    
    
@app.route('/admin/edit-team/<team_id>', methods=['POST'])
def edit_team(team_id):
    # Authentication check for admin
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    try:
        data = request.get_json()
        updated_members = data.get('members', [])
        updated_team_name = data.get('team_name')
        
        with open(DATABASE_FILE, 'r+') as f:
            db_data = json.load(f)
            teams = db_data.get('teams', [])
            
            team_found = False
            for team in teams:
                if team['team_id'] == team_id:
                    team_found = True
                    if updated_team_name:
                        team['team_name'] = updated_team_name
                    
                    # Update member data
                    for i, m in enumerate(team['members']):
                        if i < len(updated_members):
                            m['name'] = updated_members[i].get('name', m.get('name'))
                            m['gender'] = updated_members[i].get('gender', m.get('gender'))
                            m['branch'] = updated_members[i].get('branch', m.get('branch'))
                            m['contact'] = updated_members[i].get('contact', m.get('contact'))
                            m['email'] = updated_members[i].get('email', m.get('email'))
                    break
            
            if not team_found:
                return jsonify({'success': False, 'message': 'Team not found'}), 404
                
            f.seek(0)
            json.dump(db_data, f, indent=4)
            f.truncate()
            
        return jsonify({'success': True, 'message': 'Team updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/generate_qr/<team_id>')
def generate_qr(team_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    # Look up team data
    with open(DATABASE_FILE, 'r') as f:
        try:
            data = json.load(f)
            team = next((t for t in data['teams'] if t['team_id'] == team_id), None)
        except (json.JSONDecodeError, KeyError):
            return "Database error", 500
    
    if not team:
        return "Team not found", 404

    # Generate QR code data
    qr_data = {
        'team_id': team['team_id'],
        'team_name': team['team_name'],
        'members': [{'name': m['name'], 'id': m['id']} for m in team['members']]
    }

    # Generate the QR code image
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to memory buffer
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        # For view requests
        if request.args.get('view'):
            return send_file(buffer, mimetype='image/png')
        
        # For download requests
        return send_file(
            buffer,
            mimetype='image/png',
            as_attachment=True,
            download_name=f"{team_id}_qr.png"
        )
    except Exception as e:
        return f"QR generation failed: {str(e)}", 500
    
@app.route('/download_qr/<team_id>')
def download_qr(team_id):
    qr_path = os.path.join('static', 'qr_images', f"{team_id}.png")
    if not os.path.exists(qr_path):
        return "QR code not found", 404
    
    return send_file(qr_path, as_attachment=True, download_name=f"{team_id}_qr.png")
# Add this route to your Flask app
@app.route('/get_sections')
def get_sections():
    branch = request.args.get('branch')
    # Return sections based on branch - this should match your actual data structure
    sections = {
        'CSE': ['A', 'B', 'C'],
        'ECE': ['A', 'B'],
        'EEE': ['A'],
        # Add other branches and their sections
    }
    return jsonify(sections.get(branch, []))


# Add these imports at the top if not already present
from datetime import datetime
import json
import os

# Add this new route to toggle registration status
@app.route('/admin/toggle-registration', methods=['POST'])
def toggle_registration():
    """Toggle the registration open/close status"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        new_status = data.get('open', True)
        message = data.get('message', '')
        
        # Load current config
        config_path = HACKATHON_CONFIG_FILE
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {
                'payment_required': True,
                'registration_fee': 500,
                'registration_open': True,
                'registration_message': ''
            }
        
        # Update status
        config['registration_open'] = new_status
        if message:
            config['registration_message'] = message
        
        # Save config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        return jsonify({
            'success': True,
            'message': f'Registration {"opened" if new_status else "closed"} successfully',
            'new_status': new_status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Add this route to get current registration status
@app.route('/admin/registration-status', methods=['GET'])
def get_registration_status():
    """Get current registration status"""
    # Authentication check removed for public access support

    
    try:
        config_path = HACKATHON_CONFIG_FILE
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {
                'payment_required': True,
                'registration_fee': 500,
                'registration_open': True,
                'registration_message': ''
            }
        
        return jsonify({
            'success': True,
            'registration_open': config.get('registration_open', True),
            'registration_message': config.get('registration_message', ''),
            'payment_required': config.get('payment_required', True),
            'registration_fee': config.get('registration_fee', 500)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
    
@app.route('/admin/registration-toggle', methods=['GET'])
def registration_toggle():
    """Show registration toggle page"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    return render_template('registration_toggle.html')

def parse_user_agent(ua_string):
    if not ua_string:
        return "Unknown Device"
    ua_lower = ua_string.lower()
    os_name = "Unknown OS"
    browser_name = "Unknown Browser"
    
    if "windows" in ua_lower:
        os_name = "Windows"
    elif "macintosh" in ua_lower or "mac os" in ua_lower:
        os_name = "macOS"
    elif "android" in ua_lower:
        os_name = "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "iOS"
    elif "linux" in ua_lower:
        os_name = "Linux"
        
    if "chrome" in ua_lower:
        browser_name = "Chrome"
    elif "safari" in ua_lower:
        browser_name = "Safari"
    elif "firefox" in ua_lower:
        browser_name = "Firefox"
    elif "edge" in ua_lower:
        browser_name = "Edge"
    elif "opera" in ua_lower:
        browser_name = "Opera"
        
    return f"{os_name} ({browser_name})"

@app.route('/admin/scan', methods=['GET', 'POST'])
def scan_qr():
    """Handle QR code scanning for attendance and meal tracking with day-based limits"""
    
    # Authentication check removed for public scanning desks


    if request.method == 'GET':
        # Get today's date in IST for display
        today_ist = datetime.now(IST).strftime('%Y-%m-%d')
        return render_template('scan_qr.html', 
                             scan_types=SCAN_TYPES,
                             today_date=today_ist)

    # POST request handling
    try:
        # Validate request format
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': 'Request must be JSON',
                'code': 'INVALID_REQUEST'
            }), 400

        data = request.get_json()
        qr_data = data.get('qr_data')
        scan_type = data.get('scan_type')
        member_ids = data.get('member_ids', [])
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy')
        
        user_agent = request.headers.get('User-Agent', '')
        device = parse_user_agent(user_agent)

        # Validate required fields
        if not all([qr_data, scan_type]):
            return jsonify({
                'success': False,
                'message': 'Missing QR data or scan type',
                'code': 'MISSING_DATA'
            }), 400

        if scan_type not in SCAN_TYPES:
            return jsonify({
                'success': False,
                'message': f'Invalid scan type. Allowed: {", ".join(SCAN_TYPES)}',
                'code': 'INVALID_SCAN_TYPE'
            }), 400

        # Parse and validate QR data
        try:
            qr_json = json.loads(qr_data)
            required_fields = ['team_id', 'team_name', 'members']
            if not all(field in qr_json for field in required_fields):
                missing = [f for f in required_fields if f not in qr_json]
                return jsonify({
                    'success': False,
                    'message': f'Missing fields in QR data: {", ".join(missing)}',
                    'code': 'INVALID_QR_FORMAT'
                }), 400

            if not isinstance(qr_json['members'], list):
                return jsonify({
                    'success': False,
                    'message': 'Members data should be an array',
                    'code': 'INVALID_MEMBERS_DATA'
                }), 400

        except json.JSONDecodeError as e:
            return jsonify({
                'success': False,
                'message': 'Invalid JSON in QR code',
                'code': 'INVALID_QR_DATA',
                'error': str(e)
            }), 400

        team_id = qr_json['team_id']
        team_name = qr_json['team_name']

        # Verify team exists in database
        teams = get_teams_from_database()
        team = next((t for t in teams if t['team_id'] == team_id), None)
        if not team:
            return jsonify({
                'success': False,
                'message': 'Team not registered',
                'code': 'TEAM_NOT_FOUND'
            }), 404

        # Check if team payment is verified (if applicable)
        if not team.get('payment_verified', False):
            return jsonify({
                'success': False,
                'message': 'Team payment not verified',
                'code': 'PAYMENT_NOT_VERIFIED'
            }), 403

        # Get current date in IST for day-based tracking
        now_ist = datetime.now(IST)
        today_date = now_ist.strftime('%Y-%m-%d')
        today_display = now_ist.strftime('%d %b %Y')
        
        # Load scan log with error handling
        initial_data = {
            'entries': [],
            'food': {st: [] for st in SCAN_TYPES if st != 'entry'},
            'daily_stats': {}  # New: track daily scans
        }

        try:
            if not os.path.exists(SCANNED_LOG_FILE):
                with open(SCANNED_LOG_FILE, 'w') as f:
                    json.dump(initial_data, f)

            with open(SCANNED_LOG_FILE, 'r') as f:
                log_data = json.load(f)
                
            # Ensure the structure is valid
            if 'food' not in log_data:
                log_data['food'] = {st: [] for st in SCAN_TYPES if st != 'entry'}
            if 'entries' not in log_data:
                log_data['entries'] = []
            if 'daily_stats' not in log_data:
                log_data['daily_stats'] = {}
                
            # Validate each food scan type exists
            for st in SCAN_TYPES:
                if st != 'entry' and st not in log_data['food']:
                    log_data['food'][st] = []
                    
        except Exception as e:
            app.logger.error(f"Error loading scan log: {str(e)}")
            # Try to recover by creating fresh log data
            log_data = initial_data
            try:
                with open(SCANNED_LOG_FILE, 'w') as f:
                    json.dump(log_data, f)
            except Exception as write_error:
                app.logger.error(f"Could not recreate scan log: {str(write_error)}")
                return jsonify({
                    'success': False,
                    'message': 'Could not access or recreate scan records',
                    'code': 'LOG_READ_ERROR',
                    'error': str(e)
                }), 500

        # Get the appropriate log category
        log_category = (
            log_data['entries'] 
            if scan_type == 'entry' 
            else log_data['food'].setdefault(scan_type, [])
        )

        # Initialize daily stats for this team if not exists
        if team_id not in log_data['daily_stats']:
            log_data['daily_stats'][team_id] = {}

        # Process member scans with day-based checking
        scanned_members = []
        duplicate_members = []
        invalid_members = []
        already_scanned_today = []
        now_ist_str = now_ist.strftime('%Y-%m-%d %H:%M:%S')

        for member_id in member_ids:
            # Verify member exists in team
            member = next((m for m in team['members'] if m['id'] == member_id), None)
            if not member:
                invalid_members.append({
                    'id': member_id,
                    'name': 'Unknown',
                    'reason': 'Not in team'
                })
                continue

            # Check if member has already been scanned for this type today
            member_key = f"{member_id}_{scan_type}"
            
            if member_key in log_data['daily_stats'][team_id]:
                last_scan_date = log_data['daily_stats'][team_id][member_key].get('date')
                
                if last_scan_date == today_date:
                    # Already scanned today for this type
                    already_scanned_today.append({
                        'id': member_id,
                        'name': member['name'],
                        'scan_time': log_data['daily_stats'][team_id][member_key].get('time', 'Unknown')
                    })
                    continue

            # Check for duplicates in the last 2 hours (still keep this as additional check)
            is_duplicate = False
            for entry in log_category[-20:]:  # Check last 20 entries for performance
                if (entry.get('team_id') == team_id and 
                    member_id in entry.get('members', [])):
                    
                    # Parse the timestamp and make it timezone-aware
                    entry_time = datetime.strptime(entry['timestamp'], '%Y-%m-%d %H:%M:%S')
                    # Make entry_time aware (assume it's in IST since we store in IST)
                    entry_time = IST.localize(entry_time)
                    
                    # Now compare with timezone-aware now_ist
                    if (now_ist - entry_time).total_seconds() < 7200:  # 2 hours in seconds
                        is_duplicate = True
                        break

            if is_duplicate:
                duplicate_members.append({
                    'id': member_id,
                    'name': member['name'],
                    'reason': 'Already scanned recently'
                })
            else:
                scanned_members.append({
                    'id': member_id,
                    'name': member['name']
                })

        # If members already scanned today, show appropriate message
        if already_scanned_today:
            names = [m['name'] for m in already_scanned_today]
            return jsonify({
                'success': False,
                'message': f"Already scanned today: {', '.join(names[:3])}" + 
                          (f" and {len(already_scanned_today)-3} more" if len(already_scanned_today) > 3 else ""),
                'code': 'ALREADY_SCANNED_TODAY',
                'details': {
                    'already_scanned': already_scanned_today,
                    'date': today_display
                }
            }), 400

        # Return early if no valid scans
        if not scanned_members:
            return jsonify({
                'success': False,
                'message': 'No valid members to scan',
                'code': 'NO_VALID_SCANS',
                'details': {
                    'scanned': scanned_members,
                    'duplicates': duplicate_members,
                    'invalid': invalid_members,
                    'already_scanned': already_scanned_today
                }
            }), 400

        # Create and save log entry
        log_entry = {
            'team_id': team_id,
            'team_name': team_name,
            'members': [m['id'] for m in scanned_members],
            'member_names': [m['name'] for m in scanned_members],
            'timestamp': now_ist_str,
            'date': today_date,
            'scanner_id': session.get('username', 'unknown'),
            'scan_type': scan_type,
            'device': device,
            'latitude': latitude,
            'longitude': longitude,
            'location_accuracy': accuracy
        }

        try:
            log_category.append(log_entry)
            
            # Update daily stats for each scanned member
            for member in scanned_members:
                member_key = f"{member['id']}_{scan_type}"
                log_data['daily_stats'][team_id][member_key] = {
                    'date': today_date,
                    'time': now_ist_str,
                    'scan_type': scan_type,
                    'member_name': member['name'],
                    'scanner_id': session.get('username', 'unknown'),
                    'device': device,
                    'latitude': latitude,
                    'longitude': longitude
                }
            
            # Save with file locking to prevent corruption
            with open(SCANNED_LOG_FILE, 'w') as f:
                json.dump(log_data, f, indent=4, ensure_ascii=False)
                
        except Exception as e:
            app.logger.error(f"Error saving scan log: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Failed to save scan record',
                'code': 'LOG_SAVE_ERROR',
                'error': str(e)
            }), 500

        # Return success response
        return jsonify({
            'success': True,
            'message': f"Successfully scanned {len(scanned_members)} member(s) for {today_display}",
            'data': {
                'team_id': team_id,
                'team_name': team_name,
                'scan_type': scan_type,
                'timestamp': now_ist_str,
                'date': today_display,
                'scanned_members': scanned_members,
                'duplicate_members': duplicate_members,
                'invalid_members': invalid_members,
                'already_scanned_today': already_scanned_today
            }
        })

    except Exception as e:
        app.logger.error(f"Unexpected error in scan_qr: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred',
            'code': 'SERVER_ERROR',
            'error': str(e)
        }), 500


@app.route('/get_scan_log')
def get_scan_log():
    # Authentication check removed for public scanning desks


    try:
        # Initialize empty log if file doesn't exist
        if not os.path.exists(SCANNED_LOG_FILE):
            with open(SCANNED_LOG_FILE, 'w') as f:
                json.dump({
                    'entries': [],
                    'food': {st: [] for st in SCAN_TYPES if st != 'entry'},
                    'daily_stats': {}
                }, f)

        # Load log data
        with open(SCANNED_LOG_FILE, 'r') as f:
            log_data = json.load(f)

        # Get filter parameters
        date_filter = request.args.get('date', '')
        team_filter = request.args.get('team', '')
        member_filter = request.args.get('member', '')

        # Process all entries into a single list
        all_entries = []
        
        # Process entry logs
        for entry in log_data.get('entries', []):
            for i, member_id in enumerate(entry.get('members', [])):
                all_entries.append({
                    'timestamp': entry.get('timestamp'),
                    'date': entry.get('date', entry.get('timestamp', '')[:10]),
                    'scan_type': 'entry',
                    'team_id': entry.get('team_id'),
                    'team_name': entry.get('team_name', 'Unknown Team'),
                    'member_id': member_id,
                    'member_name': entry.get('member_names', [])[i] if i < len(entry.get('member_names', [])) else 'Unknown Member',
                    'status': 'Success',
                    'scanner_id': entry.get('scanner_id', 'unknown'),
                    'device': entry.get('device', 'Unknown Device'),
                    'latitude': entry.get('latitude'),
                    'longitude': entry.get('longitude'),
                    'accuracy': entry.get('location_accuracy')
                })

        # Process food logs
        for meal_type in ['breakfast', 'lunch', 'dinner']:
            for entry in log_data.get('food', {}).get(meal_type, []):
                for i, member_id in enumerate(entry.get('members', [])):
                    all_entries.append({
                        'timestamp': entry.get('timestamp'),
                        'date': entry.get('date', entry.get('timestamp', '')[:10]),
                        'scan_type': meal_type,
                        'team_id': entry.get('team_id'),
                        'team_name': entry.get('team_name', 'Unknown Team'),
                        'member_id': member_id,
                        'member_name': entry.get('member_names', [])[i] if i < len(entry.get('member_names', [])) else 'Unknown Member',
                        'status': 'Success',
                        'scanner_id': entry.get('scanner_id', 'unknown'),
                        'device': entry.get('device', 'Unknown Device'),
                        'latitude': entry.get('latitude'),
                        'longitude': entry.get('longitude'),
                        'accuracy': entry.get('location_accuracy')
                    })

        # Apply filters
        if date_filter:
            all_entries = [e for e in all_entries if e.get('date', '') == date_filter]
        
        if team_filter and team_filter.lower() != 'all':
            all_entries = [e for e in all_entries if team_filter.lower() in e.get('team_name', '').lower() or 
                          team_filter.lower() in e.get('team_id', '').lower()]
        
        if member_filter:
            all_entries = [e for e in all_entries if member_filter.lower() in e.get('member_name', '').lower()]

        # Sort by timestamp (newest first) - handle timezone properly
        def parse_timestamp(ts):
            try:
                dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                # Make it timezone-aware (IST)
                return IST.localize(dt)
            except (ValueError, TypeError):
                return datetime.min.replace(tzinfo=IST)

        all_entries.sort(key=lambda x: parse_timestamp(x['timestamp']), reverse=True)

        # Get daily stats for summary
        daily_stats = log_data.get('daily_stats', {})
        
        # Count scans by date
        scans_by_date = {}
        for entry in all_entries:
            date = entry.get('date', 'Unknown')
            if date not in scans_by_date:
                scans_by_date[date] = {
                    'total': 0,
                    'entry': 0,
                    'breakfast': 0,
                    'lunch': 0,
                    'dinner': 0
                }
            scans_by_date[date]['total'] += 1
            scans_by_date[date][entry['scan_type']] += 1

        return jsonify({
            'entries': all_entries,
            'daily_stats': scans_by_date,
            'filters': {
                'date': date_filter,
                'team': team_filter,
                'member': member_filter
            }
        })

    except Exception as e:
        app.logger.error(f"Error in get_scan_log: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Server error',
            'message': 'Could not load scan log',
            'details': str(e)
        }), 500
    
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check dynamic credentials first
        credentials = load_credentials()
        user = next((u for u in credentials if u['username'] == username), None)
        if user and check_password_hash(user['password'], password):
            session['admin_logged_in'] = True
            session['username'] = username
            session['role'] = user.get('role', 'custom')
            return redirect(url_for('admin'))
            
        # Fallback to legacy hardcoded AD2025 check
        if username == ADMIN_CREDENTIALS['username'] and password == ADMIN_CREDENTIALS['password']:
            session['admin_logged_in'] = True
            session['username'] = username
            session['role'] = 'super_admin'
            return redirect(url_for('admin'))
            
        flash('Invalid credentials', 'error')
    return render_template('admin_login.html')

@app.route('/api/dashboard-stats')
def dashboard_stats():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
    teams = get_teams_from_database()
    
    total_teams = len(teams)
    total_members = sum(len(team.get('members', [])) for team in teams)
    
    verified_count = 0
    pending_count = 0
    
    for team in teams:
        if team.get('payment_verified'):
            verified_count += 1
        else:
            pending_count += 1
            
    return jsonify({
        'success': True,
        'total_teams': total_teams,
        'total_members': total_members,
        'verified_count': verified_count,
        'pending_count': pending_count
    })

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        if session.get('teams_logged_in'):
            return redirect(url_for('view_teams'))
        return redirect(url_for('admin_login'))
        
    username = session.get('username')
    role = session.get('role')
    
    # If they are NOT super_admin, check if they have allowed modules and redirect to the first one
    if username != ADMIN_CREDENTIALS['username'] and role != 'super_admin':
        credentials = load_credentials()
        user = next((u for u in credentials if u['username'] == username), None)
        if user:
            allowed_ws = user.get('allowed_workspaces', [])
            allowed_mods = user.get('allowed_modules', {})
            all_ws = load_workspaces()
            
            for ws in all_ws:
                if ws['id'] in allowed_ws:
                    mod_names = allowed_mods.get(ws['id'], [])
                    for mod in ws['modules']:
                        if mod['name'] in mod_names:
                            return redirect(mod['url'])
                            
        flash('Access Denied: You do not have permission to view the dashboard.', 'error')
        return redirect(url_for('logout'))
        
    return render_template('admin_dashboard.html')


@app.route('/admin/teams')
def view_teams():
    # Authentication check removed for public teams roster desk

    
    teams = get_teams_from_database()
    
    # Calculate gender distribution
    gender_counts = {
        'Male': 0,
        'Female': 0,
        'Other': 0,
        'Prefer not to say': 0
    }
    
    # Initialize verification counters
    verified_count = 0
    pending_count = 0
    verified_members = 0
    pending_members = 0
    
    for team in teams:
        # Count verified/pending teams and members
        if team.get('payment_verified'):
            verified_count += 1
            verified_members += len(team['members'])
        else:
            pending_count += 1
            pending_members += len(team['members'])
        
        # Count genders
        for member in team['members']:
            gender = member.get('gender', 'Prefer not to say')
            gender_counts[gender] = gender_counts.get(gender, 0) + 1
    
    # Format dates before passing to template
    for team in teams:
        if not isinstance(team['registration_date'], str):
            team['registration_date'] = team['registration_date'].strftime('%d %b %Y')
    
    total_members = sum(len(team['members']) for team in teams)
    
    return render_template('view_teams.html', 
                         teams=teams, 
                         total_members=total_members,
                         verified_count=verified_count,
                         pending_count=pending_count,
                         verified_members=verified_members,
                         pending_members=pending_members,
                         gender_counts=gender_counts,
                         is_admin=session.get('admin_logged_in', False))

@app.route('/admin/suggestions')
def view_suggestions():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('suggestions.html')

@app.route('/get_suggestions')
def get_suggestions():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        with open(SUGGESTIONS_FILE, 'r') as f:
            data = json.load(f)
            return jsonify(data)
    except Exception as e:
        return jsonify({'suggestions': [], 'error': str(e)})

@app.route('/admin/export/<export_type>')
def export_data(export_type):
    # Authentication check removed for public exports support

    
    if export_type == 'teams':
        teams = get_teams_from_database()
        
        # Create CSV in memory
        output = BytesIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Team ID', 'Team Name', 'Payment Status', 
            'Member Name', 'Email', 'Contact', 
            'College', 'Branch', 'Year', 'Gender',
            'Registration Date'
        ])
        
        # Write data
        for team in teams:
            for member in team.get('members', []):
                writer.writerow([
                    team['team_id'],
                    team['team_name'],
                    'Verified' if team.get('payment_verified') else 'Pending',
                    member['name'],
                    member['email'],
                    member['contact'],
                    member['college'],
                    member['branch'],
                    member['year'],
                    member.get('gender', ''),
                    team.get('registration_date', '')
                ])
        
        output.seek(0)
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name='teams_export.csv'
        )
    
    elif export_type == 'logs':
        try:
            with open(SCANNED_LOG_FILE, 'r') as f:
                log_data = json.load(f)
        except Exception:
            log_data = {'entries': [], 'food': {st: [] for st in SCAN_TYPES if st != 'entry'}}
        
        # Create CSV in memory
        output = BytesIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Timestamp', 'Scan Type', 'Team ID', 
            'Team Name', 'Member ID', 'Member Name',
            'Scanner ID', 'Device', 'Latitude', 'Longitude', 'Accuracy'
        ])
        
        # Write entry logs
        for entry in log_data.get('entries', []):
            for i, member_id in enumerate(entry.get('members', [])):
                writer.writerow([
                    entry.get('timestamp'),
                    'entry',
                    entry.get('team_id'),
                    entry.get('team_name', 'Unknown Team'),
                    member_id,
                    entry.get('member_names', [])[i] if i < len(entry.get('member_names', [])) else 'Unknown Member',
                    entry.get('scanner_id', 'unknown'),
                    entry.get('device', 'Unknown Device'),
                    entry.get('latitude', ''),
                    entry.get('longitude', ''),
                    entry.get('location_accuracy', '')
                ])
        
        # Write food logs
        for meal_type in ['breakfast', 'lunch', 'dinner']:
            for entry in log_data.get('food', {}).get(meal_type, []):
                for i, member_id in enumerate(entry.get('members', [])):
                    writer.writerow([
                        entry.get('timestamp'),
                        meal_type,
                        entry.get('team_id'),
                        entry.get('team_name', 'Unknown Team'),
                        member_id,
                        entry.get('member_names', [])[i] if i < len(entry.get('member_names', [])) else 'Unknown Member',
                        entry.get('scanner_id', 'unknown'),
                        entry.get('device', 'Unknown Device'),
                        entry.get('latitude', ''),
                        entry.get('longitude', ''),
                        entry.get('location_accuracy', '')
                    ])
        
        output.seek(0)
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name='scan_logs_export.csv'
        )
    
    else:
        flash('Invalid export type', 'error')
        return redirect(url_for('admin'))
    

# Receipt login and generate route handlers completely removed.

@app.route('/teams-login', methods=['GET', 'POST'])
def teams_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check dynamic credentials first
        credentials = load_credentials()
        user = next((u for u in credentials if u['username'] == username), None)
        if user and check_password_hash(user['password'], password):
            session['teams_logged_in'] = True
            session['username'] = username
            session['role'] = user.get('role', 'teams_viewer')
            return redirect(url_for('view_teams'))
            
        # Fallback to legacy hardcoded TC2025 check
        if username == TEAMS_CREDENTIALS['username'] and password == TEAMS_CREDENTIALS['password']:
            session['teams_logged_in'] = True
            session['username'] = username
            session['role'] = 'teams_viewer'
            return redirect(url_for('view_teams'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('teams_login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- Navigation Workspaces System ---
WORKSPACES_FILE = 'data/workspaces.json'
CREDENTIALS_FILE = 'data/credentials.json'

def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        default_creds = [
            {
                "username": "AD2025",
                "password": generate_password_hash("CCAD02"),
                "role": "super_admin",
                "allowed_workspaces": [],
                "allowed_modules": {}
            },
            {
                "username": "TC2025",
                "password": generate_password_hash("CCMA1"),
                "role": "teams_viewer",
                "allowed_workspaces": ["administration"],
                "allowed_modules": {
                    "administration": ["View Teams"]
                }
            }
        ]
        os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(default_creds, f, indent=4)
        return default_creds
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_credentials(creds):
    os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(creds, f, indent=4)

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s_-]', '', text)
    text = re.sub(r'[\s_-]+', '_', text)
    return text

@app.before_request
def check_route_access():
    path = request.path
    if path.startswith('/static/') or path.startswith('/favicon.ico'):
        return
        
    if path.startswith('/evaluator') or path == '/evaluator-login':
        return
        
    if path == '/teams-login':
        return
        
    if path.startswith('/admin') or path.startswith('/attendance') or path.startswith('/message-center') or path == '/get_suggestions':
        if path == '/admin-login':
            return
            
        if path in ['/admin/teams', '/get_team_details', '/api/teams']:
            return
            
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
            
        username = session.get('username')
        role = session.get('role')
        
        # Super admin gets access to all pages
        if username == ADMIN_CREDENTIALS['username'] or role == 'super_admin':
            return
            
        if role == 'teams_viewer':
            allowed = ['/admin', '/admin/teams', '/logout']
            if path not in allowed:
                flash('Access Denied: You do not have permission to access this page.', 'error')
                return redirect(url_for('admin'))
            return
            
        credentials = load_credentials()
        user = next((u for u in credentials if u['username'] == username), None)
        if user:
            if path == '/admin/workspaces' or path == '/admin/settings':
                flash('Access Denied: Super Admin only.', 'error')
                return redirect(url_for('admin'))
                
            allowed_urls = ['/admin', '/logout']
            allowed_ws = user.get('allowed_workspaces', [])
            allowed_mods = user.get('allowed_modules', {})
            all_ws = load_workspaces()
            
            for ws in all_ws:
                if ws['id'] in allowed_ws:
                    mod_names = allowed_mods.get(ws['id'], [])
                    for mod in ws['modules']:
                        if mod['name'] in mod_names:
                            allowed_urls.append(mod['url'])
            
            # Map suggestion fetches to suggestion page access
            if '/admin/suggestions' in allowed_urls:
                allowed_urls.append('/get_suggestions')
                
            if path not in allowed_urls:
                flash('Access Denied: You do not have permission to access this page.', 'error')
                return redirect(url_for('admin'))
        else:
            session.clear()
            return redirect(url_for('admin_login'))

def load_workspaces():
    if not os.path.exists(WORKSPACES_FILE):
        default_ws = [
            {
                "id": "administration",
                "name": "Administration Workspace",
                "enabled": True,
                "assigned_roles": ["admin"],
                "modules": [
                    {"name": "View Teams", "url": "/admin/teams", "icon": "fas fa-users-between-lines"},
                    {"name": "QR Scanner", "url": "/admin/scan", "icon": "fas fa-qrcode"},
                    {"name": "Evaluation Settings", "url": "/admin/evaluation-settings", "icon": "fas fa-cog"},
                    {"name": "Leaderboard", "url": "/admin/leaderboard", "icon": "fas fa-trophy"},
                    {"name": "Evaluation Results", "url": "/admin/evaluation-results", "icon": "fas fa-chart-bar"},
                    {"name": "Edit Homepage", "url": "/admin/homepage", "icon": "fas fa-home"},
                    {"name": "Upload Student Data", "url": "/admin/upload-students", "icon": "fas fa-upload"},
                    {"name": "Attendance Management", "url": "/attendance", "icon": "fas fa-clipboard-check"},
                    {"name": "Suggestions Management", "url": "/admin/suggestions", "icon": "fas fa-comments"},
                    {"name": "Message Center", "url": "/message-center", "icon": "fas fa-envelope"}
                ]
            }
        ]
        os.makedirs(os.path.dirname(WORKSPACES_FILE), exist_ok=True)
        with open(WORKSPACES_FILE, "w") as f:
            json.dump(default_ws, f, indent=4)
        return default_ws
    
    try:
        with open(WORKSPACES_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_workspaces(workspaces):
    os.makedirs(os.path.dirname(WORKSPACES_FILE), exist_ok=True)
    with open(WORKSPACES_FILE, "w") as f:
        json.dump(workspaces, f, indent=4)

@app.context_processor
def inject_workspaces():
    all_workspaces = load_workspaces()
    if session.get('admin_logged_in'):
        username = session.get('username')
        role = session.get('role')
        if username == ADMIN_CREDENTIALS['username'] or role == 'super_admin':
            return dict(workspaces=all_workspaces)
            
        credentials = load_credentials()
        user = next((u for u in credentials if u['username'] == username), None)
        if user:
            if user.get('role') == 'super_admin':
                return dict(workspaces=all_workspaces)
                
            allowed_ws_ids = user.get('allowed_workspaces', [])
            allowed_mods = user.get('allowed_modules', {})
            filtered = []
            for ws in all_workspaces:
                if ws['id'] in allowed_ws_ids:
                    ws_copy = {
                        'id': ws['id'],
                        'name': ws['name'],
                        'enabled': ws['enabled'],
                        'modules': [m for m in ws['modules'] if m['name'] in allowed_mods.get(ws['id'], [])]
                    }
                    filtered.append(ws_copy)
            return dict(workspaces=filtered)
        return dict(workspaces=all_workspaces)
    elif session.get('teams_logged_in'):
        username = session.get('username')
        credentials = load_credentials()
        user = next((u for u in credentials if u['username'] == username), None)
        if user:
            allowed_ws_ids = user.get('allowed_workspaces', [])
            allowed_mods = user.get('allowed_modules', {})
            filtered = []
            for ws in all_workspaces:
                if ws['id'] in allowed_ws_ids:
                    ws_copy = {
                        'id': ws['id'],
                        'name': ws['name'],
                        'enabled': ws['enabled'],
                        'modules': [m for m in ws['modules'] if m['name'] in allowed_mods.get(ws['id'], [])]
                    }
                    filtered.append(ws_copy)
            return dict(workspaces=filtered)
        fallback_ws = []
        for ws in all_workspaces:
            if ws['id'] == 'administration':
                ws_copy = ws.copy()
                ws_copy['modules'] = [m for m in ws['modules'] if m['name'] == 'View Teams']
                fallback_ws.append(ws_copy)
        return dict(workspaces=fallback_ws)
    return dict(workspaces=[])

@app.route('/admin/workspaces', methods=['GET', 'POST'])
def manage_workspaces():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    username = session.get('username')
    role = session.get('role')
    
    # Only super admins can access workspaces manager
    if username != ADMIN_CREDENTIALS['username'] and role != 'super_admin':
        flash('Access Denied: Super Admin only.', 'error')
        return redirect(url_for('admin'))
    
    workspaces = load_workspaces()
    credentials = load_credentials()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            name = request.form.get('name', '').strip()
            
            if not name:
                flash('Workspace Name is required', 'error')
                return redirect(url_for('manage_workspaces'))
            
            ws_id = slugify(name)
            if any(w['id'] == ws_id for w in workspaces):
                flash(f'Workspace with ID "{ws_id}" already exists', 'error')
                return redirect(url_for('manage_workspaces'))
            
            new_ws = {
                'id': ws_id,
                'name': name,
                'enabled': True,
                'modules': []
            }
            workspaces.append(new_ws)
            save_workspaces(workspaces)
            flash('Workspace created successfully!', 'success')
            
        elif action == 'edit':
            ws_id = request.form.get('id', '').strip()
            name = request.form.get('name', '').strip()
            enabled = request.form.get('enabled') == 'true'
            
            ws = next((w for w in workspaces if w['id'] == ws_id), None)
            if ws:
                ws['name'] = name
                ws['enabled'] = enabled
                save_workspaces(workspaces)
                flash('Workspace updated successfully!', 'success')
            else:
                flash('Workspace not found', 'error')
                
        elif action == 'delete':
            ws_id = request.form.get('id', '').strip()
            workspaces = [w for w in workspaces if w['id'] != ws_id]
            save_workspaces(workspaces)
            flash('Workspace deleted successfully!', 'success')
            
        elif action == 'add_module':
            ws_id = request.form.get('id', '').strip()
            mod_name = request.form.get('mod_name', '').strip()
            mod_url = request.form.get('mod_url', '').strip()
            mod_icon = request.form.get('mod_icon', 'fas fa-link').strip()
            
            if not mod_name or not mod_url:
                flash('Module name and URL are required', 'error')
                return redirect(url_for('manage_workspaces'))
                
            ws = next((w for w in workspaces if w['id'] == ws_id), None)
            if ws:
                ws['modules'].append({
                    'name': mod_name,
                    'url': mod_url,
                    'icon': mod_icon
                })
                save_workspaces(workspaces)
                flash('Module added successfully!', 'success')
            else:
                flash('Workspace not found', 'error')
                
        elif action == 'delete_module':
            ws_id = request.form.get('id', '').strip()
            mod_name = request.form.get('mod_name', '').strip()
            
            ws = next((w for w in workspaces if w['id'] == ws_id), None)
            if ws:
                ws['modules'] = [m for m in ws['modules'] if m['name'] != mod_name]
                save_workspaces(workspaces)
                flash('Module deleted successfully!', 'success')
            else:
                flash('Workspace not found', 'error')
                
        elif action == 'create_credential':
            new_user = request.form.get('username', '').strip()
            new_pass = request.form.get('password', '').strip()
            new_role = request.form.get('role', 'custom').strip()
            
            if not new_user or not new_pass:
                flash('Username and Password are required', 'error')
                return redirect(url_for('manage_workspaces'))
                
            if any(u['username'].lower() == new_user.lower() for u in credentials):
                flash(f'Credential with username "{new_user}" already exists', 'error')
                return redirect(url_for('manage_workspaces'))
                
            if new_role == 'super_admin':
                allowed_ws = []
                allowed_mods = {}
            elif new_role == 'teams_viewer':
                allowed_ws = ["administration"]
                allowed_mods = {"administration": ["View Teams"]}
            else:
                allowed_ws = request.form.getlist('allowed_workspaces')
                allowed_mods = {}
                for ws_id in allowed_ws:
                    allowed_mods[ws_id] = request.form.getlist('allowed_modules_' + ws_id)
                    
            credentials.append({
                'username': new_user,
                'password': generate_password_hash(new_pass),
                'role': new_role,
                'allowed_workspaces': allowed_ws,
                'allowed_modules': allowed_mods
            })
            save_credentials(credentials)
            flash('Credential added successfully!', 'success')
            
        elif action == 'edit_credential':
            edit_user = request.form.get('username', '').strip()
            edit_pass = request.form.get('password', '').strip()
            edit_role = request.form.get('role', 'custom').strip()
            
            user = next((u for u in credentials if u['username'] == edit_user), None)
            if user:
                if edit_pass:
                    user['password'] = generate_password_hash(edit_pass)
                user['role'] = edit_role
                
                if edit_role == 'super_admin':
                    user['allowed_workspaces'] = []
                    user['allowed_modules'] = {}
                elif edit_role == 'teams_viewer':
                    user['allowed_workspaces'] = ["administration"]
                    user['allowed_modules'] = {"administration": ["View Teams"]}
                else:
                    allowed_ws = request.form.getlist('allowed_workspaces')
                    allowed_mods = {}
                    for ws_id in allowed_ws:
                        allowed_mods[ws_id] = request.form.getlist('allowed_modules_' + ws_id)
                    user['allowed_workspaces'] = allowed_ws
                    user['allowed_modules'] = allowed_mods
                    
                save_credentials(credentials)
                flash('Credential updated successfully!', 'success')
            else:
                flash('Credential not found', 'error')
                
        elif action == 'delete_credential':
            del_user = request.form.get('username', '').strip()
            if del_user == ADMIN_CREDENTIALS['username']:
                flash('Cannot delete default system administrator.', 'error')
            else:
                credentials = [u for u in credentials if u['username'] != del_user]
                save_credentials(credentials)
                flash('Credential deleted successfully!', 'success')
                
        return redirect(url_for('manage_workspaces'))
        
    return render_template('admin_workspaces.html', workspaces=workspaces, credentials=credentials)
    
@app.route('/get_team_details')
def get_team_details():
    if not session.get('admin_logged_in') and not session.get('teams_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    team_id = request.args.get('team_id')
    if not team_id:
        return jsonify({'error': 'Team ID required'}), 400
    
    with open(DATABASE_FILE, 'r') as f:
        data = json.load(f)
        team = next((t for t in data['teams'] if t['team_id'] == team_id), None)
        if not team:
            return jsonify({'error': 'Team not found'}), 404
        
        return jsonify(team)

@app.route('/api/teams')
def get_teams_api():
    try:
        with open(DATABASE_FILE, 'r') as f:
            data = json.load(f)
        return jsonify({'teams': data.get('teams', [])})
    except:
        return jsonify({'teams': []})


@app.route('/message-center', methods=['GET', 'POST'])
def message_center():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        recipients_type = request.form.get('recipients_type', 'all')
        
        if not subject or not message:
            flash('Subject and message are required', 'error')
            return redirect(url_for('message_center'))
        
        # Get recipients based on type
        recipients = []
        with open(DATABASE_FILE, 'r') as f:
            data = json.load(f)
            for team in data.get('teams', []):
                if recipients_type == 'all' or \
                   (recipients_type == 'paid' and team.get('payment_verified')) or \
                   (recipients_type == 'unpaid' and not team.get('payment_verified')):
                    for member in team.get('members', []):
                        if member.get('email'):
                            recipients.append({
                                'name': member.get('name'),
                                'email': member.get('email'),
                                'team': team.get('team_name'),
                                'team_id': team.get('team_id')
                            })
        
        if not recipients:
            flash('No recipients found for the selected criteria', 'warning')
            return redirect(url_for('message_center'))
        
        # Handle file attachments
        attachments = []
        if 'attachments' in request.files:
            for file in request.files.getlist('attachments'):
                if file.filename != '':
                    if not allowed_file(file.filename):
                        flash(f'File type not allowed: {file.filename}', 'error')
                        continue
                    
                    file_data = file.read()
                    attachments.append({
                        'filename': secure_filename(file.filename),
                        'content_type': file.content_type,
                        'data': file_data
                    })
        
        # Create email log entry
        email_log = {
            'id': str(uuid.uuid4()),
            'subject': subject,
            'message': message,
            'recipients_type': recipients_type,
            'total_recipients': len(recipients),
            'sent_by': session.get('admin_id', 'unknown'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'recipients': recipients[:100],
            'attachments': [{'filename': a['filename']} for a in attachments] if attachments else []
        }
        
        # Save to email logs
        try:
            email_logs = []
            if os.path.exists(EMAIL_LOGS_FILE):
                with open(EMAIL_LOGS_FILE, 'r') as f:
                    email_logs = json.load(f)
            
            email_logs.append(email_log)
            
            with open(EMAIL_LOGS_FILE, 'w') as f:
                json.dump(email_logs, f, indent=4)
        except Exception as e:
            app.logger.error(f"Failed to save email log: {str(e)}")
        
        # Send emails in background thread
        def send_messages():
            with app.app_context():
                sent_count = 0
                for recipient in recipients:
                    try:
                        # Create attachments HTML if there are attachments
                        attachments_html = ""
                        if attachments:
                            attachments_list = ""
                            for attachment in attachments:
                                file_ext = attachment['filename'].split('.')[-1].lower() if '.' in attachment['filename'] else 'file'
                                attachments_list += f"""
                                <div class="attachment-item">
                                    <i class="fas fa-file-{file_ext}"></i>
                                    <span class="filename">{attachment['filename']}</span>
                                    <span class="filesize">({len(attachment['data'])} bytes)</span>
                                </div>
                                """
                            
                            attachments_html = f"""
                            <div class="attachments-section">
                                <div class="attachments-title">
                                    <i class="fas fa-paperclip"></i> Attachments ({len(attachments)})
                                </div>
                                {attachments_list}
                            </div>
                            """
                        
                        # Professional HTML email with SAMISTI aesthetic
                        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>{subject} - Creator Club</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        /* Reset styles */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }}
        
        body {{
            background-color: #f4f7fc;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }}
        
        .email-wrapper {{
            max-width: 600px;
            margin: 20px auto;
            background-color: #ffffff;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 20px 40px rgba(0,0,0,0.08);
        }}
        
        /* Header - SAMISTI style */
        .email-header {{
            background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
            padding: 30px 20px;
            text-align: center;
            border-bottom: 4px solid #c41e3a;
        }}
        
        .logo-container {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        
        .logo {{
            height: 60px;
            width: auto;
            object-fit: contain;
            filter: drop-shadow(0 4px 6px rgba(0,0,0,0.2));
        }}
        
        .club-badge {{
            background: #c41e3a;
            color: white;
            padding: 6px 16px;
            border-radius: 40px;
            font-size: 0.9rem;
            font-weight: 500;
            display: inline-block;
        }}
        
        .email-title {{
            font-size: 28px;
            font-weight: 700;
            color: white;
            margin: 15px 0 5px;
            letter-spacing: -0.5px;
            word-break: break-word;
        }}
        
        .recipient-info {{
            color: rgba(255,255,255,0.8);
            font-size: 15px;
            margin-top: 10px;
        }}
        
        .recipient-info i {{
            color: #c41e3a;
            margin-right: 5px;
        }}
        
        /* Content */
        .email-content {{
            padding: 30px 25px;
        }}
        
        /* Greeting */
        .greeting {{
            font-size: 18px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #eaeaea;
        }}
        
        .greeting strong {{
            color: #c41e3a;
        }}
        
        /* Message card */
        .message-card {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 25px;
            margin: 20px 0;
            border-left: 4px solid #c41e3a;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        }}
        
        .message-content {{
            font-size: 16px;
            color: #1a1a1a;
            line-height: 1.8;
            white-space: pre-line;
        }}
        
        /* Attachments section */
        .attachments-section {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
        }}
        
        .attachments-title {{
            font-size: 16px;
            font-weight: 600;
            color: #1a1a1a;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .attachments-title i {{
            color: #c41e3a;
        }}
        
        .attachment-item {{
            background: white;
            border-radius: 8px;
            padding: 12px 15px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
            border: 1px solid #eaeaea;
        }}
        
        .attachment-item i {{
            color: #c41e3a;
            font-size: 20px;
        }}
        
        .attachment-item .filename {{
            font-weight: 500;
            color: #1a1a1a;
            flex: 1;
            word-break: break-word;
        }}
        
        .attachment-item .filesize {{
            color: #999;
            font-size: 13px;
        }}
        
        /* Contact card */
        .contact-card {{
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            border: 1px solid #eaeaea;
        }}
        
        .contact-card h4 {{
            color: #1a1a1a;
            margin-bottom: 15px;
            font-size: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .contact-card h4 i {{
            color: #c41e3a;
        }}
        
        .contact-details {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        
        .contact-details p {{
            display: flex;
            align-items: center;
            gap: 10px;
            color: #666;
            margin: 0;
            flex-wrap: wrap;
        }}
        
        .contact-details i {{
            color: #c41e3a;
            width: 20px;
        }}
        
        .contact-details a {{
            color: #c41e3a;
            text-decoration: none;
            font-weight: 500;
        }}
        
        .contact-details a:hover {{
            text-decoration: underline;
        }}
        
        /* Footer - SAMISTI style */
        .email-footer {{
            background: #1a1a1a;
            padding: 30px 20px;
            color: white;
            text-align: center;
        }}
        
        .footer-logos {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 30px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        
        .footer-logo {{
            height: 50px;
            width: auto;
            object-fit: contain;
            filter: brightness(0) invert(1);
        }}
        
        .club-info {{
            margin: 20px 0;
        }}
        
        .club-info h4 {{
            font-size: 18px;
            margin-bottom: 10px;
            color: white;
        }}
        
        .social-links {{
            display: flex;
            justify-content: center;
            gap: 15px;
            flex-wrap: wrap;
            margin: 20px 0;
        }}
        
        .social-link {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            color: white;
            text-decoration: none;
            padding: 8px 16px;
            background: rgba(255,255,255,0.1);
            border-radius: 40px;
            transition: all 0.3s ease;
        }}
        
        .social-link:hover {{
            background: #c41e3a;
            color: white;
            transform: translateY(-2px);
        }}
        
        .developer-credit {{
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0 10px;
        }}
        
        .developer-credit p {{
            color: #ccc;
            font-size: 13px;
            margin: 5px 0;
        }}
        
        .developer-credit strong {{
            color: #c41e3a;
        }}
        
        .copyright {{
            color: #999;
            font-size: 13px;
            margin-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.1);
            padding-top: 20px;
        }}
        
        /* Responsive styles */
        @media only screen and (max-width: 480px) {{
            .email-content {{
                padding: 20px 15px;
            }}
            
            .logo {{
                height: 50px;
            }}
            
            .email-title {{
                font-size: 22px;
            }}
            
            .greeting {{
                font-size: 16px;
            }}
            
            .message-card {{
                padding: 20px;
            }}
            
            .message-content {{
                font-size: 15px;
            }}
            
            .attachment-item {{
                flex-wrap: wrap;
            }}
            
            .social-links {{
                flex-direction: column;
                gap: 10px;
            }}
            
            .social-link {{
                width: 100%;
                justify-content: center;
            }}
            
            .contact-details p {{
                flex-wrap: wrap;
            }}
        }}
        
        @media only screen and (max-width: 360px) {{
            .logo-container {{
                gap: 10px;
            }}
            
            .logo {{
                height: 40px;
            }}
            
            .club-badge {{
                font-size: 0.8rem;
                padding: 4px 12px;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <!-- Header -->
        <div class="email-header">
            <div class="logo-container">
                <img src="https://res.cloudinary.com/dvfqvqbkn/image/upload/v1752482945/clglogo_rqnxum.png" alt="Sphoorthy Engineering College" class="logo">
                <img src="https://res.cloudinary.com/dvfqvqbkn/image/upload/v1752482876/cc_lbohfd.png" alt="Creators Club" class="logo">
            </div>
            <span class="club-badge">Official Communication</span>
            <h1 class="email-title">{subject}</h1>
            <div class="recipient-info">
                <i class="fas fa-user"></i> {recipient['name']} · 
                <i class="fas fa-users"></i> Team {recipient['team']}
            </div>
        </div>
        
        <!-- Content -->
        <div class="email-content">
            <!-- Greeting -->
            <div class="greeting">
                Dear <strong>{recipient['name']}</strong>,
            </div>
            
            <!-- Main Message -->
            <div class="message-card">
                <div class="message-content">
                    {message}
                </div>
            </div>
            
            <!-- Attachments (if any) -->
            {attachments_html}
            
            <!-- Contact Information -->
            <div class="contact-card">
                <h4><i class="fas fa-headset"></i> Need Assistance?</h4>
                <div class="contact-details">
                   
                   
                    <p>
                        <i class="fas fa-envelope"></i>
                        <a href="mailto:creator_club@sphoorthyengg.ac.in">creator_club@sphoorthyengg.ac.in</a>
                    </p>
                    <p>
                        <i class="fab fa-instagram"></i>
                        <a href="https://instagram.com/creator_club_official">@creator_club_official</a>
                    </p>
                   
                </div>
            </div>
            
            <!-- Note -->
            <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin-top: 20px;">
                <i class="fas fa-info-circle" style="color: #856404; margin-right: 8px;"></i>
                <span style="color: #856404; font-size: 14px;">
                    This is an official communication from Creator Club. Please do not reply directly to this email.
                </span>
            </div>
        </div>
        
        <!-- Footer -->
        <div class="email-footer">
            <div class="footer-logos">
                <img src="https://res.cloudinary.com/dvfqvqbkn/image/upload/v1752482945/clglogo_rqnxum.png" alt="College Logo" class="footer-logo">
                <img src="https://res.cloudinary.com/dvfqvqbkn/image/upload/v1752482876/cc_lbohfd.png" alt="Club Logo" class="footer-logo">
            </div>
            
            <div class="club-info">
                <h4>Creator Club | Sphoorthy Engineering College</h4>
            </div>
            
            <div class="social-links">
                <a href="https://instagram.com/creator_club_official" target="_blank" class="social-link">
                    <i class="fab fa-instagram"></i> Instagram
                </a>
                <a href="https://wa.me/919059160424" target="_blank" class="social-link">
                    <i class="fab fa-whatsapp"></i> WhatsApp
                </a>
                <a href="mailto:creator_club@sphoorthyengg.ac.in" class="social-link">
                    <i class="fas fa-envelope"></i> Email
                </a>
            </div>
            
            <div class="copyright">
                &copy; {datetime.now().year} Creator Club. All rights reserved.<br>
                <span style="font-size: 11px;">Team ID: {recipient['team_id']} · {recipient['email']}</span>
            </div>
        </div>
    </div>
</body>
</html>
                        """

                        # Plain text version
                        text_content = f"""
╔══════════════════════════════════════════════════════════════╗
║                    {subject}                                  ║
║                    Creator Club | Sphoorthy Engineering College ║
╚══════════════════════════════════════════════════════════════╝

Dear {recipient['name']} (Team {recipient['team']}),

{message}

════════════════════════════════════════════════════════════════
CONTACT INFORMATION
════════════════════════════════════════════════════════════════
For any queries, contact:
📞 Phone: +91 9059160424
📧 Email: creator_club@sphoorthyengg.ac.in
📱 Instagram: @creator_club_official


{f'''
════════════════════════════════════════════════════════════════
ATTACHMENTS
════════════════════════════════════════════════════════════════
{chr(10).join(f'📎 {attachment["filename"]}' for attachment in attachments)}
''' if attachments else ''}

This is an official communication from Creator Club.
Please do not reply directly to this email.

════════════════════════════════════════════════════════════════
Team ID: {recipient['team_id']}
Email: {recipient['email']}

© {datetime.now().year} Creator Club. All rights reserved.
                        """

                        msg = Message(
                            subject=f"📢 {subject} - Creator Club",
                            recipients=[recipient['email']],
                            body=text_content,
                            html=html_content
                        )
                        
                        # Add attachments
                        for attachment in attachments:
                            msg.attach(
                                filename=attachment['filename'],
                                content_type=attachment['content_type'],
                                data=attachment['data'],
                                disposition='attachment'
                            )
                        
                        mail.send(msg)
                        sent_count += 1
                        app.logger.info(f"✓ Message sent successfully to {recipient['email']}")
                        
                    except Exception as e:
                        app.logger.error(f"❌ Failed to send to {recipient['email']}: {str(e)}")
                        log_email(recipient['team_id'], 'message_center', recipient['email'], False, str(e))
                
                # Update log with actual sent count
                try:
                    if os.path.exists(EMAIL_LOGS_FILE):
                        with open(EMAIL_LOGS_FILE, 'r') as f:
                            email_logs = json.load(f)
                        
                        for log in reversed(email_logs):
                            if log['id'] == email_log['id']:
                                log['actually_sent'] = sent_count
                                log['success_rate'] = f"{sent_count}/{len(recipients)}"
                                break
                        
                        with open(EMAIL_LOGS_FILE, 'w') as f:
                            json.dump(email_logs, f, indent=4)
                except Exception as e:
                    app.logger.error(f"Failed to update email log: {str(e)}")
        
        threading.Thread(target=send_messages).start()
        
        flash(f'📧 Message is being sent to {len(recipients)} recipients', 'success')
        return redirect(url_for('message_center'))
    
    # Load email history for display
    email_history = []
    try:
        if os.path.exists(EMAIL_LOGS_FILE):
            with open(EMAIL_LOGS_FILE, 'r') as f:
                email_history = json.load(f)
                email_history.reverse()  # Show newest first
                
                # Add some stats
                total_sent = sum(log.get('actually_sent', log.get('total_recipients', 0)) for log in email_history)
                app.logger.info(f"📊 Loaded {len(email_history)} email logs, total messages sent: {total_sent}")
    except Exception as e:
        app.logger.error(f"Failed to load email history: {str(e)}")
    
    return render_template('message_center.html', email_history=email_history)



@app.route('/resend-email/<email_id>', methods=['POST'])
def resend_email(email_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        with open(EMAIL_LOGS_FILE, 'r') as f:
            email_logs = json.load(f)
        
        email_to_resend = next((e for e in email_logs if e['id'] == email_id), None)
        
        if not email_to_resend:
            return jsonify({'success': False, 'message': 'Email not found'}), 404
        
        # Send emails in background thread
        def send_messages():
            with app.app_context():
                sent_count = 0
                for recipient in email_to_resend.get('recipients', []):
                    try:
                        msg = Message(
                            subject=f"Resent: {email_to_resend['subject']}",
                            recipients=[recipient['email']],
                            html=render_template(
                                'email_message.html',
                                subject=email_to_resend['subject'],
                                message=email_to_resend['message'],
                                recipient=recipient
                            )
                        )
                        
                        # If you want to include original attachments in resend,
                        # you would need to store them differently (not in this example)
                        
                        mail.send(msg)
                        sent_count += 1
                    except Exception as e:
                        app.logger.error(f"Failed to resend to {recipient['email']}: {str(e)}")
                
                # Create new log entry for the resend
                new_log = {
                    'id': str(uuid.uuid4()),
                    'subject': f"Resent: {email_to_resend['subject']}",
                    'message': email_to_resend['message'],
                    'recipients_type': 'resend-' + email_to_resend['id'],
                    'total_recipients': len(email_to_resend.get('recipients', [])),
                    'actually_sent': sent_count,
                    'sent_by': session.get('admin_id', 'unknown') + ' (resend)',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'original_email_id': email_id,
                    'attachments': email_to_resend.get('attachments', [])
                }
                
                try:
                    email_logs.append(new_log)
                    with open(EMAIL_LOGS_FILE, 'w') as f:
                        json.dump(email_logs, f, indent=4)
                except Exception as e:
                    app.logger.error(f"Failed to save resend log: {str(e)}")
        
        threading.Thread(target=send_messages).start()
        
        return jsonify({'success': True, 'message': 'Email is being resent'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit


if __name__ == '__main__':
    app.run(debug=True, port=5003)