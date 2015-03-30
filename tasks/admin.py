import os
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.pardir))

from models import db
from daily import import_congresspeople


def reset_database(prompt=True):
    if prompt:
        decision = raw_input("This will delete everything in the database. Are you sure you want to do this? [Y,n]")
    else:
        decision = 'Y'

    if decision == 'Y':
        print 'Dropping all tables and recreating them from scratch...'
        db.drop_all()
        db.create_all()
        print 'Importing congresspeople...'
        import_congresspeople()
    else:
        print "Aborting resetting database."

if __name__ == '__main__':
    if len(sys.argv) > 1:
        try:
            {
                'reset_database': reset_database
            }.get(sys.argv[1])()
        except:
            print 'Admin task with name "' + sys.argv[1] + '" does not exist.'
    else:
        print 'Please provide an admin task to run with relevant arguments.'