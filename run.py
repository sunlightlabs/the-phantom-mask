from app import phantom_mask

application = phantom_mask.route_app(phantom_mask.create_app())

if __name__ == '__main__':
    application.run()


#gunicorn -w 4 run:app --daemon