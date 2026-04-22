from core.cache_manager import load, mark_dirty
import copy

FILE_KEY = "embeds"


# =========================
# SAFE CACHE ACCESS
# =========================

def _get_cache():
    cache = load(FILE_KEY)

    if not isinstance(cache, dict):
        cache = {}

    return cache


# =========================
# NORMALIZE GUILD KEY
# =========================

def _gid(guild_id):
    return str(guild_id) if guild_id is not None else "global"


def _nid(name):
    return str(name) if name is not None else None


# =========================
# SAVE EMBED
# =========================

def save_embed(guild_id, name=None, data=None):

    if data is None:
        data = name
        name = guild_id
        guild_id = "global"

    cache = _get_cache()

    gid = _gid(guild_id)
    name = _nid(name)

    if not name:
        return False

    if gid not in cache or not isinstance(cache[gid], dict):
        cache[gid] = {}

    cache[gid][name] = copy.deepcopy(data)

    mark_dirty(FILE_KEY)
    return True


# =========================
# LOAD EMBED
# =========================

def load_embed(guild_id, name=None):

    if name is None:
        return None

    cache = _get_cache()

    gid = _gid(guild_id)
    name = _nid(name)

    guild_data = cache.get(gid, {})

    if not isinstance(guild_data, dict):
        return None

    return guild_data.get(name)


# =========================
# DELETE EMBED
# =========================

def delete_embed(guild_id, name=None):

    if name is None:
        return False

    cache = _get_cache()

    gid = _gid(guild_id)
    name = _nid(name)

    guild_data = cache.get(gid)

    if not isinstance(guild_data, dict):
        return False

    if name not in guild_data:
        return False

    del guild_data[name]

    if not guild_data:
        cache.pop(gid, None)

    mark_dirty(FILE_KEY)
    return True


# =========================
# GET ALL EMBEDS
# =========================

def get_all_embeds(guild_id):

    cache = _get_cache()

    gid = _gid(guild_id)

    guild_data = cache.get(gid, {})

    if not isinstance(guild_data, dict):
        return {}

    return guild_data


# =========================
# GET NAMES
# =========================

def get_all_embed_names(guild_id=None):

    if guild_id is None:
        return []

    cache = _get_cache()

    gid = _gid(guild_id)

    guild_data = cache.get(gid, {})

    if not isinstance(guild_data, dict):
        return []

    return list(guild_data.keys())
