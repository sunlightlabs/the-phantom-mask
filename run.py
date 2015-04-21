from app import phantom_mask

application = phantom_mask.config_ext(phantom_mask.create_app())

if __name__ == '__main__':
    application.run()