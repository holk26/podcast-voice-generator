from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional
from core.project import Project, Section
from core.audio_pipeline import AudioPipeline
from core.tts_engine import TTSBase


@dataclass
class GenerationTask:
    section_id: str
    status: str = "pending"  # pending, running, completed, failed
    output_path: Optional[str] = None
    error: Optional[str] = None


class BatchGenerator:
    def __init__(self, pipeline: Optional[AudioPipeline] = None):
        self.pipeline = pipeline or AudioPipeline()
        self.queue: List[GenerationTask] = []
        self.engines: Dict[str, TTSBase] = {}
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None

    def register_engine(self, name: str, engine: TTSBase) -> None:
        self.engines[name] = engine

    def set_progress_callback(self, callback: Callable[[int, int, str], None]) -> None:
        self._progress_callback = callback

    def add_project(self, project: Project) -> None:
        for section in project.sections:
            task = GenerationTask(section_id=section.id)
            self.queue.append(task)

    def run(self, project: Project) -> List[GenerationTask]:
        total = len(self.queue)
        for i, task in enumerate(self.queue):
            if task.status == "completed":
                continue
            task.status = "running"
            if self._progress_callback:
                self._progress_callback(i + 1, total, f"Generating {task.section_id}...")
            
            section = None
            for s in project.sections:
                if s.id == task.section_id:
                    section = s
                    break
            
            if section is None:
                task.status = "failed"
                task.error = "Section not found"
                continue
            
            try:
                output_path = self.pipeline.generate_section(project, section, self.engines)
                task.output_path = output_path
                task.status = "completed"
                project.generation_state["completed_sections"].append(task.section_id)
                project.generation_state["output_files"][task.section_id] = output_path
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
        
        project.generation_state["status"] = "completed" if all(t.status == "completed" for t in self.queue) else "partial"
        if self._progress_callback:
            completed = sum(1 for t in self.queue if t.status == "completed")
            self._progress_callback(completed, total, "Done")
        return self.queue

    def reset(self) -> None:
        self.queue.clear()
