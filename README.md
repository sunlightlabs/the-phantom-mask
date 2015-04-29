# The Phantom Mask

Lightweight Flask web app to courier email messages via [Postmark](https://postmarkapp.com/) to be processed by an instance of [Phantom of the Capitol](https://github.com/EFForg/phantom-of-the-capitol).


## Installation and Setup

This project is still a work in progress so the README will be updated as it finalizes. In the meantime, you can get a working development environment set up by doing the following.

1. Clone the project
2. Create a virtul environment for Python 2.7.8
3. `pip install -r requirements.txt`
4. `mv config/settings.py.example config/settings.py` **YOU WILL NEED TO CONFIG THIS**
5. Set values for API keys, url for your instance of Phantom of the Capitol, etc in `config/settings.py`
6. `python tasks/admin.py setup_test_environment` to create initial schema for database & create test data
7. `python run.py` to run app locally for development. 
8. Check out `bin/deploy.sh` and `fabfile.py` for deploying to a production environment

To process emails, you'll need to point your postmark server inbound webhook to "\<your server\>/postmark/inbound". Note that this isn't secure unless you have server authentication set up. Since it's not feasible to test locally with postmark, you can simulate an inbound email using `python tasks/admin.py simulate_postmark_message <from_email> <to_oc_email>`.
