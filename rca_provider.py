# rca_provider.py

from abc import ABC, abstractmethod

class RCAProvider(ABC):
    @abstractmethod
    async def generate_rca(self, description: str, tags: list) -> dict:
        """Generate RCA based on description and tags."""
        pass
