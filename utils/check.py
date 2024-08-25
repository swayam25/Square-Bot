from utils import database as db

# Is the user a owner
def is_owner(user_id):
    owner_ids = db.owner_ids()
    if owner_ids == user_id:
        return True
    else:
        return False

# Is the user a dev
def is_dev(user_id):
    owner_ids = db.owner_ids()
    dev_ids = db.dev_ids()
    if user_id in dev_ids or user_id == owner_ids:
        return True
    else:
        return False
