import ctypes
import os
import platform
from typing import Any, Dict


class SystemSpecs:
    """Collects lightweight runtime information for recommendation logic."""

    @staticmethod
    def detect() -> Dict[str, Any]:
        memory_gb = SystemSpecs._detect_memory_gb()
        gpu_name = None
        has_cuda = False

        try:
            import torch

            has_cuda = bool(torch.cuda.is_available())
            if has_cuda:
                gpu_name = torch.cuda.get_device_name(0)
        except Exception:
            has_cuda = False

        cpu_count = os.cpu_count() or 1
        spec_tier = "entry"
        if has_cuda or memory_gb >= 16 or cpu_count >= 12:
            spec_tier = "high"
        elif memory_gb >= 8 or cpu_count >= 8:
            spec_tier = "balanced"

        return {
            "os": platform.system(),
            "os_version": platform.release(),
            "architecture": platform.machine() or "unknown",
            "cpu": platform.processor() or "Unknown CPU",
            "cpu_count": cpu_count,
            "memory_gb": memory_gb,
            "has_cuda": has_cuda,
            "gpu_name": gpu_name,
            "tier": spec_tier,
        }

    @staticmethod
    def recommended_whisper_model(specs: Dict[str, Any]) -> str:
        if specs.get("has_cuda") or specs.get("memory_gb", 0) >= 16:
            return "turbo"
        if specs.get("memory_gb", 0) >= 8:
            return "small"
        return "base"

    @staticmethod
    def _detect_memory_gb() -> int:
        if platform.system() == "Windows":
            try:
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                memory_status = MEMORYSTATUSEX()
                memory_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))
                return max(1, round(memory_status.ullTotalPhys / (1024 ** 3)))
            except Exception:
                pass

        try:
            import psutil  # type: ignore

            return max(1, round(psutil.virtual_memory().total / (1024 ** 3)))
        except Exception:
            return 8
