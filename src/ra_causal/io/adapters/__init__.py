from .raw_assumed import adapt as adapt_raw_assumed
from .ciat import adapt as adapt_ciat

ADAPTERS = {
    "raw_assumed": adapt_raw_assumed,
    "ciat": adapt_ciat,
    "canonical": lambda df, schema_version: df # Do nothing for canonical
}

