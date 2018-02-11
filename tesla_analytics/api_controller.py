from typing import List
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from flask import Blueprint, request, jsonify
from flask_sqlalchemy import Pagination
from sqlalchemy import desc

from tesla_analytics.helpers import requires_api_token
from tesla_analytics.models import ChargeState, ClimateState, DriveState, VehicleState

blueprint = Blueprint("APIController", __name__)


@blueprint.route("/charge")
@requires_api_token
def charge():
    return _fetch_data(ChargeState)


@blueprint.route("/climate")
@requires_api_token
def climate():
    return _fetch_data(ClimateState)


@blueprint.route("/drive")
@requires_api_token
def drive():
    return _fetch_data(DriveState)


@blueprint.route("/vehicle")
@requires_api_token
def vehicle():
    return _fetch_data(VehicleState)


def _fetch_data(model):
    vehicle_id = request.args.get("vehicle_id")
    if not vehicle_id:
        return "", 400
    data = model.query.order_by(desc(model.timestamp)).paginate(per_page=50)
    serialized = [model.serialize() for model in data.items]

    headers = {"Link": ", ".join(
        _pagination_headers(data)
    )}

    return jsonify(serialized), 200, headers


def _pagination_headers(data: Pagination) -> List[str]:
    url = _url_without_pagination(request.url)
    items = []
    if data.has_prev:
        items.append("<{link}page={prev}>; rel=\"prev\"".format(
            link=url, prev=data.prev_num
        ))
    if data.has_next:
        items.append("<{link}page={next}>; rel=\"next\"".format(
            link=url, next=data.next_num
        ))
        items.append("<{link}page={last}>; rel=\"last\"".format(
            link=url, last=data.pages
        ))
    if data.has_prev:
        items.append("<{link}page=1>; rel=\"first\"".format(
            link=url
        ))
    return items


def _url_without_pagination(url: str) -> str:
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    query.pop('size', None)
    query.pop('page', None)
    connector = '&' if query else '?'
    parsed_url = parsed_url._replace(query=urlencode(query, True))
    return '{0}{1}'.format(urlunparse(parsed_url), connector)
