from flask import request, jsonify
from services import address_inferrence_service

def autofill_address():
    address = address_inferrence_service.address_lookup(**request.json)
    return jsonify(address)