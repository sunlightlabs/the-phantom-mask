from flask import request, jsonify
from services import address_inferrence_service


def autofill_address():
    address = address_inferrence_service.address_lookup(**request.json)
    if address is None:
        address = {'error': 'Unable to locate city, state, and zip4.'}
    return jsonify(address)