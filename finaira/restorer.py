def restore(response: str, vault) -> str:
    for token, record in vault.by_token.items():
        response = response.replace(token, record.original)
    return response
