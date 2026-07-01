"""Apple Sign In — documented stub (not implemented for V1; SPEC §3.1)."""


class AppleOAuthNotImplemented(NotImplementedError):
    """Raised to signal Apple Sign In is not yet available."""


async def verify_apple_identity_token(identity_token: str) -> dict:
    """TODO(V2): implement after obtaining an Apple Developer account."""
    raise AppleOAuthNotImplemented("Apple Sign In is not available in V1.")
