from flask import render_template, request, jsonify
from utils.document_utils import load_document, extract_fields, get_doc_path, set_doc_path
from utils.ai_utils import generate_suggestions, get_gpt_suggestions
from models.data_model import load_db, save_db, load_form_history, save_form_history
import os

def register_form_routes(app):
    """
    Đăng ký các route cho biểu mẫu
    """
    @app.route('/form')
    def form():
        doc_path = get_doc_path()
        if not doc_path:
            return jsonify({'error': 'No document uploaded'}), 400
            
        text = load_document(doc_path)
        fields = extract_fields(text)
        db_data = load_db()
        
        suggestions = generate_suggestions(db_data) if db_data else {}
        
        return render_template("index.html", fields=fields, suggestions=suggestions)
    
    @app.route('/submit', methods=['POST'])
    def submit():
        try:
            form_data = request.form.to_dict()
            if not form_data:
                return jsonify({"error": "Không có dữ liệu được gửi"}), 400
            
            # Tạo form_id unique
            import uuid
            form_id = str(uuid.uuid4())
            
            # Lấy document path hiện tại
            doc_path = get_doc_path()
            if not doc_path:
                return jsonify({"error": "Không tìm thấy tài liệu"}), 400
                
            # Tải nội dung tài liệu và trích xuất các trường
            text = load_document(doc_path)
            fields = extract_fields(text)
            
            # Tạo dictionary mới với field_name và giá trị
            transformed_data = {
                "form_id": form_id,
                "document_name": form_data.get('document_name', '')
            }
            
            # Lưu trực tiếp field_name và value
            for field in fields:
                field_code = field['field_code']
                field_name = field['field_name']
                if field_code in form_data:
                    transformed_data[field_name] = form_data[field_code]
            
            # Lưu vào form history
            try:
                from flask_login import current_user
                form_history = load_form_history()
                
                form_entry = {
                    "form_id": form_id,
                    "path": doc_path,
                    "form_data": transformed_data,
                    "timestamp": __import__('datetime').datetime.now().isoformat(),
                    "user_id": current_user.id if current_user.is_authenticated else None,
                    "user_name": current_user.fullname if current_user.is_authenticated else None
                }
                
                form_history.append(form_entry)
                save_form_history(form_history)
                
                return jsonify({
                    "message": "Lưu thông tin thành công",
                    "form_id": form_id
                })
                
            except Exception as e:
                print(f"Error saving form history: {str(e)}")
                return jsonify({"error": "Có lỗi xảy ra khi lưu lịch sử"}), 500
                
        except Exception as e:
            print(f"Error submitting form: {str(e)}")
            return jsonify({"error": "Có lỗi xảy ra khi lưu dữ liệu"}), 500
    
    @app.route('/get_suggestions', methods=['POST'])
    def get_suggestions():
        field_code = request.json.get('field_code')
        if not field_code:
            return jsonify({'error': 'Field code is required'}), 400

        db_data = load_db()
        suggestions = generate_suggestions(db_data, field_code)

        return jsonify({'field_code': field_code, 'suggestions': suggestions})
    
    @app.route('/get_gpt_suggestions', methods=['POST'])
    def get_gpt_suggestions_route():
        field_code = request.json.get('field_code')
        if not field_code:
            return jsonify({'error': 'Field code is required'}), 400

        result, status_code = get_gpt_suggestions(field_code)
        return jsonify(result), status_code
    
    @app.route('/form/<form_id>')
    def view_form(form_id):
        try:
            form_history = load_form_history()
            clean_form_id = form_id.replace('_test', '')
            
            # Tìm form theo form_id
            form_data = None
            form_path = None
            
            for form in form_history:
                file_name = os.path.basename(form['path'])
                file_id = file_name.split('_')[0]
                
                if file_id == clean_form_id:
                    form_data = form.get('form_data')
                    form_path = form['path']
                    break
            
            if not form_data or not form_path:
                return jsonify({'error': 'Không tìm thấy biểu mẫu'}), 404
                
            # Set document path và load fields
            set_doc_path(form_path)
            text = load_document(form_path)
            fields = extract_fields(text)
            
            # Gán giá trị trực tiếp từ form_data vào fields
            for field in fields:
                field_name = field['field_name']
                field['value'] = form_data.get(field_name, '')
            
            # Get suggestions
            db_data = load_db()
            suggestions = generate_suggestions(db_data) if db_data else {}
            
            return render_template(
                "index.html",
                fields=fields,
                suggestions=suggestions,
                form_data=form_data,
                document_name=form_data.get('document_name', '')
            )
            
        except Exception as e:
            print(f"Error loading form: {str(e)}")
            return jsonify({'error': f'Không thể tải biểu mẫu: {str(e)}'}), 500
    
    @app.route('/delete-form/<form_id>', methods=['DELETE'])
    def delete_form(form_id):
        try:
            # Load form history
            form_history = load_form_history()
            
            # Find the form with the matching ID
            form_index = None
            for i, form in enumerate(form_history):
                # Lấy ID từ đường dẫn file
                file_name = os.path.basename(form['path'])
                file_id = file_name.split('_')[0] if '_' in file_name else file_name.split('.')[0]
                
                # So sánh với form_id được truyền vào
                if file_id == form_id or file_name.startswith(form_id):
                    form_index = i
                    break
            
            if form_index is None:
                return jsonify({'error': 'Form not found'}), 404
            
            # Xóa form khỏi lịch sử
            deleted_form = form_history.pop(form_index)
            save_form_history(form_history)
            
            # Xóa file nếu cần
            try:
                if os.path.exists(deleted_form['path']) and os.path.isfile(deleted_form['path']):
                    # Chỉ xóa file nếu nó nằm trong thư mục uploads
                    from config.config import UPLOADS_DIR
                    if UPLOADS_DIR in deleted_form['path']:
                        os.remove(deleted_form['path'])
            except Exception as e:
                print(f"Warning: Could not delete file: {str(e)}")
            
            return jsonify({'message': 'Form deleted successfully'})
            
        except Exception as e:
            print(f"Error deleting form: {str(e)}")
            return jsonify({'error': 'Failed to delete form'}), 500