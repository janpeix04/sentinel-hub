import datetime as dt
from collections.abc import Iterable
from typing import Any, Literal

from sentinel_hub.api.base import SHService
from sentinel_hub.api.utils import remove_undefined
from sentinel_hub.base import FeatureIterator
from sentinel_hub.geometry import CRS, BBox, Geometry
from sentinel_hub.time_utils import parse_time, parse_time_interval, serialize_time
from sentinel_hub.types import JsonDict, RawTimeIntervalType, RawTimeType


class SHCatalog(SHService):
    """
    The main class for interacting with Sentinel Hub Catalog API.

    For more details about certain endpoints and parameters check Catalog API documentation:
    <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Catalog.html>.
    """

    @staticmethod
    def _get_service_url(base_url: str) -> str:
        """Provides URL to Catalog API."""
        return f"{base_url}/api/v1/catalog/1.0.0"

    def get_info(self) -> JsonDict:
        """
        Provides the main information that define Sentinel Hub Catalog API.

        Catalog API reference:
        <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/ApiReference.html>.
        """
        return self.client.get_json_dict(self.service_url)

    def get_conformance(self) -> JsonDict:
        """
        Get information about specifications that this API conforms to.

        Catalog API reference:
        <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/ApiReference.html>.
        """
        return self.client.get_json_dict(f"{self.service_url}/conformance")

    def get_collections(self) -> list[JsonDict]:
        """
        Provides a list of collections that are available to a user.

        Catalog API reference:
        <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/ApiReference.html>.
        """
        return self.client.get_json_dict(
            f"{self.service_url}/collections", use_session=True
        )["collections"]

    def get_collection(self, collection_id: str) -> JsonDict:
        """
        Provides information about given collection.

        Catalog API reference:
        <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/ApiReference.html>.
        """
        url = f"{self.service_url}/collections/{collection_id}"
        return self.client.get_json_dict(url, use_session=True)

    def get_feature(self, collection_id: str, feature_id: str) -> JsonDict:
        """
        Provides information about a single feature in a collection.

        Catalog API reference:
        <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/ApiReference.html>."""
        url = f"{self.service_url}/collections/{collection_id}/items/{feature_id}"
        return self.client.get_json_dict(url, use_session=True)

    def search(
        self,
        collection_id: str,
        *,
        time: RawTimeType | RawTimeIntervalType = None,
        bbox: BBox | None = None,
        geometry: Geometry | None = None,
        ids: list[str] | None = None,
        filter: None | str | JsonDict = None,
        filter_lang: Literal["cql2-text", "cql2-json"] = "cql2-text",
        fields: JsonDict | None = None,
        limit: int = 100,
        **kwargs: Any,
    ) -> CatalogSearchIterator:
        """
        Catalog STAC search.

        Catalog API reference:
        <https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/ApiReference.html>.
        """
        url = f"{self.service_url}/search"

        start_time, end_time = serialize_time(
            parse_time_interval(time, allow_undefined=True), use_tz=True
        )

        if bbox and bbox.crs is not CRS.WGS84:
            bbox = bbox.transform_bounds(CRS.WGS84)
        if geometry and geometry.crs is not CRS.WGS84:
            geometry = geometry.transform(CRS.WGS84)

        payload = remove_undefined(
            {
                "collections": [collection_id],
                "datetime": f"{start_time}/{end_time}" if time else None,
                "bbox": list(bbox) if bbox else None,
                "intersects": geometry.get_geojson(with_crs=False)
                if geometry
                else None,
                "ids": ids,
                "filter": filter,
                "filter-lang": filter_lang if filter else None,
                "fields": fields,
                "limit": limit,
                **kwargs,
            }
        )

        return CatalogSearchIterator(self.client, url, payload)


class CatalogSearchIterator(FeatureIterator[JsonDict]):
    """Searches a catalog with a given query and provides results."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.next: JsonDict | None = None

    def _fetch_features(self) -> Iterable[JsonDict]:
        """Collects more results from the service."""
        payload = remove_undefined({**self.params, "next": self.next})

        results = self.client.get_json_dict(
            self.url, post_values=payload, use_session=True
        )

        self.next = results["context"].get("next")
        new_features = results["features"]
        self.finished = self.next is None or not new_features

        return new_features

    def get_timestamps(self) -> list[dt.datetime]:
        """Provides features timestamps."""
        return [
            parse_time(feature["properties"]["datetime"], force_datetime=True)
            for feature in self
        ]

    def get_geometries(self) -> list[Geometry]:
        """Provides features geometries."""
        return [Geometry.from_geojson(feature["geometry"]) for feature in self]

    def get_ids(self) -> list[str]:
        """Provides features IDs."""
        return [feature["id"] for feature in self]
