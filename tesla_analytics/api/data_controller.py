from datetime import datetime
from typing import List
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_sqlalchemy import Pagination
from sqlalchemy import desc

from tesla_analytics.models import ChargeState, ClimateState, DriveState, VehicleState, User

blueprint = Blueprint("DataController", __name__)


@blueprint.route("/vehicles")
@jwt_required
def vehicles():
    user = User.query.filter_by(email=get_jwt_identity()).first()
    return jsonify([v.serialize() for v in user.vehicles])


@blueprint.route("/charge")
@jwt_required
def charge():
    return _fetch_data(ChargeState)


@blueprint.route("/climate")
@jwt_required
def climate():
    return _fetch_data(ClimateState)


@blueprint.route("/drive")
@jwt_required
def drive():
    return _fetch_data(DriveState)


@blueprint.route("/vehicle")
@jwt_required
def vehicle():
    return _fetch_data(VehicleState)


def _fetch_data(model):
    user = User.query.filter_by(email=get_jwt_identity()).first()
    vehicle_id = request.args.get("vehicle_id")
    if not vehicle_id:
        return jsonify({"error": "Missing required parameter 'vehicle_id'"}), 400
    if vehicle_id not in [v.tesla_id for v in user.vehicles]:
        return jsonify({"error": "Vehicle not found"}), 400

    if "start" in request.args and "end" in request.args:
        start_time = datetime.strptime(request.args["start"], "%Y-%m-%dT%H:%M:%S.%fZ")
        end_time = datetime.strptime(request.args["end"], "%Y-%m-%dT%H:%M:%S.%fZ")
        assert start_time < end_time
        query = model.query.filter(model.timestamp.between(start_time, end_time))
    else:
        query = model.query.order_by(desc(model.timestamp))

    data = query.paginate(per_page=50)
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
