from config import BLOCKED_DOMAINS


def is_blocked(hostname: str) -> bool:
    """
    Return True if hostname matches a blocked domain
    or one of its subdomains.
    """
    hostname = hostname.lower().rstrip(".")

    for domain in BLOCKED_DOMAINS:
        domain = domain.lower().strip().rstrip(".")

        if hostname == domain or hostname.endswith("." + domain):
            return True

    return False