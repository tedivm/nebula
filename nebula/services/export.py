from nebula.models import ssh_keys


def collect_all_keys():
    """Collect all keys into a dictionary, { name: [list of keys] }."""
    all_keys = {}
    keys = ssh_keys.list_all_ssh_keys()

    for entry in keys:
        if entry['username'] in all_keys:
            all_keys[entry['username']].append(entry['ssh_key'])
        else:
            all_keys[entry['username']] = [entry['ssh_key']]

    return all_keys
