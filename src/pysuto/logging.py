# src/pysuto/logging.py
import logging
import sys
import os


_LOG_DIR = None          # set by configure(); None until a run asks for log files
_NAMES: list = []        # every logger get_logger returned, in first-call order


def get_logger(name="system"):
    """
    Return a named logger with a console handler and no file handler.

    Importing pySUTO writes nothing to disk (#190); the per-module file
    ``<log_dir>/<name>.log`` appears only after :func:`configure` names a
    directory. Calling get_logger with the same name twice is idempotent
    (handlers are not duplicated).
    """
    logger = logging.getLogger(name)
    if not logger.handlers:  # prevent duplicate handlers; check own handlers only (not ancestors')
        logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(_formatter())
        logger.addHandler(ch)
        _NAMES.append(name)
        if _LOG_DIR is not None:
            _add_file_handler(logger, name)

    return logger


def configure(log_dir) -> None:
    """
    Send the per-module logs to ``<log_dir>/<name>.log`` from now on.

    Adds a file handler to every logger :func:`get_logger` has returned and to
    every one it returns later. A driver calls it once with ``<data-dir>/logs``;
    the directory is created here, not at import. Calling it again with the same
    directory is a no-op; with another one, the loggers move to the new directory.
    """
    global _LOG_DIR
    log_dir = os.fspath(log_dir)
    if log_dir == _LOG_DIR:
        return
    _LOG_DIR = log_dir
    os.makedirs(log_dir, exist_ok=True)
    for name in _NAMES:
        logger = logging.getLogger(name)
        for h in [h for h in logger.handlers if isinstance(h, logging.FileHandler)]:
            logger.removeHandler(h)
            h.close()
        _add_file_handler(logger, name)


def _add_file_handler(logger: logging.Logger, name: str) -> None:
    fh = logging.FileHandler(os.path.join(_LOG_DIR, f"{name}.log"))
    fh.setFormatter(_formatter())
    logger.addHandler(fh)


def add_run_handler(log_path: str) -> logging.FileHandler:
    """
    Attach a FileHandler for *this run* to the root logger.

    Because all named loggers propagate to root by default, a single call
    here funnels every logger in the process (feedpipe, conc, baci, …)
    into one timestamped file — without changing per-module log files.

    Returns the handler so the caller can remove it later if needed.

    Usage (top of an init script)::

        from pysuto.logging import add_run_handler
        add_run_handler(f"{data_dir}/logs/baci_v0_{datetime.now():%Y%m%d_%H%M%S}.log")
    """
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    fh = logging.FileHandler(log_path)
    fh.setFormatter(_formatter())
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(fh)
    return fh


def _formatter() -> logging.Formatter:
    return logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
