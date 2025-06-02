from ..schema import DevTable


async def fetch_dev_ids() -> list[int]:
    """Fetches all developer user IDs from the database."""
    devs = await DevTable.all().values_list("user_id", flat=True)
    return list(devs)


async def add_dev(user_id: int) -> None:
    """
    Adds a developer user ID to the database.

    Parameters:
        user_id (int): The user ID to perform action on.
    """
    await DevTable.get_or_create(user_id=user_id)


async def remove_dev(user_id: int) -> None:
    """
    Removes a developer user ID from the database.

    Parameters:
        user_id (int): The user ID to perform action on.
    """
    dev = await DevTable.filter(user_id=user_id).first()
    if dev:
        await dev.delete()
    else:
        raise ValueError(f"User ID {user_id} is not a developer.")
