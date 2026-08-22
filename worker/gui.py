import logging
import queue
import threading
import tkinter as tk
from tkinter import scrolledtext
from typing import Callable

logger = logging.getLogger(__name__)


class WorkerGui:
    """Ventana tkinter simple de estado del worker."""

    def __init__(self, on_reconnect: Callable[[], None] | None = None) -> None:
        self.on_reconnect = on_reconnect
        self._queue: queue.Queue[dict] = queue.Queue()
        self._root: tk.Tk | None = None
        self._thread: threading.Thread | None = None
        self._status_var: tk.StringVar | None = None
        self._job_var: tk.StringVar | None = None
        self._log_box: scrolledtext.ScrolledText | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        self._root = tk.Tk()
        self._root.title("Podcast Worker")
        self._root.geometry("600x400")
        self._root.configure(bg="#1e293b")

        self._status_var = tk.StringVar(value="Conectando...")
        self._job_var = tk.StringVar(value="Sin trabajo activo")

        header = tk.Label(
            self._root,
            text="Worker de Podcast",
            fg="#e2e8f0",
            bg="#1e293b",
            font=("Helvetica", 16, "bold"),
        )
        header.pack(pady=(12, 8))

        status_frame = tk.Frame(self._root, bg="#1e293b")
        status_frame.pack(fill="x", padx=16, pady=4)

        tk.Label(status_frame, text="Estado:", fg="#94a3b8", bg="#1e293b", font=("Helvetica", 11)).pack(side="left")
        tk.Label(status_frame, textvariable=self._status_var, fg="#4ade80", bg="#1e293b", font=("Helvetica", 11, "bold")).pack(side="left", padx=(8, 0))

        job_frame = tk.Frame(self._root, bg="#1e293b")
        job_frame.pack(fill="x", padx=16, pady=4)

        tk.Label(job_frame, text="Job actual:", fg="#94a3b8", bg="#1e293b", font=("Helvetica", 11)).pack(side="left")
        tk.Label(job_frame, textvariable=self._job_var, fg="#e2e8f0", bg="#1e293b", font=("Helvetica", 11)).pack(side="left", padx=(8, 0), fill="x")

        tk.Label(self._root, text="Logs recientes:", fg="#94a3b8", bg="#1e293b", font=("Helvetica", 11)).pack(anchor="w", padx=16, pady=(12, 4))

        self._log_box = scrolledtext.ScrolledText(
            self._root,
            wrap=tk.WORD,
            bg="#0f172a",
            fg="#cbd5e1",
            insertbackground="#cbd5e1",
            font=("Consolas", 10),
            height=12,
        )
        self._log_box.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self._log_box.config(state="disabled")

        btn_frame = tk.Frame(self._root, bg="#1e293b")
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))

        reconnect_btn = tk.Button(
            btn_frame,
            text="Reconectar",
            command=self._on_reconnect,
            bg="#7c3aed",
            fg="white",
            activebackground="#6d28d9",
            borderwidth=0,
            padx=12,
            pady=4,
        )
        reconnect_btn.pack(side="left", padx=(0, 8))

        quit_btn = tk.Button(
            btn_frame,
            text="Salir",
            command=self._root.destroy,
            bg="#334155",
            fg="#e2e8f0",
            activebackground="#475569",
            borderwidth=0,
            padx=12,
            pady=4,
        )
        quit_btn.pack(side="left")

        self._poll_queue()
        self._root.protocol("WM_DELETE_WINDOW", self._root.destroy)
        self._root.mainloop()

    def _on_reconnect(self) -> None:
        if self.on_reconnect:
            threading.Thread(target=self.on_reconnect, daemon=True).start()

    def _poll_queue(self) -> None:
        if self._root is None:
            return
        try:
            while True:
                msg = self._queue.get_nowait()
                self._apply_update(msg)
        except queue.Empty:
            pass
        self._root.after(200, self._poll_queue)

    def _apply_update(self, msg: dict) -> None:
        kind = msg.get("kind")
        if kind == "status" and self._status_var:
            self._status_var.set(msg.get("value", ""))
        elif kind == "job" and self._job_var:
            self._job_var.set(msg.get("value", ""))
        elif kind == "log" and self._log_box:
            self._log_box.config(state="normal")
            self._log_box.insert("end", msg.get("value", "") + "\n")
            self._log_box.see("end")
            self._log_box.config(state="disabled")

    def update_status(self, text: str) -> None:
        self._queue.put({"kind": "status", "value": text})

    def update_job(self, text: str) -> None:
        self._queue.put({"kind": "job", "value": text})

    def log(self, text: str) -> None:
        self._queue.put({"kind": "log", "value": text})


class GuiLogHandler(logging.Handler):
    """Handler de logging que redirige los registros a una WorkerGui."""

    def __init__(self, gui: WorkerGui) -> None:
        super().__init__()
        self.gui = gui

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.gui.log(msg)
        except Exception:
            self.handleError(record)
