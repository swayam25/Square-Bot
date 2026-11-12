from square.db.schema import DevTable


async def fetch_dev_ids() -> list[int]:
    devs = await DevTable.all().values_list("user_id", flat=True)
    return list(devs)


async def add_dev(user_id: int) -> None:
    await DevTable.get_or_create(user_id=user_id)


async def remove_dev(user_id: int) -> None:
    dev = await DevTable.filter(user_id=user_id).first()
    if dev:
        await dev.delete()
    else:
        raise ValueError(f"User ID {user_id} is not a developer.")
