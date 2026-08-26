"""Gateway contracts re-exported without creating a second authority."""

from gateway.platforms.base import (
    BasePlatformAdapter,
    should_bypass_proxy,
    validate_media_delivery_path,
)

__all__ = ["BasePlatformAdapter", "should_bypass_proxy", "validate_media_delivery_path"]
