# The Phantom Mask

Lightweight Flask web app to courier email messages via [Postmark](https://postmarkapp.com/) to be processed by an instance of [Phantom of the Capitol](https://github.com/EFForg/phantom-of-the-capitol).

## Installation and Setup

This project is still a work in progress so the README will be updated as it finalizes. In the meantime, you can get a working development environment set up by doing the following.

### App Setup

1. Clone the project
2. Create a virtul environment for Python 2.7.8
3. `pip install -r requirements.txt`
4. `mv config/settings.py.example config/settings.py` **YOU WILL NEED TO CONFIG THIS**
5. Set values for API keys, url for your instance of Phantom of the Capitol, etc in `config/settings.py`
6. `python tasks/admin.py setup_test_environment` to create initial schema for database & create test data
7. `python run.py` to run app locally for development. 
8. Check out `bin/deploy.sh` and `fabfile.py` for deploying to a production environment.

You will also need to do the following to fully set up the project:

#### PHANTOM OF THE CAPITOL SERVER SETUP

1. Follow instructions on [https://github.com/EFForg/phantom-of-the-capitol](https://github.com/EFForg/phantom-of-the-capitol)
2. Point to your instance in the `PHANTOM_API_BASE` variable in `config/settings.py`

#### POSTMARK SETUP

1. Create a postmark account and obtain credits.
2. Forward your inbound emails to postmark.
3. Add webhook to process outbound emails to the `/postmark/inbound` endpoint found in `app/urls.py`

#### REDIS SETUP

1. Install redis ([http://redis.io/](http://redis.io/) or `brew install redis`, `sudo apt-get install redis-server`)
2. Run the redis server with `$ redis-server`

### Helpful Commands

- To process emails, you'll need to point your postmark server inbound webhook to "\<your server\>/postmark/inbound".
Note that this isn't secure unless you have server authentication set up. Since it's not feasible to test locally
with postmark, you can simulate an inbound email using `python tasks/admin.py simulate_postmark_message <from_email> <to_oc_email>`.
If you use this script to simulate postmark messages then keep in mind that if `APP_DEBUG=True` in `config/settings.py`
then live emails will not send (unless the `<from_email>` argument is in the list in `ADMIN_EMAILS` - also
in `config/settings.py`).

- You can reset a user's acceptance of the terms of service by running `tasks/admin.py reset_tos <email>`.
This will make it so a user has to go through the signup process again.
Additionally, it will also allow all previously sent messages by the user to be sent again.


## License

Code released under the [MIT license](https://github.com/sunlightlabs/the-phantom-mask/blob/master/LICENSE).
Design released under [Creative Commons](https://github.com/sunlightlabs/the-phantom-mask/blob/master/design/LICENSE).