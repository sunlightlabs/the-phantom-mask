import os
from app import phantom_mask

application = phantom_mask.config_ext(phantom_mask.create_app())

if __name__ == '__main__':
    os.environ['PROJECT_DIR'] = os.path.dirname(os.path.abspath(__file__))
    os.chdir(os.environ['PROJECT_DIR'])
    os.system('bin/deploy.sh start_celery')
    application.run()