class SingleRouter:
    """Router for single-screen tests that logs navigation attempts."""

    def navigate(self, target: str) -> None:
        """Log navigation instead of performing it."""
        print(f"navigation to {target}")
