from flask import Flask, redirect, url_for
from config.config import DEBUG  # Đảm bảo DEBUG tồn tại trong config.py
from routes.home_routes import register_home_routes
from routes.form_routes import register_form_routes
from routes.docx_routes import register_docx_routes
from routes import register_routes
from flask_login import LoginManager
from models.user import User, db
import nltk
import os

# Khởi tạo ứng dụng Flask
app = Flask(__name__)

# Cấu hình cơ sở dữ liệu (Thay thế bằng URI thật của bạn)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'  # Hoặc PostgreSQL/MySQL URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-secret-key-here'  # Thêm secret key cho session

# Khởi tạo database với Flask app
db.init_app(app)

# Đảm bảo có một app context khi truy vấn DB
with app.app_context():
    db.create_all()
    # Khởi tạo các vai trò
    from models.user import Role
    Role.insert_roles()

# Cấu hình Flask-Login
login_manager = LoginManager() 
login_manager.init_app(app)
login_manager.login_view = 'login'  # Đặt view đăng nhập mặc định

@login_manager.user_loader
def load_user(user_id):
    with app.app_context():
        # Use query.get instead of session.get to ensure the object stays attached to the session
        return db.session.get(User, int(user_id))

# Đảm bảo các tài nguyên NLTK được tải xuống
# def ensure_nltk_resources():
#     resources = {
#         'punkt_tab': 'tokenizers/punkt_tab',
#         'stopwords': 'corpora/stopwords', 
#         'wordnet': 'corpora/wordnet',
#         'omw-1.4': 'corpora/omw-1.4'  # Cần thiết cho WordNetLemmatizer
#     }
#     for resource, path in resources.items():
#         try:
#             nltk.data.find(path)
#             print(f"Resource {resource} already exists.")
#         except LookupError:
#             try:
#                 print(f"Downloading {resource} resource...")
#                 nltk.download(resource, quiet=True)
#                 print(f"Downloaded {resource} successfully!")
#             except Exception as e:
#                 print(f"Error downloading {resource}: {e}")
#                 print(f"Please manually download {resource} using: nltk.download('{resource}')")

# # Tải các resource cần thiết
# ensure_nltk_resources()

# Đăng ký các route
register_routes(app)

def run_app():
    app.run(host='0.0.0.0', debug=DEBUG)

if __name__ == '__main__':
    run_app()
