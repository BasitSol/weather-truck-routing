from __future__ import annotations

import uuid
from pathlib import Path
from typing import ClassVar

from asgiref.sync import async_to_sync
from django.conf import settings
from django.http import FileResponse, HttpRequest, HttpResponse
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from trips.api.errors import ApiError
from trips.api.serializers import AnalyzeRequestSerializer, GeocodeQuerySerializer, present
from trips.providers.base import NoRouteError, ProviderError, RateLimitedError
from trips.services import providers
from trips.services.analyze import WeatherUnavailable, analyze
from trips.services.timezones import tz_at

VERSION = "1.0.0"


class AnalyzeView(APIView):
    throttle_classes: ClassVar = [ScopedRateThrottle]
    throttle_scope = "analyze"

    def post(self, request: Request) -> Response:
        serializer = AnalyzeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_id = uuid.uuid4().hex[:12]
        try:
            analysis = async_to_sync(analyze)(
                serializer.trip_request(), providers.routing(), providers.weather()
            )
        except NoRouteError as exc:
            raise ApiError(404, "no_route", str(exc)) from exc
        except RateLimitedError as exc:
            if exc.provider == "open-meteo":
                raise ApiError(
                    503,
                    "weather_busy",
                    "The free weather service is limiting requests right now. Try again in a minute.",
                ) from exc
            raise ApiError(
                503,
                "routing_busy",
                "The routing service is limiting requests right now. Try again in a minute.",
            ) from exc
        except ProviderError as exc:
            raise ApiError(
                502,
                "routing_unavailable",
                f"The routing service is unavailable right now (request {request_id}).",
            ) from exc
        except WeatherUnavailable as exc:
            raise ApiError(
                502,
                "weather_unavailable",
                f"The weather service is unavailable right now (request {request_id}).",
            ) from exc
        return Response(present(analysis, request_id))


class GeocodeView(APIView):
    throttle_classes: ClassVar = [ScopedRateThrottle]
    throttle_scope = "geocode"

    def get(self, request: Request) -> Response:
        query = GeocodeQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        places = async_to_sync(providers.geocoder().suggest)(
            query.validated_data["q"], query.bias(), query.validated_data["limit"]
        )
        return Response(
            {"results": [{"label": p.label, "lat": p.lat, "lon": p.lon, "tz": tz_at(p.pos)} for p in places]}
        )


class HealthView(APIView):
    def get(self, request: Request) -> Response:
        return Response(
            {
                "ok": True,
                "version": VERSION,
                "providers": {
                    "routing": providers.routing_service(),
                    "weather": providers.weather().name,
                    "geocode": providers.geocoder().name,
                },
            }
        )


def spa_index(request: HttpRequest) -> HttpResponse:
    """Serve the built single-page app for any non-API path (production; dev uses Vite)."""
    index = Path(settings.SPA_DIR) / "index.html"
    if not index.exists():
        return HttpResponse("Frontend not built. Run the Vite dev server (see README).", status=404)
    response = FileResponse(index.open("rb"), content_type="text/html")
    response["Cache-Control"] = "no-cache"
    return response
