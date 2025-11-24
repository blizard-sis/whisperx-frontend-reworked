"""Утилиты для проверки зависимостей WhisperX."""
from __future__ import annotations

import importlib
from importlib.util import find_spec
from typing import Dict, Iterable, List


class DependencyValidationError(RuntimeError):
    """Ошибка, возникающая при отсутствии критичных зависимостей."""


_REQUIRED_MODULES: Dict[str, str] = {
    "torch": "Установите PyTorch: pip install torch",  # Базовая зависимость
    "torchaudio": "Установите torchaudio: pip install torchaudio",
    "ctranslate2": "Установите ctranslate2: pip install ctranslate2",
    "faster_whisper": "Установите faster-whisper: pip install faster-whisper",
    "pyannote.audio": "Установите pyannote.audio: pip install pyannote.audio",
    "pytorch_lightning": "Установите pytorch-lightning: pip install pytorch-lightning",
    "torchvision": "Установите torchvision: pip install torchvision",
}

_OPTIONAL_HINTS: Dict[str, str] = {
    "sentencepiece": "Установите sentencepiece: pip install sentencepiece",
    "huggingface_hub": "Установите huggingface-hub: pip install huggingface-hub",
    "soundfile": "Установите soundfile: pip install soundfile",
}


def _missing_modules(modules: Iterable[str]) -> List[str]:
    missing: List[str] = []
    for module in modules:
        if find_spec(module) is None:
            missing.append(module)
    return missing


def validate_whisperx_dependencies() -> None:
    """Проверяет наличие ключевых зависимостей перед запуском WhisperX."""

    missing = _missing_modules(_REQUIRED_MODULES.keys())
    if missing:
        hints = [f"- {module}: {_REQUIRED_MODULES[module]}" for module in missing]
        raise DependencyValidationError(
            "Не найдены обязательные зависимости WhisperX:\n" + "\n".join(hints)
        )

    # Некоторые зависимости могут быть необязательными, но полезно подсказать о них заранее.
    optional_missing = _missing_modules(_OPTIONAL_HINTS.keys())
    if optional_missing:
        hints = [f"- {module}: {_OPTIONAL_HINTS[module]}" for module in optional_missing]
        print(
            "⚠️ Обнаружены отсутствующие дополнительные зависимости:\n" + "\n".join(hints)
        )

    # torchvision тесно связан с torch и часто вызывает ошибки совместимости при импорте.
    # Пробуем явно импортировать его, чтобы сообщить пользователю более понятную ошибку.
    try:
        importlib.import_module("torchvision")
    except ModuleNotFoundError as exc:
        raise DependencyValidationError(
            "Не найден пакет 'torchvision'. Установите его: pip install torchvision"
        ) from exc
    except RuntimeError as exc:
        raise DependencyValidationError(
            "Ошибка инициализации 'torchvision'. Убедитесь, что версии PyTorch и torchvision"
            " совместимы и что установлены необходимые операторные расширения"
            " (например, torchvision::nms). Исходная ошибка: "
            f"{exc}"
        ) from exc
    except Exception as exc:
        raise DependencyValidationError(
            "Не удалось инициализировать 'torchvision'. Проверьте установку и совместимость"
            f" зависимостей. Исходная ошибка: {exc}"
        ) from exc

    # Проверяем, что transformers корректно инициализируется и доступен класс Pipeline.
    try:
        transformers_module = importlib.import_module("transformers")
        # Попытка импортировать Pipeline выявляет скрытые ошибки зависимостей внутри transformers.
        getattr(transformers_module, "Pipeline")
    except ModuleNotFoundError as exc:
        raise DependencyValidationError(
            "Не удалось импортировать transformers.Pipeline. Установите пакет 'transformers'."
        ) from exc
    except AttributeError as exc:
        raise DependencyValidationError(
            "Класс transformers.Pipeline недоступен. Обновите пакет 'transformers'."
        ) from exc
    except Exception as exc:
        raise DependencyValidationError(
            "Ошибка инициализации transformers.Pipeline. Проверьте совместимость пакетов 'transformers',"
            " 'torch', 'torchvision', 'scikit-learn' и других зависимостей. Исходная ошибка: "
            f"{exc}"
        ) from exc

    # Отдельно проверяем scikit-learn, так как он требуется для VAD и генерации пайплайнов.
    try:
        importlib.import_module("sklearn")
    except ModuleNotFoundError as exc:
        raise DependencyValidationError(
            "Не найден пакет 'scikit-learn'. Установите его: pip install scikit-learn"
        ) from exc
    except Exception as exc:
        raise DependencyValidationError(
            "Ошибка инициализации 'scikit-learn'. Проверьте установленную версию."
            f" Исходная ошибка: {exc}"
        ) from exc
