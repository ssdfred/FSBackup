"""Windows source discovery module."""

from .service import SYSTEM_USER_DIRECTORIES, SourceDiscoveryService, discover_source

# Profils techniques supplémentaires créés par Windows pour les sessions
# temporaires, le rendu des polices et certains composants système. Ils ne
# représentent jamais des comptes utilisateur à sauvegarder.
SYSTEM_USER_DIRECTORIES.update(
    {
        "temp",
        "temp.font driver host",
        "umfd-0",
        "umfd-0.font driver host",
        "wsiaccount",
    }
)
SYSTEM_USER_DIRECTORIES.update(
    {f"temp.font driver host.{index:03d}" for index in range(1000)}
)
SYSTEM_USER_DIRECTORIES.update(
    {f"umfd-0.font driver host.{index:03d}" for index in range(1000)}
)

__all__ = [
    "SourceDiscoveryService",
    "discover_source",
]
