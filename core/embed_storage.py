from core.cache_manager import load, mark_dirty

FILE_KEY = "embeds"


# =========================
# SAVE EMBED
# =========================

def save_embed(guild_id, name=None, data=None):

    if data is None:
        data = name
        name = guild_id
        guild_id = "global"

    cache = load(FILE_KEY)

    guild_id = str(guild_id)

    if guild_id not in cache:
        cache[guild_id] = {}

    cache[guild_id][name] = data

    mark_dirty(FILE_KEY)


# =========================
# LOAD EMBED
# =========================

def load_embed(guild_id, name=None):

    if name is None:
        return None

    cache = load(FILE_KEY)

    return cache.get(str(guild_id), {}).get(name)


# =========================
# DELETE EMBED
# =========================

def delete_embed(guild_id, name=None):

    if name is None:
        return False

    cache = load(FILE_KEY)

    guild_id = str(guild_id)

    if guild_id in cache and name in cache[guild_id]:

        del cache[guild_id][name]

        if not cache[guild_id]:
            cache.pop(guild_id, None)

        mark_dirty(FILE_KEY)
        return True

    return False


# =========================
# GET ALL EMBEDS
# =========================

def get_all_embeds(guild_id):

    cache = load(FILE_KEY)

    return cache.get(str(guild_id), {})


# =========================
# GET NAMES
# =========================

def get_all_embed_names(guild_id=None):

    if guild_id is None:
        return []

    cache = load(FILE_KEY)

    return list(cache.get(str(guild_id), {}).keys())
