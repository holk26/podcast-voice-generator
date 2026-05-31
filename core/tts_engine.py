from abc import ABC, abstractmethod
from typing import List
from core.project import Voice


class TTSBase(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice: Voice, output_path: str) -> str:
        pass

    @abstractmethod
    def clone_voice(self, reference_path: str, name: str) -> str:
        pass

    @abstractmethod
    def get_speakers(self) -> List[str]:
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        pass

    @abstractmethod
    def load(self) -> None:
        pass

    @abstractmethod
    def unload(self) -> None:
        pass
