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
# SAVE EMBED
# =========================

def save_embed(guild_id, name=None, data=None):

    if data is None:
        data = name
        name = guild_id
        guild_id = "global"

    cache = _get_cache()

    guild_id = str(guild_id)

    # 🔥 FIX: isolate guild bucket safely
    if guild_id not in cache or not isinstance(cache[guild_id], dict):
        cache[guild_id] = {}

    # 🔥 FIX: deepcopy to avoid shared mutation bug
    cache[guild_id][name] = copy.deepcopy(data)

    mark_dirty(FILE_KEY)


# =========================
# LOAD EMBED
# =========================

def load_embed(guild_id, name=None):

    if name is None:
        return None

    cache = _get_cache()

    guild_data = cache.get(str(guild_id), {})

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

    guild_id = str(guild_id)

    guild_data = cache.get(guild_id)

    if not isinstance(guild_data, dict):
        return False

    if name not in guild_data:
        return False

    del guild_data[name]

    if not guild_data:
        cache.pop(guild_id, None)

    mark_dirty(FILE_KEY)
    return True


# =========================
# GET ALL EMBEDS
# =========================

def get_all_embeds(guild_id):

    cache = _get_cache()

    guild_data = cache.get(str(guild_id), {})

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

    guild_data = cache.get(str(guild_id), {})

    if not isinstance(guild_data, dict):
        return []

    return list(guild_data.keys())
