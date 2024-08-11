from utils import database as db, emoji

# Is the user a owner
def is_owner(user_id):
    if db.owner_ids() == user_id:
        return True
    else:
        return False

# Is the user a dev
def is_dev(user_id):
    if user_id in db.dev_ids:
        return True
    else:
        return False
