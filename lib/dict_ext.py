def remove_keys(dictionary, keys):
    [dictionary.pop(k, None) for k in keys]


def sanitize_keys(dictionary, whitelist):
    removed = []
    for key in dictionary.keys():
        if key not in whitelist:
            removed.append(dictionary.pop(key, None))
    return removed