from app import create_app, db
from app.models import User, Sample, ExperimentRecord, MLModel, OptimizationReport
import os

app = create_app()
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Sample': Sample,
        'ExperimentRecord': ExperimentRecord,
        'MLModel': MLModel,
        'OptimizationReport': OptimizationReport
    }

if __name__ == '__main__':
    # 确保必要的目录存在
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('models', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    with app.app_context():
        db.create_all()
    
    app.run(debug=True, host='0.0.0.0', port=5001)

