from .p01_schema_check import run as run_p01
from .p02_harmonize import run as run_p02
from .p03_deduplicate import run as run_p03
from .p04_outliers import run as run_p04
from .p05_treatment_define import run as run_p05
from .p06_missingness import run as run_p06
from .p07_time_order import run as run_p07
from .p08_variable_roles import run as run_p08
from .p09_clusters import run as run_p09

from ra_causal.core.registry import REGISTRY

__all__ = [
    "run_p01", "run_p02", "run_p03", "run_p04", "run_p05",
    "run_p06", "run_p07", "run_p08", "run_p09", "REGISTRY"
]

