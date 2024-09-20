from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__, static_folder='pic')
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///votes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# 定义文件夹路径
pic_folder = "pic"

# 获取所有文件夹名称
folders = sorted([f for f in os.listdir(app.static_folder) if os.path.isdir(os.path.join(app.static_folder, f))])

# 初始化投票结果
votes = {folder: {f"{i+1}.png": 0 for i in range(6)} for folder in folders}

# 用户模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)

# 投票记录模型
class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    folder_name = db.Column(db.String(80), nullable=False)
    option_name = db.Column(db.String(80), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    voted_folders = [vote.folder_name for vote in Vote.query.filter_by(user_id=current_user.id).all()]
    return render_template('index.html', folders=folders, voted_folders=voted_folders)

@app.route('/folder/<folder_name>')
@login_required
def folder(folder_name):
    options = sorted([f for f in os.listdir(os.path.join(app.static_folder, folder_name)) if f.endswith(".png")])
    return render_template('folder.html', folder_name=folder_name, options=options)

@app.route('/vote', methods=['POST'])
@login_required
def vote():
    folder_name = request.form['folder']
    option_name = request.form['option']
    
    # 检查用户是否已经投过票
    existing_vote = Vote.query.filter_by(user_id=current_user.id, folder_name=folder_name).first()
    if existing_vote:
        return jsonify({'error': '您已经为这个文件夹投过票了。'}), 400
    
    # 记录投票结果
    votes[folder_name][option_name] += 1
    
    # 保存投票结果到文件
    with open("votes.txt", "a") as vote_file:
        vote_file.write(f"{folder_name}/{option_name}\n")
    
    # 保存投票记录到数据库
    new_vote = Vote(user_id=current_user.id, folder_name=folder_name, option_name=option_name)
    db.session.add(new_vote)
    db.session.commit()
    
    return jsonify({'success': '感谢您的投票!'}), 200

@app.route('/results')
@login_required
def results():
    return render_template('results.html', votes=votes)

@app.route('/all_results')
@login_required
def all_results():
    # 统计所有投票结果
    all_votes = {}
    for folder in folders:
        all_votes[folder] = {}
        for i in range(1, 7):
            option_name = f"{i}.png"
            count = Vote.query.filter_by(folder_name=folder, option_name=option_name).count()
            all_votes[folder][option_name] = count
    
    return render_template('all_results.html', all_votes=all_votes)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误。', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('用户名已存在。', 'error')
        else:
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash('注册成功，请登录。', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

def create_tables():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    create_tables()
    app.run(debug=True)