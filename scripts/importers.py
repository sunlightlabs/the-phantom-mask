import sys
import os
import json
from dateutil import parser

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.path.pardir))

from util import absoluteFilePaths

def import_formageddon_users(path):
    """
    Imports formageddon user(s) from a file or directory of .json files.


    @param file_dir: [String] a particular file or directory
    @return:
    """

    from models import db
    from models import User
    from models import UserMessageInfo

    def perform_import(file):
        with open(file) as data_file:
            data = json.load(data_file)
            for person in data:
                user = User.query.filter_by(email=person['email']).first()
                if user is None:
                    user = User(email=person['email'])
                    db.session.add(user) and db.session.commit()
                created_at = parser.parse(person['created_at'])
                [person.pop(k,None) for k in ['email','created_at']]
                UserMessageInfo.first_or_create(user.id, created_at, **person)
                umi = None
                for item in UserMessageInfo.query.filter_by(user_id=user.id):
                    item.default = False
                    if umi is None or umi.created_at.replace(tzinfo=None) < item.created_at.replace(tzinfo=None):
                        umi = item
                if umi is not None:
                    umi.default = True
                    db.session.commit()

    if os.path.isdir(path):
        print "Importing all files in " + path
        for f in absoluteFilePaths(path):
            perform_import(f)
    else:
        print "Importing single file " + path
        perform_import(path)

if __name__ == '__main__':
    import_formageddon_users(sys.argv[1])