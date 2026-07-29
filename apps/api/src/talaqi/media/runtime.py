from __future__ import annotations

from fastapi import FastAPI

from talaqi.config import MediaStorageBackend
from talaqi.media.local_storage import LocalMediaStorage
from talaqi.media.s3_storage import S3MediaStorage
from talaqi.media.storage import MediaStorage
from talaqi.runtime import SettingsFactory


class LazyMediaStorage:
    def __init__(
        self,
        settings_factory: SettingsFactory,
        storage: MediaStorage | None = None,
    ) -> None:
        self._settings_factory = settings_factory
        self._storage = storage

    def resolve(self) -> MediaStorage:
        if self._storage is None:
            settings = self._settings_factory()
            if settings.media_storage_backend is MediaStorageBackend.LOCAL:
                self._storage = LocalMediaStorage(
                    settings.media_local_root,
                    api_public_url=str(settings.api_public_url),
                    signing_secret=settings.session_secret.get_secret_value().encode("utf-8"),
                )
            else:
                self._storage = S3MediaStorage(
                    endpoint=str(settings.s3_endpoint),
                    bucket=settings.s3_bucket,
                    access_key=settings.s3_access_key.get_secret_value(),
                    secret_key=settings.s3_secret_key.get_secret_value(),
                    region=settings.s3_region,
                )
        return self._storage

    async def ready(self) -> bool:
        return await self.resolve().ready()


def install_media_storage(
    application: FastAPI,
    settings_factory: SettingsFactory,
    storage: MediaStorage | None = None,
) -> LazyMediaStorage:
    runtime = LazyMediaStorage(settings_factory, storage)
    application.state.media_storage_runtime = runtime
    return runtime


__all__ = ["LazyMediaStorage", "install_media_storage"]
