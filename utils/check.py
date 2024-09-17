from utils import database as db

# Is the user a owner
def is_owner(user_id):
    owner_id = db.owner_id()
    if owner_id == user_id:
        return True
    else:
        return False

# Is the user a dev
def is_dev(user_id):
    owner_id = db.owner_id()
    dev_ids = db.dev_ids()
    if user_id in dev_ids or user_id == owner_id:
        return True
    else:
        return False
