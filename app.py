from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import check_password_hash

app = Flask(__name__)

# Set up the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hopehub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key'  # for session management

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Create a user model for the database
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Assuming you will hash the password
    role = db.Column(db.String(50), nullable=False, default='user')  # Role can be 'user' or 'admin'
    
    def __repr__(self):
        return f'<User {self.username}>'

    def is_admin(self):
        return self.role == 'admin'

# Create a resource model for the database
class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(300), nullable=True)
    category = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<Resource {self.name}>'

# Create a job model for the database
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    company = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    apply_link = db.Column(db.String(300), nullable=True)

    def __repr__(self):
        return f'<Job {self.title}>'


@app.before_request
def load_logged_in_user():
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])
    else:
        g.user = None

# Home route
@app.route('/')
def home():
    return render_template('home.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']  # Plain text password entered by the user
        
        # Query the database for the user by username
        user = User.query.filter_by(username=username).first()

        # Directly compare the plain text password (this is NOT secure for production)
        if user and user.password == password:  # Direct comparison of plain text passwords
            session['user_id'] = user.id  # Store user ID in the session
            return redirect(url_for('dashboard'))  # Redirect to the dashboard
        else:
            flash('Invalid credentials', 'danger')  # Show an error message if credentials are incorrect

    return render_template('login.html')

# Create Account route
@app.route('/create-account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists. Please choose a different one.", "error")
            return redirect(url_for('create_account'))

        try:
            # Create a new user
            new_user = User(username=username, password=password, email=email)
            db.session.add(new_user)
            db.session.commit()
            flash("Account created successfully. Please log in.", "success")
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash("An error occurred while creating the account. Please try again.", "error")
            return redirect(url_for('create_account'))

    return render_template('create_account.html')

# Dashboard route
@app.route('/home')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    print(f"Session user_id: {session['user_id']}")
    user = User.query.get(session['user_id'])
    return render_template('home.html', user=user)

#Job Finder
@app.route('/job-finder', methods=['GET', 'POST'])
def job_finder():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Get distinct categories from the database
    categories = db.session.query(Job.category).distinct().all()

    # Convert categories from list of tuples to a simple list
    category_list = [category[0] for category in categories]

    # Filter jobs by category if it's provided, otherwise show all jobs
    category = request.form.get('category')
    if category:
        jobs_list = Job.query.filter_by(category=category).all()
    else:
        jobs_list = Job.query.all()

    return render_template('job_finder.html', jobs=jobs_list, categories=category_list)


# Helper function to fetch a job by ID
def get_job_by_id(job_id):
    job = Job.query.get(job_id)
    if not job:
        return None
    return job


# Function to check if user is admin
def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.username == 'admin'  # Assuming admin username is 'admin'



# View application details
@app.route('/application/<int:application_id>', methods=['GET'])
def application_details(application_id):
    application = Application.query.get(application_id)
    if not application:
        return "Application not found", 404

    job = Job.query.get(application.job_id)
    if not job:
        return "Job details not found", 404

    # Provide a link to edit the application
    return render_template(
        'confirmation.html',
        application=application,
        job=job
    )



# Resources route
@app.route('/resources')
def resources():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    resources_list = Resource.query.all()
    return render_template('resources.html', resources=resources_list)

# Submit Resource route
@app.route('/submit-resource', methods=['GET', 'POST'])
def submit_resource():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        link = request.form['link']
        category = request.form['category'].upper()

        new_resource = Resource(name=name, description=description, link=link, category=category)
        db.session.add(new_resource)
        db.session.commit()

        return redirect(url_for('resources'))

    return render_template('submit_resource.html')


# View All Jobs
@app.route('/admin/jobs')
def manage_jobs():
    jobs = Job.query.all()
    return render_template('manage_jobs.html', jobs=jobs)

# Add Job
@app.route('/admin/jobs/add', methods=['GET', 'POST'])
def add_job():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        location = request.form['location']
        company = request.form['company']
        category = request.form['category'].upper()
        apply_link = request.form['apply_link']
        
        new_job = Job(
            title=title, description=description, location=location,
            company=company, category=category, apply_link=apply_link
        )
        db.session.add(new_job)
        db.session.commit()
        flash('Job added successfully', 'success')
        return redirect(url_for('manage_jobs'))
    return render_template('add_job.html')

# Edit Job
@app.route('/admin/jobs/edit/<int:job_id>', methods=['GET', 'POST'])
def edit_job(job_id):
    job = Job.query.get(job_id)
    if not job:
        return "Job not found", 404
    if request.method == 'POST':
        job.title = request.form['title']
        job.description = request.form['description']
        job.location = request.form['location']
        job.company = request.form['company']
        job.category = request.form['category']
        job.apply_link = request.form['apply_link']
        db.session.commit()
        flash('Job updated successfully', 'success')
        return redirect(url_for('manage_jobs'))
    return render_template('edit_job.html', job=job)

# Delete Job
@app.route('/admin/jobs/delete/<int:job_id>', methods=['POST'])
def delete_job(job_id):
    job = Job.query.get(job_id)
    if job:
        db.session.delete(job)
        db.session.commit()
        flash('Job deleted successfully', 'success')
    return redirect(url_for('manage_jobs'))

# View All Resources
@app.route('/admin/resources')
def manage_resources():
    resources = Resource.query.all()
    return render_template('manage_resources.html', resources=resources)

# Add Resource
@app.route('/admin/resources/add', methods=['GET', 'POST'])
def add_resource():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        link = request.form['link']
        category = request.form['category']
        
        new_resource = Resource(
            name=name, description=description, link=link, category=category
        )
        db.session.add(new_resource)
        db.session.commit()
        flash('Resource added successfully', 'success')
        return redirect(url_for('manage_resources'))
    return render_template('add_resource.html')

# Edit Resource
@app.route('/admin/resources/edit/<int:resource_id>', methods=['GET', 'POST'])
def edit_resource(resource_id):
    resource = Resource.query.get(resource_id)
    if not resource:
        return "Resource not found", 404
    if request.method == 'POST':
        resource.name = request.form['name']
        resource.description = request.form['description']
        resource.link = request.form['link']
        resource.category = request.form['category']
        db.session.commit()
        flash('Resource updated successfully', 'success')
        return redirect(url_for('manage_resources'))
    return render_template('edit_resource.html', resource=resource)

# Delete Resource
@app.route('/admin/resources/delete/<int:resource_id>', methods=['POST'])
def delete_resource(resource_id):
    resource = Resource.query.get(resource_id)
    if resource:
        db.session.delete(resource)
        db.session.commit()
        flash('Resource deleted successfully', 'success')
    return redirect(url_for('manage_resources'))

@app.route('/policy', methods=['GET'])
def policy():
    return render_template('privacy_policy.html')

@app.route('/about', methods=['GET'])
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET'])
def contact():
    return render_template('contact.html')
# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

